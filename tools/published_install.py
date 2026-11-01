#!/usr/bin/env python3
"""Interactive entry point for a verified public bundle; never rebuild it."""
import argparse
from pathlib import Path
import subprocess

import bootstrap_packages
import install as guided
import plugin_manager
import native_transition
import session_activation
import session_config
import user_artwork

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
    print('The exact package review asks once; declining it defers only this optional build scope.')
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
        keyboard = input('XKB keyboard layout [' + reviewed['keyboard_layout'] + '], or skip: ').strip()
        if keyboard.lower() == 'skip':
            print('Generic profile deferred; existing configuration preserved.')
            return
        keyboard = keyboard or reviewed['keyboard_layout']
        apply_stage(['--session-config', '--keyboard-layout', keyboard, '--apply'])
        if not session_config.locations()[2]['receipt'].is_file():
            return  # The inner review can also be cancelled.
    activation = session_activation.plan(root)
    if activation['blockers']:
        print('Next-login file preparation deferred: ' + '; '.join(activation['blockers']))
        return
    if not activation.get('changes') and 'changes' in activation:
        print('Next-login files already current; no repeated grant questions.')
        return
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
            ready = native_transition.manager_ready(plugin_manager.policy(root), app.state, allow_unloaded=True)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            print('Existing manager reuse requires review: ' + str(error))
        else:
            print('Existing exact manager build verified; no rebuild or reconciliation needed.')
            if ready['loaded']:
                print('Existing live hyprbars activation preserved; no duplicate enable/load.')
            elif reviewed['receipt_before'].get('activated') is True:
                print('Repair available: the verified enabled hyprbars is not loaded in this session.')
                apply_stage(['--plugins-repair', '--apply'])
            else:
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
    apply_stage(['--plugins', '--apply'])
    # The reviewed inner action can be declined; no receipt means no load offer.
    app = user_install.Installation(*user_install.defaults())
    if not (app.state / 'hyprpm.json').is_file():
        print('Plugin preparation deferred; no build receipt, so no activation is offered.')
        return
    activation = plugin_manager.plan(root, action='activate')
    if activation['blockers']:
        print('Plugin live activation deferred: ' + '; '.join(activation['blockers']))
        return
    apply_stage(['--plugins-activate', '--apply'])
    print('No full configuration reload was performed. Unapplied titlebars remain deferred until an approved rules action or configured next login.')


def offer_artwork(installation):
    """Offer the pinned private theme artwork once when the release has none."""
    selected = installation.selected()
    if selected is None:
        return
    bundled = installation.root / selected / 'config/menu/backgrounds'
    if bundled.is_dir() and not bundled.is_symlink():
        return  # Release-local artwork wins; no private download needed.
    try:
        reviewed = user_artwork.plan()
    except (OSError, ValueError) as error:
        print('Theme artwork check deferred: ' + str(error))
        return
    if not reviewed['missing']:
        print('Theme backgrounds/previews already downloaded privately; menus can use them.')
        return
    if not ask('Download the pinned Omarchy theme backgrounds/previews into your private user directory? %d files, %d bytes; they stay local, releases ship artwork-free' % (
            len(reviewed['missing']), reviewed['bytes'])):
        print('Theme artwork deferred. Menus stay without Omarchy backgrounds; rerun this installer to retry.')
        return
    try:
        user_artwork.apply(reviewed, guided.digest(reviewed),
                           progress=user_artwork.terminal_progress)
    except (OSError, ValueError) as error:
        print('Theme artwork download failed; menus stay without Omarchy backgrounds: ' + str(error))
        return
    print('Theme backgrounds/previews downloaded privately. Menus can list them after this installer run.')


def manager_reusable(root, installation):
    if installation.selected() is None:
        return False
    try:
        native_transition.manager_ready(plugin_manager.policy(root), installation.state, allow_unloaded=True)
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return True


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
            options = [mode, '--apply'] + (['--runtime-only'] if mode == '--packages' else [])
            if setup.main(options) != 0:
                raise SystemExit('Prerequisite stage failed; published bundle not installed.')
            if inspect()['status'] != 'done':
                raise SystemExit('Prerequisite deferred; application deployment not attempted.')
    installation = user_install.Installation(*user_install.defaults())
    prerequisites_ready = True
    if management is not None and not manager_reusable(root, installation):
        prerequisites_ready = offer_plugin_packages()
    options = ['--bundle', str(args.bundle), '--apply']
    unchanged = False
    if installation.selected():
        options.append('--update')
        installed = user_install.verify_bundle(installation.root / installation.selected(), installed=True)
        unchanged = isinstance(incoming, dict) and installed == incoming
        old_target = installed.get('update_contract', {}).get('native_target')
        new_target = incoming.get('update_contract', {}).get('native_target')
        if old_target == native_transition.FROM and new_target == native_transition.TO:
            if not ask('Review the explicit 0.56.2 to 0.57.0 application handoff? The new compositor and verified manager build must already be ready; no profile/login migration'):
                raise SystemExit('Native application handoff deferred; existing application preserved.')
            options.append('--migrate-native')
    if not unchanged and installation.running() is not None:
        # This is a proposed scope, not consent: the inner reviewed transaction
        # explicitly asks about deployment plus this recorded bar restart once.
        options.append('--restart-bar')
    if unchanged:
        print('Verified application already current; skipping deployment/restart and checking repair needs.')
    else:
        result = setup.main(options)
        if result:
            raise SystemExit(result)
        if isinstance(incoming, dict):
            selected = installation.selected()
            if selected is None or user_install.verify_bundle(installation.root / selected, installed=True) != incoming:
                print('Application deployment deferred; existing state preserved. No follow-up desktop actions.')
                return
    print('Application installed. Your personal Hyprland configuration was preserved.')
    print('Generic session and login activation are separate opt-in steps; see docs/installer.md.')
    offer_artwork(installation)
    if management is not None:
        if manager_reusable(root, installation):
            print('Verified manager build reused; no compiler packages or rebuild are needed.')
        offer_session(root)
        offer_plugins(root, prerequisites_ready=prerequisites_ready)
        print('Application installation is not native/titlebar acceptance; deferred stages remain explicit.')
        print('To continue deferred steps later, rerun the same install.sh entry point. No temporary-cache commands are needed.')
    # Keep the installed release: do not leave references into the temporary download.


if __name__ == '__main__':
    main()
