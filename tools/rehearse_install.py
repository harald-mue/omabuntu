"""Fixture install/update/rollback rehearsal. Never touches the host desktop.

The temporary home lives under ignored work/. Bar start, lock lookup and native
preflight are simulated. This is not a stock-VM acceptance result.
"""
import hashlib
import json
from pathlib import Path

import release_update
import session_activation
import session_config
import user_install

ROOT = Path(__file__).resolve().parents[1]


def bundle(parent, version):
    directory = parent / version
    directory.mkdir(parents=True)
    names = [*user_install.INCOMING, *user_install.SESSION_HELPERS]
    for name in dict.fromkeys(names):
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('fixture ' + version + ' ' + name)
        path.chmod(0o755 if name.startswith('runtime/bin/') else 0o444)
    meta = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': version,
            'autostart': False, 'lock_activation': False,
            'update_contract': release_update.contract(), 'files': user_install.file_manifest(directory)}
    (directory / 'release.json').write_text(json.dumps(meta))
    return directory


def run(base, native):
    """Run the lifecycle in base. Caller supplies the isolated XDG environment."""
    app = user_install.Installation(base / 'data/omabuntu', base / 'state/omabuntu', base / 'bin/omabuntu')
    first, second = bundle(base / 'bundles', 'v1'), bundle(base / 'bundles', 'v2')
    events = []
    app.running = lambda: None
    app.stop = lambda: events.append('stop')
    def start():
        events.append('start')
        raise ValueError('fixture start failure')
    app.start = start
    check = lambda bundle: {'status': 'passed'}
    locker = lambda: None
    installed = release_update.apply(app, release_update.review(app, first), release_update.approve_digest(
        release_update.review(app, first)), check=check, check_locker=locker)
    repeated = release_update.apply(app, release_update.review(app, first), release_update.approve_digest(
        release_update.review(app, first)), check=check, check_locker=locker)
    failed_plan = release_update.review(app, second, 'update', True, False)
    try:
        release_update.apply(app, failed_plan, release_update.approve_digest(failed_plan), check=check, check_locker=locker)
        failed = 'not-raised'
    except release_update.UpdateError:
        failed = 'restored'
    app.start = lambda: events.append('start-ok')
    updated_plan = release_update.review(app, second, 'update', False, False)
    updated = release_update.apply(app, updated_plan, release_update.approve_digest(updated_plan), check=check, check_locker=locker)
    updated_selected = app.selected()
    rolled_plan = release_update.review(app, mode='rollback')
    rolled = release_update.apply(app, rolled_plan, release_update.approve_digest(rolled_plan), check=check, check_locker=locker)
    home = base / 'home'
    home.mkdir()
    original_version = session_config.build_hyprbars.installed_version
    original_layouts = session_config.layouts
    session_config.build_hyprbars.installed_version = lambda: native
    session_config.layouts = lambda path=None: {'us'}
    try:
        session = session_config.plan(ROOT, home)
        if not session['blockers']:
            session_result = session_config.apply(session, session_config.guided.digest(session), check_stopped=lambda: None)
        else:
            session_result = {'status': 'blocked'}
        release = app.root / app.selected()
        plugin_path = release / 'native/hyprbars.so'
        plugin_path.parent.mkdir(parents=True, exist_ok=True)
        plugin_path.write_bytes(b'fixture-plugin')
        plugin_path.chmod(0o444)
        meta_path = release / 'release.json'
        meta = json.loads(meta_path.read_text())
        meta['files'] = user_install.file_manifest(release)
        meta_path.write_text(json.dumps(meta))
        plugin = plugin_path.read_bytes()
        descriptor = {'library_sha256': hashlib.sha256(plugin).hexdigest()}
        activation = session_activation.plan(ROOT, home, plugin_check=lambda release: descriptor, login_probe=lambda: False)
        if not activation['blockers']:
            activation_result = session_activation.apply(activation, session_activation.guided.digest(activation),
                                                        check_stopped=lambda: None, plugin_check=lambda release: descriptor)
        else:
            activation_result = {'status': 'blocked', 'blockers': activation['blockers']}
    finally:
        session_config.build_hyprbars.installed_version = original_version
        session_config.layouts = original_layouts
    return {'installed': installed['status'], 'repeated': repeated['status'], 'failed_start': failed,
            'selected_after_failure': app.selected() if failed == 'restored' else None,
            'updated': updated['status'], 'updated_selected': updated_selected,
            'rolled_back': rolled['status'], 'final_selected': app.selected(),
            'session': session_result['status'], 'activation': activation_result['status'],
            'events': events,
            'desktop_started': False, 'host_changed': False, 'vm_accepted': False}
