# Makefile for test, release, install and autostart

## Goal

One discoverable entry point for the tasks that are currently spread over
`tools/package_user.py`, `tools/install.py`, `tools/user_install.py` and
`tools/deploy_autostart.py`. The user asked for a Makefile that makes local
installation and source updates easier. The Makefile is a thin wrapper; it
adds no policy of its own.

## Evidence

- `tools/package_user.py --version V --build-dir B` prepares a release under
  ignored `work/user-releases/` and never installs or starts it.
- `~/.local/bin/omabuntu install <bundle> --apply` performs the transactional
  release switch; it refuses while the shell runs.
- `~/.local/bin/omabuntu start|stop|status` are identity-checked and use the
  session-lifetime grant.
- `tools/deploy_autostart.py plan|apply|remove` installs the login unit and
  the instance-wait helper; it never starts the service.
- The default build stage is `work/builds/20261024T001419.742301Z`, which is
  the verified stage the installed `.23` release was built from.
- The current login left no wallpaper because `hyprpaper` restarts with no
  target and nothing re-applies the recorded background. That is a separate
  defect; it is not part of this wrapping work.

## Gaps

- No Makefile and no single documented "update my local install" command.
- Release preparation, preflight, installation and autostart are separate
  documented commands with long argument lists.
- The background restore at login is missing (tracked separately).

## Shape

`Makefile` with `.DEFAULT_GOAL := help` and these targets:

- `help` – list targets, no side effects.
- `test` – `python3 -m unittest discover -s tests -v`.
- `doctor` – read-only `tools/doctor.py` report.
- `release VERSION=` – prepare a release, refuses an existing version.
- `preflight VERSION=` – read-only bundle check.
- `plan VERSION=` – read-only deployment plan.
- `install VERSION=` – install a prepared release with `--apply`, never
  starts it.
- `update VERSION=` – prepare if missing, stop the owned shell, install,
  start. This is the requested one-command local source update and is the
  only target that starts a desktop process.
- `start`, `stop`, `status` – thin `omabuntu` passthroughs.
- `autostart`, `autostart-remove` – deploy or remove the reviewed unit.

Every target that mutates the host prints what it does and keeps the existing
tools' refusals. No target installs packages, uses sudo, reloads the desktop
or publishes anything.

## Exclusions

Package installation, the guided installer's package plans, wallpaper restore
at login, commits, remotes, releases and any new service are excluded.

## Tasks

- [x] Write the plan.
- [x] Add `Makefile` with the targets above and version validation.
- [x] Add `tests/test_makefile.py` contracts for default goal, no implicit
      start in `install`, and the update ordering.
- [x] Document the Makefile in `README.md` and `docs/user-installation.md`.
- [x] Run the unit suite and update `WORKLOG.md` (482 tests pass).
