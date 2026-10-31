#!/usr/bin/env python3
"""Interactive entry point for a verified public bundle; never rebuild it."""
import argparse
from pathlib import Path

import setup
import setup_guide
import user_install


def ask(message):
    return input(message + ' [y/N] ').strip().lower() in ('y', 'yes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    args = parser.parse_args()
    user_install.verify_bundle(args.bundle)
    # No source build here: system prerequisites and deployment stay separate.
    root = Path(__file__).resolve().parents[1]
    for mode, inspect in (('--ppa', setup_guide.ppa_stage),
                          ('--packages', lambda: setup_guide.packages_stage(setup_guide.default_installed)),
                          ('--font', lambda: setup_guide.font_stage(root))):
        stage = inspect()
        if stage['status'] != 'done':
            if not ask('Review and prepare prerequisites (' + mode + ')?'):
                raise SystemExit('Cancelled; published bundle not installed.')
            if setup.main([mode, '--apply']) != 0:
                raise SystemExit('Prerequisite stage failed; published bundle not installed.')
    installation = user_install.Installation(*user_install.defaults())
    options = ['--bundle', str(args.bundle), '--apply']
    if installation.selected():
        options.append('--update')
    if installation.running() is not None:
        if not ask('Allow stopping and restarting the recorded bar for this update?'):
            raise SystemExit('Cancelled; running bar left alone.')
        options.append('--restart-bar')
    result = setup.main(options)
    if result:
        raise SystemExit(result)
    print('Application installed. Your personal Hyprland configuration was preserved.')
    print('Generic session and login activation are separate opt-in steps; see docs/installer.md.')
    # Keep the installed release: do not leave references into the temporary download.


if __name__ == '__main__':
    main()
