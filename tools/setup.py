#!/usr/bin/env python3
"""Styled setup preview and reviewed prepared-release installation/update.

Fresh-system/PPA provisioning is still gated. A prepared local --bundle can
be applied explicitly, using verified staging and bar-start failure rollback.
No package changes, source fetches or state migrations are performed here.
"""
import argparse
import contextlib
import fcntl
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import build_runtime
import download_backgrounds
import omabuntu
import setup_ui
import user_install
import release_update
import bootstrap_sources
import bootstrap_packages
import bootstrap_build
import desktop_font
import session_config
import session_activation
import setup_guide
import source_update
import state_schema
import package_closure
import acceptance
import rehearse_install
import install as guided

ROOT = Path(__file__).resolve().parents[1]


def source_readiness(root):
    try:
        _, sources = build_runtime.load_inputs(root)
        record = json.loads((root / 'upstream/theme-backgrounds.json').read_text())
        artwork = download_backgrounds.entries(record)
        return {'ok': True, 'runtime_sources': sorted(sources), 'artwork_files': len(artwork),
                'artwork_bytes': sum(item['bytes'] for item in artwork)}
    except (OSError, ValueError, build_runtime.BuildError):
        return {'ok': False, 'error': 'Source or artwork lock is missing or invalid'}


def installation_readiness():
    try:
        installation = user_install.Installation(*user_install.defaults())
        current = installation.selected()
        previous = installation.selected('previous')
        return {'ok': True, 'installed': current is not None,
                'previous_available': previous is not None}
    except (OSError, ValueError):
        return {'ok': False, 'error': 'Existing installation integrity needs review'}


def inspect(mode='install', root=ROOT, os_info=None, architecture=None, which=None, installation=None):
    """Collect narrow readiness data without network, writes or subprocesses."""
    system = omabuntu.read_os_release() if os_info is None else os_info
    arch = platform.machine() if architecture is None else architecture
    lookup = shutil.which if which is None else which
    target = system.get('status') == 'ok' and system.get('values', {}).get('ID') == 'ubuntu' \
        and system.get('values', {}).get('VERSION_ID') == '26.04' and arch == 'x86_64'
    source = source_readiness(root)
    installed = installation_readiness() if installation is None else installation
    blockers = []
    if not target:
        blockers.append('Fresh-install target is Ubuntu 26.04 on x86_64')
    if not source['ok']:
        blockers.append(source['error'])
    if not installed['ok']:
        blockers.append(installed['error'])
    if mode in ('update', 'rollback') and not installed.get('installed'):
        blockers.append('No verified Omabuntu installation was found')
    if mode == 'rollback' and not installed.get('previous_available'):
        blockers.append('No verified previous release is available')
    blockers.extend([
        'Complete stock-machine dependency closure still needs clean-target verification',
        'Use --guide for the next implemented local stage; it does not start a session',
        'Native first-login and clean-VM acceptance are pending',
    ])
    return {'schema_version': 1, 'mode': mode, 'status': 'plan-only',
            'ready_to_apply': False, 'changes_made': False,
            'target_supported': target, 'sources': source, 'installation': installed,
            'tools_present': {name: lookup(name) is not None for name in
                              ('git', 'apt-get', 'dpkg-query', 'gpg', 'gpgv', 'cmake', 'ninja', 'bwrap')},
            'blockers': blockers,
            'artwork_notice': download_backgrounds.NOTICE}


def display(plan, console):
    console.welcome({'install': 'Installation plan', 'update': 'Update plan', 'rollback': 'Rollback plan'}[plan['mode']])
    console.line('  PREVIEW ONLY - no system changes, downloads or desktop restart.\n')
    console.step(1, 'Your Ubuntu base', 'OK' if plan['target_supported'] else 'BLOCKED',
                 'Supported target: Ubuntu 26.04 / x86_64. GNOME stays available.')
    source = plan['sources']
    console.step(2, 'Reviewed sources', 'OK' if source['ok'] else 'BLOCKED',
                 'Runtime and artwork source locks validated as data.' if source['ok'] else source['error'])
    if source['ok']:
        size = source['artwork_bytes'] / 1000000
        console.step(3, 'Make it yours', 'PLANNED',
                     '%d backgrounds/previews, %.1f MB from pinned upstream.\nVerified downloads are reused; your images are kept.' %
                     (source['artwork_files'], size))
    else:
        console.step(3, 'Make it yours', 'BLOCKED', 'Artwork source lock must pass before downloads.')
    console.step(4, 'Packages and PPA', 'CHECK',
                 'Review cppiber/hyprland, package origins and exact APT simulation.\nNo automatic system upgrade and no package removals.')
    console.step(5, 'Build, verify, install', 'PLANNED',
                 'Run ./install.sh --guide for the next local stage.\nIt never starts Hyprland, installs packages or loads a plugin.')
    console.step(6, 'Updates without losing your setup', 'PLANNED',
                 'Keep city, defaults, theme and private monitor configuration.\nKeep the previous release; application rollback is not APT rollback.')
    console.step(7, 'Ready to apply?', 'BLOCKED',
                 'This entry point is not a working stock-Ubuntu installer yet.\nUse this preview to follow readiness, not as installation acceptance.')
    console.line('  Remaining gates:')
    for blocker in plan['blockers']:
        console.line('    - ' + blocker)
    console.line()
    console.line('  Next: docs/fresh-installation.md and plans/043-fresh-install-and-updates.md')
    console.line('  No lock, capture, logout, reboot or credential collection.\n')


