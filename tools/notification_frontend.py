"""Sealed original notification closure and narrow Ubuntu service derivation."""
import hashlib
import json
from pathlib import Path

COMMIT = 'ac2690cd7be4f47e4a255f5e2e78d904d436b068'
NAMES = ('Service.qml', 'Toast.qml', 'DeedButton.qml', 'Delivery.js', 'Detect.js',
         'Icons.js', 'Layout.js', 'Markup.js', 'Security.js', 'Store.js')
AUTHORED = {
    'NotificationHost.qml': 'config/shell/preview/NotificationHost.qml',
    'Notifications/Actions.js': 'config/shell/preview/NotificationActions.js',
}
NOTICES = ('licenses/Omarchy-MIT.txt', 'licenses/Omapager-MIT.txt')
INPUTS = ('upstream/notifications.json', *NOTICES, *AUTHORED.values(),
          *('vendor/omarchy/shell/plugins/notifications/' + n for n in NAMES))


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Original notification source witness changed')
    return text.replace(old, new)


def service(data):
    text = data.decode()
    text = replace(text, 'import "Icons.js" as Icons',
                   'import "Icons.js" as Icons\nimport "Actions.js" as Actions')
    # A departing card no longer participates in layout. Its deed area can
    # collapse while placements are evaluated; feeding that transient height
    # back into land()/retarget() re-enters the readonly layout binding.
    text = replace(text, '  function noteHeight(key, h) {',
                   '  function noteHeight(key, h) {\n    if (!liveKeys[key] || leaving[key]) return')
    text = replace(text, '  property var shell: null',
                   '  property var shell: null\n  property string storageHelper: ""\n  property string actionError: ""')
    text = replace(text, '    Util.execArgv(actions[index].argv)',
                   '    if (!Actions.runArgv(actions[index].argv)) { actionError = "Notification command not admitted"; return }')
    text = replace(text, '    if (argv) {', '    if (argv && Actions.runArgv(argv)) {')
    text = replace(text, '      Util.execArgv(argv)',
                   '      // The reviewed argv action was issued above, once.')
    text = replace(text, '      else if (String(row.app || "")) Util.execArgv(["omarchy-hyprland-focus-app", String(row.app)])',
                   '      // No unreviewed helper/PATH fallback for an ambiguous application.')
    text = replace(text, '  readonly property string stateDir: Quickshell.env("HOME") + "/.local/state/omarchy/notifications"',
                   '  readonly property string stateDir: (Quickshell.env("OMABUNTU_STATE_HOME") || Quickshell.env("HOME") + "/.local/state/omabuntu") + "/notifications"')
    text = replace(text, '  // State, not cache, in ~/.local/state/omarchy/notifications/: live.json (on',
                   '  // State, not cache, in the private Omabuntu directory: live.json (on')
    text = replace(text, "  // Once at startup: the private directory and its files. Older layouts'\n  // leftovers are removed by a migration.",
                   '  // Once at startup: validate private state without repairing or migrating it.')
    start = text.index('    command: ["bash", "-c",', text.index('    id: storePrepare'))
    end = text.index('    onExited:', start)
    text = replace(text, text[start:end],
                   '    command: storageHelper ? ["/usr/bin/python3", "-B", storageHelper, "prepare"] : ["/usr/bin/false"]\n')
    text = replace(text, '  NotificationServer {\n    id: server',
                   '  Loader {\n    active: service.storeReady && service.liveLoaded && service.historyLoaded && service.quietLoaded\n    sourceComponent: Component { NotificationServer {\n    id: server')
    text = replace(text, '    onNotification: function(notification) { service.handleNotification(notification) }\n  }',
                   '    onNotification: function(notification) { service.handleNotification(notification) }\n    } }\n  }')
    text = replace(text, '  ShellIpc {', '  IpcHandler {')
    text = replace(text, '    target: "notifications"', '    target: "omabuntuNotifications"')
    text = replace(text, 'WlrLayershell.namespace: "omarchy-notifications"',
                   'WlrLayershell.namespace: "omabuntu-notifications"')
    return text.encode()


def bounded(root, path):
    relative = Path(path)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unsafe notification source path')
    target = Path(root) / relative
    if any(p.is_symlink() for p in (target, *target.parents)) or not target.is_file() or target.stat().st_size > 131072:
        raise ValueError('Require bounded regular notification source')
    return target.read_bytes()


def sources(root):
    meta = json.loads(bounded(root, 'upstream/notifications.json'))
    if (meta.get('schema_version') != 1 or meta.get('commit') != COMMIT
            or meta.get('repository') != 'https://github.com/omacom/omarchy'
            or meta.get('license') != 'MIT' or meta.get('notices') != list(NOTICES)
            or meta.get('activation') != 'separate-exclusive-owner-deployment-required'
            or set(meta.get('upstream', {})) != set(NAMES)
            or set(meta.get('authored', {})) != set(AUTHORED)):
        raise ValueError('Require reviewed notification profile')
    files = {}
    for name in NAMES:
        record = meta['upstream'][name]
        path = 'vendor/omarchy/shell/plugins/notifications/' + name
        if record.get('path') != path or record.get('source_path') != 'shell/plugins/notifications/' + name:
            raise ValueError('Notification origin changed')
        data = bounded(root, path)
        if hashlib.sha256(data).hexdigest() != record.get('sha256'):
            raise ValueError('Original notification bytes changed')
        files['Notifications/' + name] = service(data) if name == 'Service.qml' else data
    for name, path in AUTHORED.items():
        record = meta['authored'][name]
        data = bounded(root, path)
        if record.get('path') != path or record.get('sha256') != hashlib.sha256(data).hexdigest():
            raise ValueError('Notification adapter changed')
        files[name] = data
    for path in NOTICES:
        data = bounded(root, path)
        if meta.get('notice_hashes', {}).get(path) != hashlib.sha256(data).hexdigest():
            raise ValueError('Notification notice changed')
        files['Notifications/' + Path(path).name] = data
    files['Notifications/qmldir'] = b'Service 1.0 Service.qml\nToast 1.0 Toast.qml\nDeedButton 1.0 DeedButton.qml\n'
    actual = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    if actual != meta.get('staged'):
        raise ValueError('Notification derivation differs from review')
    return files
