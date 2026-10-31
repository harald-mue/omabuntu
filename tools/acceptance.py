"""Read-only stock-install gates. This command never accepts a native login.

It does not install packages, fetch sources, start Hyprland, load a plugin or
rewrite configuration. A passing automated gate is not VM or visual acceptance.
"""
import os

import desktop_font
import session_activation
import session_config
import setup_guide
import user_install

ROOT = setup_guide.ROOT


def gate(identifier, status, summary):
    if status not in ('done', 'blocked', 'manual'):
        raise ValueError('Invalid acceptance gate')
    return {'id': identifier, 'status': status, 'summary': summary}


def host_gate():
    item = setup_guide.host_stage()
    return gate('host', 'done' if item['status'] == 'done' else 'blocked', item['summary'])


def ppa_gate():
    item = setup_guide.ppa_stage()
    return gate('ppa', 'done' if item['status'] == 'done' else 'blocked', item['summary'] or item['command'])


def packages_gate():
    item = setup_guide.packages_stage(setup_guide.default_installed)
    return gate('packages', 'done' if item['status'] == 'done' else 'blocked', item['summary'])


def font_gate(root=ROOT):
    reviewed = desktop_font.plan(root)
    if reviewed['blockers']:
        return gate('font', 'blocked', reviewed['blockers'][0])
    if all(item['existed'] for item in reviewed['before'].values()):
        return gate('font', 'done', 'Pinned desktop font is registered.')
    return gate('font', 'blocked', 'Pinned desktop font is not registered. Use --font --apply.')


def bundle_gate(installation):
    selected = installation.selected()
    if selected is None:
        return gate('bundle', 'blocked', 'No verified Omabuntu release is installed.')
    release = installation.root / selected
    if (release / 'runtime/bin/omasnap').is_file() and (release / 'native/hyprbars.so').is_file():
        return gate('bundle', 'done', 'Installed release contains the screenshot tool and plugin artifact.')
    return gate('bundle', 'blocked', 'Installed release lacks the screenshot tool or plugin artifact.')


def session_gate(root=ROOT):
    reviewed = session_config.plan(root)
    if reviewed['blockers']:
        return gate('session', 'blocked', reviewed['blockers'][0])
    if reviewed['changes']:
        return gate('session', 'blocked', 'Generic session profile has unapplied changes.')
    return gate('session', 'done', 'Generic session profile is current.')


def activation_gate(root=ROOT):
    reviewed = session_activation.plan(root)
    if reviewed['blockers']:
        return gate('activation', 'blocked', reviewed['blockers'][0])
    if reviewed['changes']:
        return gate('activation', 'blocked', 'Next-login activation files have unapplied changes.')
    return gate('activation', 'done', 'Next-login files are prepared. Nothing has been started.')


def login_gate():
    return gate('native-login', 'manual', 'A real Hyprland login is not accepted by this tool.')


def review(root=ROOT, installation=None):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Review acceptance as your normal user')
    installation = user_install.Installation(*user_install.defaults()) if installation is None else installation
    checks = (
        ('host', host_gate), ('ppa', ppa_gate), ('packages', packages_gate),
        ('font', lambda: font_gate(root)), ('bundle', lambda: bundle_gate(installation)),
        ('session', lambda: session_gate(root)), ('activation', lambda: activation_gate(root)),
        ('native-login', login_gate),
    )
    gates = []
    for identifier, function in checks:
        try:
            item = function()
        except (OSError, ValueError) as error:
            item = gate(identifier, 'blocked', str(error))
        if item['id'] != identifier:
            raise ValueError('Acceptance gate identity differs')
        gates.append(item)
    return {'schema_version': 1, 'kind': 'omabuntu-acceptance', 'accepted': False,
            'starts_desktop': False, 'packages_installed': False, 'gates': gates,
            'ready_for_native_login': all(item['status'] == 'done' for item in gates if item['id'] != 'native-login')}
