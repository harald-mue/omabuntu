"""Closed monitor-profile projections and Lua for Hyprland 0.57.0; no I/O."""
import copy
import hashlib
import json
import math
import re

TEXT_SIZES = (9, 10, 11, 12, 14, 16, 20)
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9 _.-]{0,47}\Z')
CONNECTOR = re.compile(r'[A-Za-z0-9_.-]{1,64}\Z')
MODE = re.compile(r'(\d{2,5})x(\d{2,5})@(\d{1,3}(?:\.\d{1,6})?)(?:Hz)?\Z')
FIELDS = {'identity','enabled','width','height','refresh','scale','x','y','transform'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def number(value, lo, hi):
    if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:
        raise ValueError('Invalid finite numeric field')
    return value


def text(value, maximum=128):
    if not isinstance(value,str) or len(value)>maximum or any(ord(c)<32 or 0x7f<=ord(c)<=0x9f or ord(c) in range(0x202a,0x202f) or ord(c) in range(0x2066,0x206a) for c in value):
        raise ValueError('Invalid display identity text')
    return value


def identity(m):
    name=text(m['name'],64)
    if not CONNECTOR.fullmatch(name):raise ValueError('Unsupported connector name')
    return {'connector':name, **{k:text(m.get(k,'') or '') for k in ('make','model','serial')}}


def key(i):
    if set(i)!={'connector','make','model','serial'}:raise ValueError('Unexpected identity fields')
    for v in i.values():text(v)
    if not CONNECTOR.fullmatch(i['connector']):raise ValueError('Invalid connector')
    # A unique manufacturer/model/serial survives connector reassignment. Otherwise
    # deliberately bind to the physical connector as well as make/model.
    return ('serial',i['make'],i['model'],i['serial']) if i['serial'] and i['serial'] not in ('Unknown','0') else ('connector',i['connector'],i['make'],i['model'])


def mode(value):
    match=MODE.fullmatch(value) if isinstance(value,str) else None
    if not match:raise ValueError('Only advertised numeric modes are supported')
    w,h,r=match.groups();number(int(w),64,32768);number(int(h),64,32768);number(float(r),1,999)
    return int(w),int(h),float(r)


def modes(m):
    result=[]
    for value in m.get('availableModes',[]):
        try:parsed=mode(value)
        except ValueError:continue
        if parsed not in result:result.append(parsed)
    return result[:256]


def snapshot(monitors):
    if not isinstance(monitors,list) or not 1<=len(monitors)<=16:raise ValueError('Expected one to sixteen connected outputs')
    result=[];seen=set()
    for m in monitors:
        i=identity(m);k=key(i)
        if k in seen:raise ValueError('Ambiguous duplicate display identity')
        seen.add(k)
        if m.get('mirrorOf',-1) not in (-1,'none','',None):raise ValueError('Mirroring requires a separate reviewed backend')
        if m.get('colorManagementPreset','srgb') not in ('srgb','') or m.get('vrr',False) or m.get('currentFormat','XRGB8888') not in ('XRGB8888','XBGR8888','ARGB8888','ABGR8888') or any(abs(m.get(k,1)-1)>1e-5 for k in ('sdrBrightness','sdrSaturation')):
            raise ValueError('Advanced color/bit-depth/VRR requires a separate reviewed monitor backend')
        active=not m.get('disabled',False)
        if active:
            w,h,r=int(m['width']),int(m['height']),float(m['refreshRate'])
        else:
            available=modes(m)
            if not available:raise ValueError('Disabled output has no advertised restorable mode')
            w,h,r=available[0]
        result.append({'identity':i,'enabled':active,'width':w,'height':h,'refresh':r,
                       'scale':m.get('scale',1) if active else 1,'x':m.get('x',0) if active else 0,
                       'y':m.get('y',0) if active else 0,'transform':m.get('transform',0) if active else 0})
    return sorted(result,key=lambda o:tuple(str(x) for x in key(o['identity'])))


def validate(profile, monitors=None):
    if not isinstance(profile,dict) or set(profile)!={'schema_version','name','outputs','text_size'} or type(profile['schema_version']) is not int or profile['schema_version']!=1:
        raise ValueError('Unexpected profile schema')
    if not isinstance(profile['name'],str) or not NAME.fullmatch(profile['name']):raise ValueError('Invalid profile name')
    if type(profile['text_size']) is not int or profile['text_size'] not in TEXT_SIZES:raise ValueError('Unsupported shell text size')
    outputs=profile['outputs']
    if not isinstance(outputs,list) or not 1<=len(outputs)<=16:raise ValueError('Invalid output count')
    seen=set();rects=[]
    inventory={key(identity(m)):m for m in monitors} if monitors is not None else None
    if inventory is not None and len(inventory)!=len(monitors):raise ValueError('Ambiguous inventory')
    for o in outputs:
        if not isinstance(o,dict) or set(o)!=FIELDS:raise ValueError('Unexpected output fields')
        k=key(o['identity'])
        if k in seen:raise ValueError('Duplicate profile identity')
        seen.add(k)
        if type(o['enabled']) is not bool:raise ValueError('Invalid enabled flag')
        for f in ('width','height'):number(o[f],64,32768)
        for f in ('x','y'):number(o[f],-65536,65536)
        for f in ('width','height','x','y','transform'):
            if type(o[f]) is not int:raise ValueError('Expected integer field')
        number(o['transform'],0,7);number(o['scale'],0.5,4);number(o['refresh'],1,999)
        if o['enabled']:
            w,h=o['width'],o['height']
            if o['transform']%2:w,h=h,w
            w,h=w/o['scale'],h/o['scale']
            if abs(w-round(w))>1e-5 or abs(h-round(h))>1e-5:raise ValueError('Nonintegral logical pixels')
            rects.append((o['x'],o['y'],w,h))
            if inventory is not None:
                m=inventory.get(k)
                if not m:raise ValueError('Output identity disappeared')
                allowed=modes(m)
                if not any(a==o['width'] and b==o['height'] and abs(r-o['refresh'])<=0.02 for a,b,r in allowed):raise ValueError('Mode not advertised by current output')
    if not rects:raise ValueError('Refusing to disable every output')
    if inventory is not None and seen!=set(inventory):raise ValueError('Connected topology differs; no partial/unknown-output apply')
    for i,a in enumerate(rects):
        for b in rects[i+1:]:
            if max(a[0],b[0])<min(a[0]+a[2],b[0]+b[2]) and max(a[1],b[1])<min(a[1]+a[3],b[1]+b[3]):raise ValueError('Output rectangles overlap')
    # Every active output must be pointer-reachable through an edge or corner.
    reached={0}
    while True:
        old=len(reached)
        for i,a in enumerate(rects):
            if i not in reached:continue
            for j,b in enumerate(rects):
                if max(a[0],b[0])<=min(a[0]+a[2],b[0]+b[2]) and max(a[1],b[1])<=min(a[1]+a[3],b[1]+b[3]):reached.add(j)
        if len(reached)==old:break
    if len(reached)!=len(rects):raise ValueError('Outputs have an unreachable gap')
    return copy.deepcopy(profile)


def bind(outputs, monitors):
    inventory={key(identity(m)):m['name'] for m in monitors}
    if len(inventory)!=len(monitors) or set(inventory)!={key(o['identity']) for o in outputs}:raise ValueError('Topology identity changed')
    return [dict(o,identity=dict(o['identity'],connector=inventory[key(o['identity'])])) for o in outputs]


def same(a,b):
    if {key(o['identity']) for o in a}!={key(o['identity']) for o in b}:return False
    other={key(o['identity']):o for o in b}
    for o in a:
        q=other[key(o['identity'])]
        if o['enabled']!=q['enabled']:return False
        if o['enabled'] and any(abs(o[f]-q[f])>(0.03 if f=='refresh' else 1e-5) for f in ('width','height','refresh','scale','x','y','transform')):return False
    return True


def program(output):
    probe=copy.deepcopy(output);probe['enabled']=True
    validate({'schema_version':1,'name':'Rule','outputs':[probe],'text_size':12})
    name=output['identity']['connector']
    if not CONNECTOR.fullmatch(name):raise ValueError('Invalid Lua output')
    fields='output = '+json.dumps(name)+', disabled = '+str(not output['enabled']).lower()
    if output['enabled']:
        fields+=', mode = '+json.dumps(f"{output['width']}x{output['height']}@{output['refresh']:.6f}")
        fields+=', position = '+json.dumps(f"{output['x']}x{output['y']}")+f", scale = {output['scale']}, transform = {output['transform']}"
    return 'hl.monitor({ '+fields+' }); return "ok"'


def topology(monitors):
    return digest(sorted([key(identity(m)) for m in monitors]))
