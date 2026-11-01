#!/usr/bin/env python3
"""Interactive entry point for a verified public bundle; never rebuild it."""
import argparse
from pathlib import Path
import subprocess

import bootstrap_packages
import plugin_manager
import native_transition
import session_activation
import session_config

import setup
import setup_guide
import setup_ui
import user_install


def ask(message):
    return setup_ui.confirm(message)


def apply_stage(options):
    if setup.main(options) != 0:
        raise SystemExit('Reviewed setup stage failed; inspect its report before retrying.')


def review_plugin_packages():
    # Planning is read-only except for private reports; apply rechecks under its lock.
    root = Path(__file__).resolve().parents[1]
    parent = user_install.private_directory(root / 'work')
    parent = user_install.private_directory(parent / 'bootstrap')
    case = user_install.private_directory(parent / user_install.stamp())
    plan = bootstrap_packages.prepare(case, plugin_build_only=True)
    return plan, case / 'package-plan.json'


def offer_plugin_packages():
    stage = setup_guide.packages_stage(setup_guide.default_installed, plugin_build_only=True)
    if stage['status'] == 'done':
        return True
    print('Local hyprbars builds need their own compiler/header packages, not the Omabuntu application build chain.')
    print(stage['summary'])
    if not ask('Review and install these plugin-build prerequisites? This may request sudo'):
        print('Plugin build prerequisites deferred; application installation can continue without titlebars.')
        return False
    try:
        plan, path = review_plugin_packages()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('Optional plugin package review failed without applying packages: ' + str(error))
        blockers = ['Plugin package prerequisites could not be reviewed']
    else:
        blockers = plan['blockers']
        print('Plugin package review: ' + str(path))
        for blocker in blockers:
            print('  BLOCKED: ' + blocker)
    if blockers:
        print('No plugin packages applied. System upgrades are not permitted by this installer.')
        if not ask('Continue application installation with the optional plugin build deferred?'):
            raise SystemExit('Cancelled; application deployment not attempted.')
        return False
    # A failure after attempted application is not safe to downgrade to a deferral.
    apply_stage(['--packages', '--plugin-build-only', '--plan', str(path), '--apply'])
    ready = setup_guide.packages_stage(setup_guide.default_installed, plugin_build_only=True)['status'] == 'done'
    if not ready:
        print('Plugin prerequisites remain incomplete; plugin preparation deferred. Rerun this installer to revisit.')
    return ready


def offer_session(root):
    try:
        session_config.require_stopped()
        reviewed = session_config.plan(root)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('Session-file preparation deferred: ' + str(error))
        return
    if reviewed['blockers']:
        print('Session profile preserved: ' + '; '.join(reviewed['blockers']))
        return
    if reviewed['changes']:
        if not ask('Review a generic next-login profile? Existing private profiles are never merged'):
            print('Generic profile deferred. Rerun this installer to revisit; answer with y then Enter, not Shift+Enter.')
            return
        keyboard = input('XKB keyboard layout [' + reviewed['keyboard_layout'] + ']: ').strip() or reviewed['keyboard_layout']
        apply_stage(['--session-config', '--keyboard-layout', keyboard, '--apply'])
        if not session_config.locations()[2]['receipt'].is_file():
            return  # The inner review can also be cancelled.
    activation = session_activation.plan(root)
    if activation['blockers']:
        print('Next-login file preparation deferred: ' + '; '.join(activation['blockers']))
        return
    if ask('Review next-login titlebar and wallpaper files without starting anything?'):
        options = ['--session-activate', '--apply']
        if ask('Grant persistent receipt-checked hyprpm loading at future logins? No builds or sudo at login'):
            options.append('--enable-plugin-login')
        if ask('Enable the existing bar login unit without starting it now?'):
            options.append('--enable-login')
        apply_stage(options)


