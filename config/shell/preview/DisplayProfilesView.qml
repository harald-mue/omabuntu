import QtQuick
import qs.Ui as Ui
import qs.Commons

// Explicit capability page in the original popup, not a replacement monitor panel.
Column {
  id:root
  required property var owner
  required property var bar
  signal back()
  spacing:Style.space(10)
  readonly property bool locked:!owner||owner.busy||!!owner.data.pending
  function label(item,value) {return value}
  Ui.Button {text:"Back";iconText:"󰁍";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;onClicked:root.back()}
  Ui.PanelSectionHeader {text:"MONITOR PROFILES";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily}
  Text {
    width:parent.width;wrapMode:Text.Wrap;textFormat:Text.PlainText;color:root.bar.foreground;font.family:root.bar.fontFamily;font.pixelSize:Style.font.bodySmall
    text:"Save a layout, review its exact target, then Apply and Keep within 25 seconds. Otherwise a separate recovery guard restores the previous matched layout. Unknown identities or external drift refuse recovery. Disabling outputs moves windows/workspaces; restoring geometry does not restore their placement. Explicit connector rules may override fallback-rule defaults. Advanced color/VRR/mirroring is excluded. Text size affects only this shell, not GTK/GNOME or application fonts."
  }
  Text {width:parent.width;wrapMode:Text.Wrap;textFormat:Text.PlainText;color:root.bar.urgent;font.family:root.bar.fontFamily;text:root.owner?root.owner.errorText:"Profiles helper unavailable"}
  Ui.Button {text:"Refresh";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!!root.owner&&!root.owner.busy;onClicked:root.owner.refresh()}
  Ui.TextField {id:profileName;width:parent.width;maximumLength:48;placeholderText:"Profile name";enabled:!root.locked;foreground:root.bar.foreground}
  Ui.Button {text:"Capture current layout";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!root.locked&&profileName.text.length>0;onClicked:root.owner.capture(profileName.text)}
  Repeater {
    model:root.owner?root.owner.data.profiles:[]
    Column {
      required property var modelData
      width:root.width;spacing:Style.space(5)
      Ui.Button {text:modelData.name+(modelData.automatic?" · automatic":"");foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!root.locked;onClicked:root.owner.select(modelData)}
      Row {
        spacing:Style.space(6)
        Ui.Button {text:modelData.automatic?"Stop automatic":"Use at login/hotplug";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!root.locked&&modelData.kept;onClicked:root.owner.automate(modelData)}
        Ui.Button {text:"Delete";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!root.locked;onClicked:root.owner.remove(modelData)}
      }
    }
  }
  Repeater {
    model:root.owner?(root.owner.data.previous||[]):[]
    Ui.Button {
      required property var modelData
      text:"Load previous layout: "+modelData.name
      foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!root.locked
      onClicked:{root.owner.select(modelData);root.owner.draftDirty=true}
    }
  }
  Column {
    width:parent.width;visible:!!root.owner&&!!root.owner.draft;spacing:Style.space(8)
    Text {text:root.owner&&root.owner.draft?"EDIT: "+root.owner.draft.name:"";textFormat:Text.PlainText;color:root.bar.foreground;font.family:root.bar.fontFamily;font.pixelSize:Style.font.subtitle}
    Repeater {
      model:root.owner&&root.owner.draft?root.owner.draft.outputs:[]
      Column {
        required property var modelData
        required property int index
        id:device
        width:root.width;spacing:Style.space(5)
        Text {width:parent.width;wrapMode:Text.Wrap;textFormat:Text.PlainText;text:device.modelData.identity.connector+" · "+device.modelData.identity.make+" "+device.modelData.identity.model;color:root.bar.foreground;font.family:root.bar.fontFamily;font.pixelSize:Style.font.body}
        Text {width:parent.width;wrapMode:Text.Wrap;textFormat:Text.PlainText;color:root.bar.foreground;font.family:root.bar.fontFamily;font.pixelSize:Style.font.caption;text:"Advertised modes: "+(root.owner?root.owner.data.inventory.filter(function(m){return m.name===device.modelData.identity.connector||m.serial&&m.serial===device.modelData.identity.serial}).map(function(m){return (m.availableModes||[]).slice(0,16).join(", ")}).join("; "):"")}
        Ui.Button {text:device.modelData.enabled?"Enabled — click to disable in draft":"Disabled — click to enable in draft";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!root.locked;onClicked:root.owner.edit(device.index,"enabled",!device.modelData.enabled)}
        Repeater {
          model:[{key:"width",title:"Width"},{key:"height",title:"Height"},{key:"refresh",title:"Refresh Hz"},{key:"scale",title:"Scale 0.5–4"},{key:"x",title:"X position"},{key:"y",title:"Y position"},{key:"transform",title:"Transform 0–7"}]
          Row {
            required property var modelData
            spacing:Style.space(8)
            Text {width:Style.space(135);text:modelData.title;textFormat:Text.PlainText;color:root.bar.foreground;font.family:root.bar.fontFamily;font.pixelSize:Style.font.body}
            Ui.TextField {objectName:"displayProfile-"+modelData.key+"-"+device.index;width:Style.space(150);maximumLength:12;text:String(device.modelData[modelData.key]);enabled:!root.locked;foreground:root.bar.foreground;onEditingFinished:root.owner.edit(device.index,modelData.key,Number(text))}
          }
        }
      }
    }
    Text {width:parent.width;wrapMode:Text.Wrap;textFormat:Text.PlainText;text:"Only modes advertised by the connected monitor are accepted; no custom modelines. Save edits before reviewing. Changes here do not touch the desktop.";color:root.bar.foreground;font.family:root.bar.fontFamily;font.pixelSize:Style.font.bodySmall}
    Ui.Button {text:root.owner&&root.owner.draft?"Shell text: "+root.owner.draft.text_size+" px (cycle)":"Shell text";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!root.locked;onClicked:{var sizes=[9,10,11,12,14,16,20];root.owner.editText(sizes[(sizes.indexOf(root.owner.draft.text_size)+1)%sizes.length])}}
    Ui.Button {text:"Save draft";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!root.locked;onClicked:root.owner.save()}
    Ui.Button {text:"Review saved profile";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!root.locked&&!root.owner.draftDirty;onClicked:root.owner.inspect()}
  }
  Text {
    width:parent.width;wrapMode:Text.Wrap;textFormat:Text.PlainText;color:root.bar.foreground;font.family:root.bar.fontFamily;font.pixelSize:Style.font.bodySmall
    visible:!!root.owner&&!!root.owner.review
    text:visible?"REVIEW — "+root.owner.review.name+"\n"+root.owner.review.target.map(function(o){return o.identity.connector+": "+(o.enabled?o.width+"×"+o.height+" @ "+o.refresh+" Hz, "+o.scale+"×, "+o.x+","+o.y+", transform "+o.transform:"disabled")}).join("\n")+"\nShell text: "+root.owner.review.text_size+" px. Apply starts a 25-second recovery deadline; Keep only if this layout works.":""
  }
  Ui.Button {text:"Apply reviewed layout";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;visible:!!root.owner&&!!root.owner.review;enabled:!root.locked;onClicked:root.owner.apply()}
  Column {
    width:parent.width;visible:!!root.owner&&!!root.owner.data.pending;spacing:Style.space(6)
    Text {width:parent.width;wrapMode:Text.Wrap;textFormat:Text.PlainText;text:"Pending layout: Keep only after checking all displays. Restore uses identity/drift guards. Acknowledge clears the fence without restoring or replaying anything.";color:root.bar.foreground;font.family:root.bar.fontFamily;font.pixelSize:Style.font.body}
    Row {
      spacing:Style.space(6)
      Ui.Button {text:"Keep";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!!root.owner&&!root.owner.busy;onClicked:root.owner.terminal("keep")}
      Ui.Button {text:"Restore";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!!root.owner&&!root.owner.busy;onClicked:root.owner.terminal("restore")}
    }
    Ui.Button {text:"Acknowledge uncertainty (not restore)";foreground:root.bar.foreground;fontFamily:root.bar.fontFamily;focusable:true;enabled:!!root.owner&&!root.owner.busy;onClicked:root.owner.terminal("acknowledge")}
  }
}