def display_release(plan, console):
    console.welcome('Local release ' + plan['operation'])
    console.line('  Prepared bundle only - no PPA, package or Hyprland session changes.\n')
    console.step(1, 'Verified release', 'OK', 'Version: ' + plan['version'])
    console.step(2, 'User state', 'CHECK' if plan['legacy_state'] else 'OK',
                 'Legacy state explicitly acknowledged; no migration will run.' if plan['legacy_state']
                 else 'Matching state contract; preferences and private configuration are kept.')
    console.step(3, 'Prepare before switching', 'PLANNED',
                 'Runtime/host preflight, complete staging, control lock and backup journal.')
    console.step(4, 'Bar lifetime', 'PLANNED',
                 'Stop/start only the recorded bar; restore the previous release on startup failure.'
                 if plan['restart_bar'] else 'No bar start or restart is approved.')
    console.line('  Approval digest: ' + release_update.approve_digest(plan))
    console.line('  No changes yet. --apply asks for confirmation; --approve DIGEST supports explicit automation.\n')


def recover_stage(args):
    installation = user_install.Installation(*user_install.defaults())
    reviewed = release_update.recover_review(installation)
    digest = guided.digest(reviewed)
    if args.json and not args.apply:
        print(json.dumps({'approval': digest, 'plan': reviewed}, indent=2))
    elif not args.json:
        console = setup_ui.Console(plain=args.plain)
        console.welcome('Recover an interrupted update')
        console.step(1, 'Journal', 'CHECK', reviewed['journal_status'] + ' -> ' + reviewed['action'])
        console.step(2, 'Prestate', 'OK' if not reviewed['blockers'] else 'BLOCKED',
                     'Restore the recorded selectors and launcher. The new release is not resumed.')
        console.step(3, 'Bar', 'CHECK' if args.restart_bar else 'OK',
                     'Start the previously running bar only with --restart-bar.' if args.restart_bar else 'No bar start. A running bar blocks selector changes.')
        console.line('  Approval digest: ' + digest)
        for blocker in reviewed['blockers']:
            console.line('  BLOCKED: ' + blocker)
    if reviewed['blockers']:
        return 1
    if not args.apply:
        return 0
    approval = args.approve
    if approval is None:
        if args.json or not sys.stdin.isatty():
            raise ValueError('Noninteractive recovery requires --approve DIGEST')
        if input('  Restore the interrupted update prestate without resuming it? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('  Cancelled. The journal remains unresolved.')
            return 0
        approval = digest
    result = release_update.recover(installation, reviewed, approval, args.restart_bar)
    print(json.dumps(result, indent=2) if args.json else '  Result: ' + result['status'])
    return 0


def local_release(args, parser):
    installation = user_install.Installation(*user_install.defaults())
    chosen = 'rollback' if args.rollback else 'update' if args.update else 'install'
    plan = release_update.review(installation, args.bundle, chosen, args.restart_bar, args.allow_legacy_state)
    digest = release_update.approve_digest(plan)
    if args.json:
        if not args.apply:
            print(json.dumps({'status': 'reviewed-not-applied', 'approval': digest, 'plan': plan}, indent=2))
    else:
        display_release(plan, setup_ui.Console(plain=args.plain))
    if not args.apply:
        return 0
    approval = args.approve
    if approval is None:
        if args.json or not sys.stdin.isatty():
            raise ValueError('Noninteractive apply requires --approve DIGEST from the exact reviewed plan')
        answer = input('  Apply this local release plan? [y/N] ').strip().lower()
        if answer not in ('y', 'yes'):
            print('  Cancelled. No release or desktop changes.')
            return 0
        approval = digest
    if args.json:
        # The legacy manager may print wallpaper restore information. Keep one
        # JSON document on stdout rather than mixing diagnostics into it.
        with contextlib.redirect_stdout(io.StringIO()):
            result = release_update.apply(installation, plan, approval)
    else:
        result = release_update.apply(installation, plan, approval)
    print(json.dumps(result, indent=2) if args.json else '\n  Release result: ' + result['status'])
    return 0


def session_stage(args):
    reviewed = session_config.plan(ROOT, keyboard=args.keyboard_layout, manual_lock=args.manual_lock,
                                  adopt_managed=args.adopt_managed)
    digest = guided.digest(reviewed)
    if args.json:
        if not args.apply:
            print(json.dumps({'approval': digest, 'plan': reviewed}, indent=2))
    else:
        console = setup_ui.Console(plain=args.plain)
        console.welcome('Prepare your Hyprland session')
        console.step(1, 'Generic profile', 'PLANNED',
                     'Auto-position monitors at scale 1, menu/workspace/window shortcuts,\nand release-local screenshot/minimize helpers. No private monitor export.')
        console.step(2, 'Your configuration', 'CHECK',
                     'Unowned profiles and edited owned modules are never overwritten.\nThe main entry stays editable; keyboard choice is preserved on updates.')
        console.step(3, 'No session activation', 'OK',
                     'No autostart, plugin load, compositor reload, lock or capture.\nApply only after all user Hyprland sessions have ended.')
        if reviewed['manual_lock']:
            console.step(4, 'Manual lock shortcut', 'CHECK',
                         'Explicit opt-in only: confirm authentication and recovery yourself first.\nThe installer never tests locking or changes PAM.')
        console.line('  Keyboard layout: ' + reviewed['keyboard_layout'])
        console.line('  Approval digest: ' + digest)
        for blocker in reviewed['blockers']:
            console.line('  BLOCKED: ' + blocker)
    if reviewed['blockers']:
        return 1
    if not args.apply:
        return 0
    approval = args.approve
    if approval is None:
        if args.json or not sys.stdin.isatty():
            raise ValueError('Noninteractive session setup requires --approve DIGEST')
        if input('  Write the reviewed configuration for your next Hyprland login? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('  Cancelled. No session configuration changes.')
            return 0
        approval = digest
    result = session_config.apply(reviewed, approval)
    print(json.dumps(result, indent=2) if args.json else '  Result: ' + result['status'])
    return 0


def activation_stage(args):
    choice = True if args.enable_login else False if args.disable_login else None
    reviewed = session_activation.plan(ROOT, enable_login=choice)
    digest = guided.digest(reviewed)
    if args.json and not args.apply:
        print(json.dumps({'approval': digest, 'plan': reviewed}, indent=2))
    elif not args.json:
        console = setup_ui.Console(plain=args.plain)
        console.welcome('Prepare next login')
        console.step(1, 'Plugin and titlebar', 'PLANNED',
                     'Write a guarded load of the immutable release library and the reviewed titlebar rules.\nNothing is loaded or reloaded now.')
        console.step(2, 'Wallpaper splash', 'PLANNED',
                     'Disable only the hyprpaper splash. A missing wallpaper choice can be recorded for next login.\nNo daemon start or service change.')
        console.step(3, 'Login hand-off', 'CHECK' if choice else 'OK',
                     'Enable the existing oneshot user unit without starting it.' if choice is True else
                     'Disable the login unit without stopping a running shell.' if choice is False else
                     'Leave login enablement unchanged. Pass --enable-login to opt in.')
        console.line('  Approval digest: ' + digest)
        for blocker in reviewed['blockers']:
            console.line('  BLOCKED: ' + blocker)
    if reviewed['blockers']:
        return 1
    if not args.apply:
        return 0
    approval = args.approve
    if approval is None:
        if args.json or not sys.stdin.isatty():
            raise ValueError('Noninteractive activation requires --approve DIGEST')
        if input('  Write next-login files without starting anything? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('  Cancelled. No activation changes.')
            return 0
        approval = digest
    result = session_activation.apply(reviewed, approval)
    print(json.dumps(result, indent=2) if args.json else '  Result: ' + result['status'])
    return 0


def install_ready_release(command):
    marker = '--bundle '
    if marker not in command:
        raise ValueError('No release bundle is ready to install')
    bundle = Path(command.split(marker, 1)[1].split(' --', 1)[0].strip())
    installation = user_install.Installation(*user_install.defaults())
    current = installation.selected()
    restart = '--restart-bar' in command
    if restart and input('  Restart the recorded bar and switch to this release? [y/N] ').strip().lower() not in ('y', 'yes'):
        print('  Cancelled. The running bar was left alone.')
        return 0
    mode = 'update' if current else 'install'
    plan = release_update.review(installation, bundle, mode, restart, False)
    result = release_update.apply(installation, plan, release_update.approve_digest(plan))
    print('  Result: ' + result['status'] + ' (' + plan['version'] + ')')
    print('  Previous release remains available through ./install.sh --rollback.')
    return 0


def guide_stage(args):
    reviewed = setup_guide.review(ROOT, allow_system=args.allow_system)
    digest = guided.digest(reviewed)
    nxt = setup_guide.next_stage(reviewed) if reviewed['next'] else None
    if args.json and not args.apply:
        print(json.dumps({'approval': digest, 'plan': reviewed}, indent=2))
    elif not args.json:
        console = setup_ui.Console(plain=args.plain)
        console.welcome('Guided setup')
        console.line('  One stage at a time. System stages run only with --allow-system, and nothing starts the desktop.\n')
        labels = {'done': 'OK', 'apply': 'PLANNED', 'command': 'CHECK', 'blocked': 'BLOCKED', 'manual': 'CHECK'}
        for number, item in enumerate(reviewed['stages'], 1):
            console.step(number, item['id'], labels[item['status']], item['summary'])
        if nxt and nxt['command']:
            console.line('  Next command: ' + nxt['command'])
        console.line('  Approval digest: ' + digest)
        if (nxt and nxt['id'] == 'release' and nxt['status'] == 'apply' and sys.stdin.isatty()
                and input('  Install this prepared development release now? [y/N] ').strip().lower() in ('y', 'yes')):
            return install_ready_release(nxt['command'])
    if not args.apply:
        return 0 if nxt is None or nxt['status'] != 'blocked' else 1
    if nxt is None or nxt['status'] != 'apply':
        raise ValueError('Next step is not a local guide action: ' + (nxt['command'] if nxt else 'none'))
    approval = args.approve
    if approval is None:
        if args.json or not sys.stdin.isatty():
            raise ValueError('Noninteractive guide apply requires --approve DIGEST')
        if input('  Run only this stage: ' + nxt['id'] + '? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('  Cancelled. No stage was started.')
            return 0
        approval = digest
    runners = setup_guide.local_runners(ROOT)
    if args.allow_system:
        runners.update(setup_guide.system_runners())
    result = setup_guide.apply_next(reviewed, approval, lambda item: True, runners)
    print(json.dumps(result, indent=2) if args.json else '  Result: ' + result['status'] + ' (' + result['stage'] + ')')
    return 0


def rehearse_stage(args):
    import tempfile
    native = {'version': '0.56.2', 'commit': session_config.build_hyprbars.HYPRLAND_COMMIT, 'dirty': False}
    base = Path(tempfile.mkdtemp(prefix='rehearse-', dir=ROOT / 'work'))
    env = {'XDG_CONFIG_HOME': str(base / 'config'), 'XDG_DATA_HOME': str(base / 'data'),
           'XDG_STATE_HOME': str(base / 'state'), 'HYPRLAND_INSTANCE_SIGNATURE': ''}
    old = {key: os.environ.get(key) for key in env}
    os.environ.update(env)
    try:
        report = rehearse_install.run(base, native)
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    report['fixture'] = str(base)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        console = setup_ui.Console(plain=args.plain)
        console.welcome('Fixture rehearsal')
        console.step(1, 'Lifecycle', 'OK' if report['failed_start'] == 'restored' else 'BLOCKED',
                     'Install, rollback, session and activation ran in a temporary home.')
        console.step(2, 'Host', 'OK', 'No host desktop, package or session file was changed.')
        console.step(3, 'Not acceptance', 'CHECK', 'This is not a stock-VM or native-login result.')
        console.line('  Result: ' + report['installed'] + ' -> ' + report['final_selected'])
    return 0 if report['failed_start'] == 'restored' and report['rolled_back'] else 1


def acceptance_stage(args):
    reviewed = acceptance.review(ROOT)
    if args.json:
        print(json.dumps(reviewed, indent=2))
    else:
        console = setup_ui.Console(plain=args.plain)
        console.welcome('Stock-install gates')
        console.line('  Read only. This does not accept a native login or start the desktop.\n')
        labels = {'done': 'OK', 'blocked': 'BLOCKED', 'manual': 'CHECK'}
        for number, item in enumerate(reviewed['gates'], 1):
            console.step(number, item['id'], labels[item['status']], item['summary'])
        console.line('  Native login accepted: no')
    return 0 if reviewed['ready_for_native_login'] else 1


def closure_stage(args):
    summary = package_closure.review(ROOT)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        console = setup_ui.Console(plain=args.plain)
        console.welcome('Package closure review')
        console.step(1, 'Simulation', 'CHECK' if not summary['blockers'] else 'BLOCKED',
                     '%d direct additions, %d dependency additions, %d removals.' %
                     (len(summary['direct_additions']), len(summary['dependency_additions']), len(summary['removals'])))
        console.step(2, 'Upgrades', 'OK' if summary['upgrade_policy']['permitted'] else 'BLOCKED',
                     summary['upgrade_policy']['reason'])
        console.step(3, 'Not acceptance', 'CHECK', summary['note'])
        for blocker in summary['native_blockers']:
            console.line('  BLOCKED: ' + blocker)
    return 1 if summary['status'] == 'blocked' else 0


def schema_stage(args):
    installation = user_install.Installation(*user_install.defaults())
    current = None
    try:
        selected = installation.selected()
        if selected:
            meta = user_install.verify_bundle(installation.root / selected, installed=True)
            current = meta.get('update_contract', {}).get('user_state_schema')
    except (OSError, ValueError):
        current = None
    decision = state_schema.decision(current if type(current) is int else None, state_schema.CURRENT)
    files = state_schema.inventory(installation.state if installation.state.exists() else None)
    report = {'schema_version': 1, 'current': state_schema.CURRENT, 'installed': current,
              'decision': decision, 'known_files': files, 'writes_state': False}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        console = setup_ui.Console(plain=args.plain)
        console.welcome('User-state schema')
        console.step(1, 'Schema', 'OK', 'Current schema %d. No migration is registered or executed.' % state_schema.CURRENT)
        console.step(2, 'Rollback', 'OK' if decision['rollback_safe'] else 'BLOCKED',
                     'Same-schema rollback keeps preferences. A schema change needs a reviewed reverse migration.')
        console.step(3, 'Files', 'CHECK', '%d known state files exist. Contents are not printed or rewritten.' % len(files))
    if args.apply:
        raise ValueError('Schema policy has no apply step; it never rewrites user state')
    return 0


def source_stage(args):
    reviewed = source_update.review(ROOT)
    digest = guided.digest(reviewed)
    if args.json and not args.apply:
        print(json.dumps({'approval': digest, 'plan': reviewed}, indent=2))
    elif not args.json:
        console = setup_ui.Console(plain=args.plain)
        console.welcome('Reviewed source pins')
        console.step(1, 'Trust policy', 'CHECK', reviewed['policy'])
        console.step(2, 'No checkout changes', 'OK', 'No git fetch, reset, build, package install or desktop start.')
        cached = sum(1 for item in reviewed['sources'] if item['cache'].get('matches'))
        console.step(3, 'Pinned archives', 'PLANNED' if not reviewed['blockers'] else 'BLOCKED',
                     str(cached) + ' verified cache hits. --apply downloads only missing exact pins.')
        console.line('  Approval digest: ' + digest)
        for blocker in reviewed['blockers']:
            console.line('  BLOCKED: ' + blocker)
    if reviewed['blockers']:
        return 1
    if not args.apply:
        return 0
    approval = args.approve
    if approval is None:
        if args.json or not sys.stdin.isatty():
            raise ValueError('Noninteractive source fetch requires --approve DIGEST')
        if input('  Download missing pinned source archives into the private cache? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('  Cancelled. No download started.')
            return 0
        approval = digest
    result = source_update.apply(reviewed, approval)
    print(json.dumps(result, indent=2) if args.json else '  Result: ' + result['status'])
    return 0


def font_stage(args):
    reviewed = desktop_font.plan(ROOT)
    digest = guided.digest(reviewed)
    if args.json:
        if not args.apply:
            print(json.dumps({'approval': digest, 'plan': reviewed}, indent=2))
    else:
        console = setup_ui.Console(plain=args.plain)
        console.welcome('Desktop icon font')
        console.step(1, 'Pinned Nerd Font', 'OK',
                     'JetBrainsMono Nerd Font Regular, OFL 1.1. Download size: 2.5 MB.')
        console.step(2, 'User font registration', 'PLANNED',
                     'Install into a content-addressed user directory, retain old fonts\nand notices, then refresh the font cache. No sudo or desktop restart.')
        console.step(3, 'Your preferences', 'OK',
                     'GTK, terminal and saved Omabuntu font choices stay untouched.')
        console.line('  Approval digest: ' + digest)
        for blocker in reviewed['blockers']:
            console.line('  BLOCKED: ' + blocker)
    if reviewed['blockers']:
        return 1
    if not args.apply:
        return 0
    approval = args.approve
    if approval is None:
        if args.json or not sys.stdin.isatty():
            raise ValueError('Noninteractive font install requires --approve DIGEST')
        if input('  Download/install the pinned user font and refresh its cache? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('  Cancelled. No font installation.')
            return 0
        approval = digest
    parent = user_install.private_directory(ROOT / 'work/bootstrap')
    fd = os.open(parent / 'operation.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = desktop_font.apply(reviewed, approval)
    print(json.dumps(result, indent=2) if args.json else '  Result: ' + result['status'])
    return 0


def build_stage(args):
    plan = bootstrap_build.create_plan(ROOT, args.jobs or 4, not args.skip_artwork, args.release_version)
    digest = guided.digest(plan)
    if args.json:
        if not args.apply:
            print(json.dumps({'approval': digest, 'plan': plan}, indent=2))
    else:
        console = setup_ui.Console(plain=args.plain)
        console.welcome('Build a local release')
        console.step(1, 'Pinned sources', 'OK',
                     'Quickshell + cpptrace, Omasnap and hyprbars/exact Hyprland headers.\nVerify notices and archive hashes.')
        console.step(2, 'Build and verify', 'PLANNED',
                     'Compile in isolated sandboxes, check linkage/imports, then package.\nNo screenshot, desktop start, package installation or selector switch.')
        console.step(3, 'Artwork', 'PLANNED',
                     'Download/reuse verified backgrounds and previews.' if plan['artwork'] else 'Artwork explicitly skipped.')
        console.step(4, 'Scope', 'CHECK',
                     'Runtime, screenshot, ABI-checked plugin and font assets.\nFont registration uses --font --apply; session config is separate. No plugin loading.')
        console.line('  Release: ' + plan['version'])
        console.line('  Approval digest: ' + digest)
        for blocker in plan['blockers']:
            console.line('  BLOCKED: ' + blocker)
    if plan['blockers']:
        return 1
    if not args.apply:
        if not args.json:
            print('  Plan only. Pass --apply for explicitly approved downloads and builds.')
        return 0
    approval = args.approve
    if approval is None:
        if args.json or not sys.stdin.isatty():
            raise ValueError('Noninteractive build requires the exact --approve DIGEST')
        if input('  Download sources/artwork/font and build this release? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('  Cancelled. No build started.')
            return 0
        print('  Started. Long steps print a still-running line every 15 seconds.', flush=True)
        print('  Compiler output stays in work/*/logs, not in this terminal.', flush=True)
        approval = digest
    if args.json:
        with contextlib.redirect_stdout(io.StringIO()):
            result = bootstrap_build.apply(plan, approval)
        print(json.dumps(result, indent=2))
    else:
        result = bootstrap_build.apply(plan, approval)
        print('  Result: ' + result['status'])
        print('  Bundle: ' + result['bundle'])
        print('  Not installed or started.')
    return 0


def system_stage(args):
    """Explicit package/source stages, never implicit in the welcome preview."""
    parent = user_install.private_directory(ROOT / 'work')
    parent = user_install.private_directory(parent / 'bootstrap')
    fd = os.open(parent / 'operation.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.plan:
            path = args.plan.absolute()
            user_install.safe_parents(path.parent)
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError('Expected a bounded saved bootstrap plan')
            plan = user_install.read_json(path)
        else:
            case = user_install.private_directory(parent / user_install.stamp())
            plan = bootstrap_sources.prepare(case) if args.ppa else bootstrap_packages.prepare(case, base_only=args.base_only)
            path = case / ('plan.json' if args.ppa else 'package-plan.json')
        expected = 'omabuntu-ppa-plan' if args.ppa else 'omabuntu-bootstrap-packages'
        if not isinstance(plan, dict) or plan.get('kind') != expected:
            raise ValueError('Saved plan has the wrong source/package scope')
        if args.packages and plan.get('base_only') is not args.base_only:
            raise ValueError('Saved package plan scope differs from --base-only selection')
        digest = guided.digest(plan)
        if args.json:
            print(json.dumps({'approval': digest, 'path': str(path), 'plan': plan}, indent=2))
        else:
            console = setup_ui.Console(plain=args.plain)
            console.welcome('PPA preparation' if args.ppa else 'Package preparation')
            if args.ppa:
                console.step(1, 'Pinned PPA identity', 'OK', bootstrap_sources.REFERENCE)
                console.step(2, 'Signature checked', 'OK', plan['verified']['fingerprint'])
                console.step(3, 'Scoped source and key', 'PLANNED',
                             'Add only the fixed Omabuntu deb822/Signed-By paths.\nRefresh APT metadata, not packages. Other source files stay untouched.')
            else:
                transaction = plan['payload']['transaction']
                names = ', '.join(transaction['new'][:8]) or 'none'
                if len(transaction['new']) > 8:
                    names += ' and %d more' % (len(transaction['new']) - 8)
                console.step(1, 'Package transaction', 'CHECK',
                             '%d additions, %d existing changes, %d removals.\nAdditions: %s' %
                             (len(transaction['new']), len(transaction['upgraded_or_changed']), len(transaction['removed']), names))
                console.step(2, 'Review origins and resolved versions', 'CHECK',
                             'Full private policy, simulation and before-state are in the printed plan.\nNo blanket upgrade, removals or auto-yes.')
                console.step(3, 'Native service warning', 'CHECK',
                             'Ubuntu package maintainer scripts may activate system services.\nNo desktop start or explicit service restart is requested.')
            console.line('  Plan: ' + str(path))
            console.line('  Approval digest: ' + digest)
            for blocker in plan.get('blockers', []):
                console.line('  BLOCKED: ' + blocker)
        if plan.get('blockers'):
            return 1
        if not args.apply:
            if not args.json:
                print('  Review only. No system source or package changes.\n')
            return 0
        approval = args.approve
        if approval is None:
            if not sys.stdin.isatty():
                raise ValueError('Noninteractive apply requires the exact --approve DIGEST')
            answer = input('  Apply this source/package plan using sudo? [y/N] ').strip().lower()
            if answer not in ('y', 'yes'):
                print('  Cancelled. No system changes.')
                return 0
            approval = digest
        result = bootstrap_sources.apply(plan, approval) if args.ppa else bootstrap_packages.apply(plan, approval)
        print('  Result: ' + result['status'])
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--update', action='store_true', help='Review update readiness, or update an explicit prepared --bundle')
    mode.add_argument('--rollback', action='store_true', help='Review the verified previous application release; --apply is explicit')
    mode.add_argument('--recover-update', action='store_true', help='Review one interrupted update; --apply restores its prestate and does not resume it')
    mode.add_argument('--ppa', action='store_true', help='Download and verify a signed PPA plan; --apply explicitly writes the source/key and refreshes metadata')
    mode.add_argument('--session-config', action='store_true', help='Prepare a generic Hyprland profile; --apply writes only when no user Hyprland is running')
    mode.add_argument('--session-activate', action='store_true', help='Prepare next-login plugin, wallpaper and optional autostart files; never starts them')
    mode.add_argument('--guide', action='store_true', help='Show the next implemented stage; --apply runs only that stage')
    mode.add_argument('--package-closure', action='store_true', help='Simulate the package closure without installing packages')
    mode.add_argument('--acceptance', action='store_true', help='Read-only stock-install gates; never claims native-login acceptance')
    mode.add_argument('--rehearse', action='store_true', help='Run the install/update/rollback fixture without touching the host desktop')
    mode.add_argument('--source-update', action='store_true', help='Review pinned source archives; --apply fetches only those exact archives')
    mode.add_argument('--state-schema', action='store_true', help='Show the user-state schema policy; it never rewrites state')
    mode.add_argument('--font', action='store_true', help='Plan the pinned desktop icon font; --apply installs only a user font and refreshes its cache')
    mode.add_argument('--build-release', action='store_true', help='Plan pinned runtime/Omasnap builds; --apply downloads/builds/packages locally without deployment')
    mode.add_argument('--packages', action='store_true', help='Plan bootstrap packages using local APT policy; --apply explicitly installs the additive-only transaction')
    parser.add_argument('--keyboard-layout', help='With --session-config: XKB layout list; default keeps the receipt choice or starts with us')
    parser.add_argument('--adopt-managed', action='store_true', help='With --session-config: replace only an untouched omabuntu-managed snippet')
    lock_choice = parser.add_mutually_exclusive_group()
    lock_choice.add_argument('--enable-manual-lock', dest='manual_lock', action='store_true', default=None,
                             help='With --session-config: opt into the manual lock chord only after verifying authentication/recovery')
    lock_choice.add_argument('--disable-manual-lock', dest='manual_lock', action='store_false',
                             help='With --session-config: remove the managed manual-lock chord without locking')
    login = parser.add_mutually_exclusive_group()
    login.add_argument('--enable-login', action='store_true', help='With --session-activate: enable the user unit without starting it')
    login.add_argument('--disable-login', action='store_true', help='With --session-activate: disable the user unit without stopping a running shell')
    parser.add_argument('--jobs', type=int, choices=range(1, 9), metavar='1..8', help='Parallel build jobs with --build-release (default: 4)')
    parser.add_argument('--release-version', help='Optional release name with --build-release; otherwise derived from source/package inputs')
    parser.add_argument('--skip-artwork', action='store_true', help='With --build-release: explicitly omit downloaded wallpapers/previews')
    parser.add_argument('--base-only', action='store_true', help='With --packages: prepare only Ubuntu tools needed before PPA verification')
    parser.add_argument('--plan', type=Path, help='Reuse a saved --ppa/--packages plan with explicit approval')
    parser.add_argument('--check', action='store_true', help='Exit nonzero while any apply gate remains blocked')
    parser.add_argument('--plain', action='store_true', help='Disable ANSI colors')
    parser.add_argument('--json', action='store_true', help='Print machine-readable readiness without the banner')
    parser.add_argument('--bundle', type=Path, help='Explicit trusted local prepared release; no source download')
    parser.add_argument('--apply', action='store_true', help='Apply only the explicit reviewed release, source, package, build or font stage')
    parser.add_argument('--approve', help='Digest of the exact selected-stage plan; requires --apply')
    parser.add_argument('--allow-system', action='store_true', help='With --guide --apply: allow the next PPA or package stage only')
    parser.add_argument('--restart-bar', action='store_true', help='Explicit session-lifetime grant to stop/start only the recorded bar')
    parser.add_argument('--allow-legacy-state', action='store_true', help='Acknowledge an unversioned installed release; no migration is performed')
    args = parser.parse_args(argv)
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        parser.error('Run as your normal user, not with sudo')
    system = args.ppa or args.packages
    if (args.keyboard_layout is not None or args.manual_lock is not None or args.adopt_managed) and not args.session_config:
        parser.error('Keyboard/lock/adopt options require --session-config')
    if (args.enable_login or args.disable_login) and not args.session_activate:
        parser.error('Login enablement requires --session-activate')
    if args.session_activate and (args.bundle or args.restart_bar or args.allow_legacy_state or args.plan):
        parser.error('Activation cannot be combined with release/bar or saved-system-plan options')
    if args.allow_system and not args.guide:
        parser.error('--allow-system requires --guide')
    if args.guide and (args.bundle or args.restart_bar or args.allow_legacy_state or args.plan or args.enable_login or args.disable_login):
        parser.error('The guide cannot be combined with release, bar, system-plan or login-enablement options')
    if args.source_update and (args.bundle or args.restart_bar or args.allow_legacy_state or args.plan):
        parser.error('Source acquisition cannot be combined with release or saved-system-plan options')
    if args.session_config and (args.bundle or args.restart_bar or args.allow_legacy_state or args.plan):
        parser.error('Session preparation cannot be combined with release/bar or saved-system-plan options')
    if (args.jobs or args.release_version or args.skip_artwork) and not args.build_release:
        parser.error('Build options require --build-release')
    if args.font and (args.bundle or args.restart_bar or args.allow_legacy_state or args.plan):
        parser.error('Font preparation cannot be combined with release/bar or saved-system-plan options')
    if args.build_release and (args.bundle or args.restart_bar or args.allow_legacy_state or args.plan):
        parser.error('Build preparation cannot be combined with deployment/saved-system-plan options')
    if args.base_only and not args.packages:
        parser.error('--base-only requires --packages')
    if args.plan and not system:
        parser.error('--plan is only for --ppa or --packages')
    if system and (args.bundle or args.restart_bar or args.allow_legacy_state):
        parser.error('Source/package stages cannot be combined with release/bar options')
    if system and args.apply and args.json:
        parser.error('Source/package apply uses your terminal for sudo/APT; JSON is review-only')
    if args.rollback and args.bundle:
        parser.error('--rollback uses the previous release, not --bundle')
    if args.recover_update and (args.bundle or args.allow_legacy_state or args.plan):
        parser.error('Update recovery uses its journal, not a bundle or legacy acknowledgement')
    if args.approve and not args.apply:
        parser.error('--approve requires --apply')
    if args.apply and args.check:
        parser.error('--apply and --check cannot be combined')
    if args.recover_update:
        try:
            return recover_stage(args)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Update recovery blocked: ' + str(error), file=sys.stderr)
            return 1
    if args.session_config:
        try:
            return session_stage(args)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Session preparation blocked: ' + str(error), file=sys.stderr)
            return 1
    if args.rehearse:
        if args.apply:
            parser.error('--rehearse never applies to the host')
        try:
            return rehearse_stage(args)
        except (OSError, ValueError) as error:
            print('  Rehearsal blocked: ' + str(error), file=sys.stderr)
            return 1
    if args.acceptance:
        if args.apply:
            parser.error('--acceptance never applies or accepts a native login')
        try:
            return acceptance_stage(args)
        except (OSError, ValueError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Acceptance review blocked: ' + str(error), file=sys.stderr)
            return 1
    if args.package_closure:
        if args.apply:
            parser.error('--package-closure never installs packages')
        try:
            return closure_stage(args)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Package closure blocked: ' + str(error), file=sys.stderr)
            return 1
    if args.state_schema:
        if args.apply:
            parser.error('--state-schema has no apply step')
        try:
            return schema_stage(args)
        except (OSError, ValueError, state_schema.SchemaError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Schema policy blocked: ' + str(error), file=sys.stderr)
            return 1
    if args.source_update:
        try:
            return source_stage(args)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Source update blocked: ' + str(error), file=sys.stderr)
            return 1
    if args.guide:
        try:
            return guide_stage(args)
        except (OSError, ValueError, subprocess.SubprocessError, build_runtime.BuildError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Guide blocked: ' + str(error), file=sys.stderr)
            return 1
    if args.session_activate:
        try:
            return activation_stage(args)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Activation blocked: ' + str(error), file=sys.stderr)
            return 1
    if args.font:
        try:
            return font_stage(args)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Font preparation blocked: ' + str(error), file=sys.stderr)
            return 1
    if args.build_release:
        try:
            return build_stage(args)
        except (OSError, ValueError, build_runtime.BuildError, subprocess.SubprocessError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Build preparation blocked: ' + str(error), file=sys.stderr)
            return 1
    if system:
        try:
            return system_stage(args)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            print('  Source/package preparation blocked: ' + str(error), file=sys.stderr)
            return 1
    if (args.apply or args.restart_bar or args.allow_legacy_state) and not (args.bundle or args.rollback):
        parser.error('A prepared --bundle, --rollback or --guide is required for apply')
    if args.bundle or args.rollback:
        try:
            return local_release(args, parser)
        except (OSError, ValueError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Release operation blocked: ' + str(error), file=sys.stderr)
            return 1
    if not args.update and not args.check and not args.json:
        try:
            return guide_stage(args)
        except (OSError, ValueError, subprocess.SubprocessError, build_runtime.BuildError) as error:
            if args.json:
                print(json.dumps({'status': 'blocked', 'message': str(error)}))
            else:
                print('  Guide blocked: ' + str(error), file=sys.stderr)
            return 1
    chosen = 'update' if args.update else 'install'
    plan = inspect(chosen)
    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        display(plan, setup_ui.Console(plain=args.plain))
    return 1 if args.check and not plan['ready_to_apply'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
