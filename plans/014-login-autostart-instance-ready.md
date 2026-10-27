# 014 — Wait for the Hyprland instance lock before login autostart

## Goal

Explain the 2026-10-26 20:59 fresh-login failure and stop it from aborting
`omabuntu start`, without adding crash supervision or changing the sealed
installed release in place.

## Evidence compared

- The enabled `omabuntu-shell.service` started at 20:59:41, in the same second
  uwsm reached `graphical-session.target`, and exited 1. Its only stdout was
  `Expecting value: line 2 column 1 (char 1)`. `omabuntu status` stayed
  `not-running`. No Quickshell process remained.
- That string is Python's `JSONDecodeError` for the payload `\n]`. Hyprland
  0.56.2 `hyprctl instances -j` builds `[` and, when the instance vector is
  empty, `pop_back()` removes it and appends `\n]`. The command still exits 0.
  A later call in this session returns a real JSON list.
- `hyprctl` lists only instance directories with a complete `hyprland.lock`.
  In the pinned Hyprland commit `efb50993780079460b0cbed1363e2166a2de1d9f`,
  `startCompositor()` forks `systemctl --user import-environment` and only
  then writes the lock. uwsm treats the imported `WAYLAND_DISPLAY` as
  readiness and starts this unit immediately. The sealed `.23` manager parses
  `hyprctl` once and aborts. Option A has no `Restart=`, so the shell stays
  down for the session.
- The environment check had already passed: a missing Hyprland session would
  have printed a different error. This is not the plan 013 control-group bug.
  The previous boot's `running.json` is stale and was not the parse failure.
- This is Ubuntu/Hyprland startup ordering, not an Omarchy behavior change.
  No upstream code or assets are imported.

## Current gaps

- The deployed unit calls `omabuntu start` with no readiness wait.
- The repository manager parses `hyprctl` once and surfaces the raw JSON error.
- `docs/user-installation.md` still says autostart has not been configured and
  that autostart is deliberately not enabled.
- The installed `.23` manager is sealed. Editing it in place would break
  release verification. A source fix does not change the host until a new
  release is approved.

## Safety constraints

- No `Restart=` and no crash supervision. A failed wait leaves the shell down
  until a manual `omabuntu start` or the next login.
- The wait is a bounded readiness poll for the instance lock, not a shell
  lifetime timer and not a timeout wrapper around Quickshell.
- Do not edit Hyprland configuration, other units, packages, or the installed
  release tree.
- Do not daemon-reload, enable, start, or replace the host unit in this plan's
  implementation. That remains a separate approval.
- Do not log out, exercise destructive rollback, or commit.

## Proposed shape

- Add `config/systemd/omabuntu-shell-wait.py`. It polls `hyprctl instances -j`
  until the live signature and Wayland socket appear, treating invalid JSON
  such as `]` as "not ready". Bound: 40 attempts, 0.25s apart.
- Point `ExecStartPre` at that script under `~/.config/systemd/user/`.
  `tools/deploy_autostart.py` installs and removes it with the unit. Apply
  still never starts the service.
- Teach `tools/user_install.py` the same parse-and-poll so a future release
  does not depend on the unit helper. The sealed `.23` copy is left untouched.
- Correct the installation document so it describes the enabled unit, this
  failed login, and the not-yet-deployed wait.

## Explicit exclusions

- No new user release, host install, daemon-reload, or `systemctl start`.
- No Hyprland patch, restart, or config edit.
- No supervision, lock, idle, suspend, or package change.
- Not a claim that the next login has been verified.

## Tasks

- [x] Record the diagnosis and the readiness-wait shape in this plan.
- [x] Add the wait script, unit `ExecStartPre`, deployer install/remove, and tests.
- [x] Teach the repository manager to retry an unready `hyprctl` instance list.
- [x] Correct the stale autostart statements in `docs/user-installation.md`.
- [x] Run `python3 -m unittest discover -s tests -v` and record the result in `WORKLOG.md`.
- [x] Ask before replacing the host unit or starting the shell. Approved
      replace only: unit and wait helper deployed, daemon reloaded, stale
      failure cleared, unit enabled and inactive. The shell was not started.
