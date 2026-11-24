"""Real shared Bluetooth QML/Process/dialogs with a synthetic stdio helper only."""
import argparse
from pathlib import Path
import check_desktop_panels

MODES = ('pin', 'confirm', 'display', 'reject', 'cancel', 'uncertain', 'device-loss')
HELPER = '''#!/usr/bin/python3
import json,sys,time
scope=next(a[8:] for a in sys.argv if a.startswith('--scope='))
def emit(**p): print(json.dumps(dict(p,scope=scope)),flush=True)
emit(event='ready')
for line in sys.stdin:
 p=json.loads(line)
 if p['op']=='stop': break
 if p['op']=='connect':
  token=p['token']
  emit(event='prompt',token=token,prompt_id='1',kind='__KIND__',code='000042',entered=2)
  if '__KIND__'=='DisplayPasskey':
   time.sleep(.15);emit(event='result',token=token,status='observed',error='')
 if p['op']=='answer':
  valid=not p['accept'] or p['value']=='AB12' or '__KIND__'!='RequestPinCode'
  emit(event='result',token=p['token'],status='__STATUS__' if p['accept'] and valid else 'error',error='' if p['accept'] else 'org.bluez.Error.AuthenticationRejected')
 if p['op']=='cancel': emit(event='result',token=p['token'],status='cancelled',error='explicit-cancel')
'''

PROBE = '''import QtQuick
import QtQuick.Window
import Quickshell
import "FixtureBluetooth"
ShellRoot {
 id:test
 property string mode:"__MODE__"
 property var session:null
 property var view:null
 property int phase:0
 property int ticks:0
 Window {id:window;visible:true;width:700;height:900}
 QtObject {
  id:bar
  property bool vertical:false
  property string position:"top"
  property int barSize:26
  property color foreground:"#cccccc"
  property color barForeground:foreground
  property color background:"#101315"
  property color urgent:"#ee8888"
  property string fontFamily:"JetBrainsMono Nerd Font"
  property bool foregroundAnimationEnabled:false
  function registerClickTarget(target){}
  function unregisterClickTarget(target){}
  function showTooltip(item,text){}
  function hideTooltip(item){}
  function requestPopout(owner){}
  function releasePopout(owner){}
 }
 function require(v,m){if(!v)throw Error(m)}
 function make(file,props){var c=Qt.createComponent(file,Component.PreferSynchronous);require(c.status===Component.Ready,c.errorString());var v=c.createObject(null,props);c.destroy();require(v!==null,'construct '+file);return v}
 function find(item,predicate){if(predicate(item))return item;var list=item.children||[];for(var i=0;i<list.length;i++){var value=find(list[i],predicate);if(value)return value}return null}
 function done(){session.enabled=false;console.log('OMABUNTU_BLUETOOTH_COMPLETION_OK');Qt.callLater(function(){Qt.quit()})}
 Timer {interval:25;repeat:true;running:true;onTriggered:{try{
  require(++test.ticks<100,'bounded synthetic Bluetooth QML fixture')
  if(test.phase===0){
   test.session=make('BluetoothSession.qml',{helper:'/probe/helpers/bluetooth-agent'})
   require(!test.session.rpc.running&&!test.session.pending,'component startup does not start an agent')
   test.view=make('BluetoothControlView.qml',{bar:bar,session:test.session})
   test.view.parent=window.contentItem;test.view.opened=true;test.view.panelWindow.ensureContent()
   require(!test.session.rpc.running,'opening original panel never starts an agent')
   var d=Bluetooth.defaultAdapter.devices.values[1]
   require(test.view.connectDevice(d),'explicit original device action starts owned session')
   require(!test.view.connectDevice(d),'shared owner prevents duplicate action')
   test.phase=1;return
  }
  if(test.phase===1){
   if(!test.session.prompt)return
   require(test.session.prompt.code==='000042','matching current helper prompt is admitted')
   var before=test.session.prompt
   test.session.receive(JSON.stringify({scope:'stale',event:'prompt',token:'stale',prompt_id:'2',kind:'RequestAuthorization'}))
   require(test.session.prompt===before,'stale scope cannot replace authentication dialog')
   if(test.mode==='device-loss'){
    Bluetooth.defaultAdapter.devices={values:[]};test.phase=3;return
   }
   var field=find(test.view,function(i){return i.password===true&&i.maximumLength!==undefined})
   require(field,'original licensed text field is present')
   if(test.mode==='display'){
    require(!field.visible&&test.session.prompt.displayOnly&&!test.session.answer(test.session.prompt.id,true,''),'display-only pairing cannot submit or auto-confirm')
    require(test.session.prompt.entered===2,'remote entered-digit count is displayed')
   }else if(test.mode==='pin'){
    require(field.visible&&field.maximumLength===16,'PIN entry is bounded and password-masked')
    field.text='AB12';field.accepted();require(field.text==='','transient input cleared immediately on submit')
   }else if(test.mode==='cancel')test.session.cancel()
   else {
    require(!field.visible,'confirmation does not expose an input field')
    var action=find(test.view,function(i){return i.text===(test.mode==='reject'?'Reject':'Confirm')&&i.clicked!==undefined})
    require(action&&action.visible&&action.focusable,'original confirmation/rejection button is keyboard accessible')
    action.clicked()
   }
   test.phase=2;return
  }
  if(test.session.pending)return
  require(test.session.prompt===null,'terminal outcome clears the transient prompt')
  if(test.mode==='uncertain'||test.mode==='device-loss'){
   require(test.session.uncertain,'loss/uncertainty is retained')
   var old=Bluetooth.defaultAdapter.devices.values[1]
   require(!test.session.begin(old,Bluetooth.defaultAdapter,'connecting'),'uncertainty blocks new writers')
   require(test.session.acknowledge()&&!test.session.uncertain&&!test.session.pending,'acknowledgement never retries')
  }else if(test.mode==='reject')require(test.session.errorText.indexOf('AuthenticationRejected')>=0,'structured rejection reaches original panel')
  else if(test.mode==='cancel')require(test.session.errorText.indexOf('cancelled')>=0,'explicit cancellation is distinct from success')
  else require(test.session.errorText==='','successful observed result is not reported as an error')
  test.view.close();require(!test.session.prompt,'close leaves no code text');done()
 }catch(error){console.error('DESKTOP_COMPILE_FAILED: '+error);Qt.exit(42)}}}
}
'''


def run(root, build, modes=MODES):
    result = 0
    for mode in modes:
        helper = HELPER.replace('__KIND__', 'RequestPinCode' if mode == 'pin' else 'DisplayPasskey' if mode == 'display' else 'RequestConfirmation')
        helper = helper.replace('__STATUS__', 'uncertain' if mode == 'uncertain' else 'observed')
        result |= check_desktop_panels.run(root, build, probe=PROBE.replace('__MODE__', mode),
                  extra_files={'helpers/bluetooth-agent': (helper, 0o500)},
                  markers=('OMABUNTU_BLUETOOTH_COMPLETION_OK',))
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir',required=True,type=Path)
    args=parser.parse_args(argv)
    return run(Path(__file__).resolve().parents[1],args.build_dir)


if __name__=='__main__':
    raise SystemExit(main())