def offer_plugins(root, prerequisites_ready=True):
    try:
        reviewed = plugin_manager.plan(root)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('Plugin preparation deferred: ' + str(error))
        return
    if isinstance(reviewed.get('receipt_before'), dict):
        try:
            app = user_install.Installation(*user_install.defaults())
            ready = native_transition.manager_ready(plugin_manager.policy(root), app.state)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass  # A stale receipt is not readiness; preserve the normal guards.
        else:
            print('Existing exact manager build verified; no rebuild or reconciliation needed.')
            if ready['loaded']:
                print('Existing live hyprbars activation preserved; no duplicate enable/load.')
            elif ask('Review live hyprbars enable/load? Loading a plugin can crash this session'):
                apply_stage(['--plugins-activate', '--apply'])
            return
    if not prerequisites_ready:
        print('Plugin build deferred because its package prerequisites are incomplete. Rerun this installer to revisit.')
        return
    if reviewed['blockers']:
        print('Plugin preparation deferred: ' + '; '.join(reviewed['blockers']))
        print('Use a separately approved matching, plugin-free Hyprland session; no logout or reload was performed.')
        print('Rerun the same installer to continue; no internal plugin command is needed.')
        return
    if not ask('Review pinned hyprpm preparation? It downloads/builds locally and may request sudo'):
        return
    apply_stage(['--plugins', '--apply'])
    activation = plugin_manager.plan(root, action='activate')
    if activation['blockers']:
        print('Plugin live activation deferred: ' + '; '.join(activation['blockers']))
        return
    if ask('Review live hyprbars enable/load? Loading a plugin can crash this session'):
        apply_stage(['--plugins-activate', '--apply'])
        print('No full configuration reload was performed. Unapplied titlebars remain deferred until an approved rules action or configured next login.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    args = parser.parse_args()
    incoming = user_install.verify_bundle(args.bundle)
    # Never rebuild the published application. Local plugin compilation is optional.
    management = plugin_manager.bundle_policy(args.bundle)
    root = Path(__file__).resolve().parents[1]
    for mode, inspect in (('--ppa', setup_guide.ppa_stage),
                          ('--packages', lambda: setup_guide.packages_stage(setup_guide.default_installed, runtime_only=True)),
                          ('--font', lambda: setup_guide.font_stage(root))):
        stage = inspect()
        if stage['status'] != 'done':
            if not ask('Review and prepare prerequisites (' + mode + ')?'):
                raise SystemExit('Cancelled; published bundle not installed.')
            options = [mode, '--apply'] + (['--runtime-only'] if mode == '--packages' else [])
            if setup.main(options) != 0:
                raise SystemExit('Prerequisite stage failed; published bundle not installed.')
    prerequisites_ready = True
    if management is not None:
        prerequisites_ready = offer_plugin_packages()
    installation = user_install.Installation(*user_install.defaults())
    options = ['--bundle', str(args.bundle), '--apply']
    if installation.selected():
        options.append('--update')
        installed = user_install.verify_bundle(installation.root / installation.selected(), installed=True)
        old_target = installed.get('update_contract', {}).get('native_target')
        new_target = incoming.get('update_contract', {}).get('native_target')
        if old_target == native_transition.FROM and new_target == native_transition.TO:
            if not ask('Review the explicit 0.56.2 to 0.57.0 application handoff? The new compositor and verified manager build must already be ready; no profile/login migration'):
                raise SystemExit('Native application handoff deferred; existing application preserved.')
            options.append('--migrate-native')
    if installation.running() is not None:
        if not ask('Allow stopping and restarting the recorded bar for this update?'):
            raise SystemExit('Cancelled; running bar left alone.')
        options.append('--restart-bar')
    result = setup.main(options)
    if result:
        raise SystemExit(result)
    print('Application installed. Your personal Hyprland configuration was preserved.')
    print('Generic session and login activation are separate opt-in steps; see docs/installer.md.')
    if management is not None:
        offer_session(root)
        offer_plugins(root, prerequisites_ready=prerequisites_ready)
        print('Application installation is not native/titlebar acceptance; deferred stages remain explicit.')
        print('To continue deferred steps later, rerun the same install.sh entry point. No temporary-cache commands are needed.')
    # Keep the installed release: do not leave references into the temporary download.


if __name__ == '__main__':
    main()
