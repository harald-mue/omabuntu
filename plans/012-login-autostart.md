# 012 — Login autostart for the installed Omabuntu shell

## Goal

Make the installed Omabuntu shell start automatically when the user logs into
the existing Hyprland session, as a reviewed, backed-up, reversible user-level
deployment. This closes the gap documented in `docs/user-installation.md`
("No login autostart or service supervision has been configured"). The plan
covers only autostart preparation; no unit is enabled or started before the
user explicitly approves that step.

## Evidence compared

- Current host state (read-only checks, 2026-10-26):
  - `~/.local/bin/omabuntu status` reports current release
    `20261025-local.23`, `status: not-running`.
  - `~/.local/state/omabuntu/running.json` records
    `'lifetime': 'session', 'autostart': False`; no Quickshell process exists.
  - No autostart mechanism exists anywhere: `~/.config/autostart/` is absent,
    no omabuntu systemd user unit exists
    (`omabuntu-bar.service could not be found`), and `~/.config/hypr/hyprland.lua`
    contains no `exec`/`exec-once` for omabuntu (only the four persistent
    shell binds and the hyprbars snippet).
- Session stack: the Hyprland session is uwsm-managed
  (`wayland-wm@hyprland.desktop.service`, `wayland-session@hyprland.desktop.target`,
  `graphical-session.target` active, `wayland-session-xdg-autostart@hyprland.desktop.target`
  active). Logout via `uwsm stop` (bound to Super+Shift+Escape) tears the
  session down.
- Working precedent on this host: `/usr/lib/systemd/user/hyprpaper.service`
  (enabled and running) uses `PartOf=graphical-session.target`,
  `Requires=graphical-session.target`, `After=graphical-session.target`,
  `ConditionEnvironment=WAYLAND_DISPLAY`, `Slice=session.slice`,
  `WantedBy=graphical-session.target`. This is the shape a new unit should
  follow so it inherits the uwsm-imported Wayland environment and stops at
  logout.
- Installed manager contract (`~/.local/share/omabuntu/current/manager.py`):
  `start()` strictly validates a live Hyprland environment
  (`XDG_CURRENT_DESKTOP` contains hyprland, `HYPRLAND_INSTANCE_SIGNATURE`
  set, `WAYLAND_DISPLAY` matches `wayland-<n>` with a real socket, verified
  against `hyprctl instances -j`), refuses to start when another Quickshell
  process exists, waits for `Configuration Loaded` plus the session-grant
  marker in the startup log, and records
  `{'lifetime': 'session', 'autostart': False}` in `running.json`. That record
  is part of the reviewed, sealed release; it cannot and should not be edited
  in place on the host. It describes the manager's own nature, not the unit.
- Project policy: autostart is a distinct deployment approval gate, separate
  from session-lifetime grants, crash supervision, and lock/idle/suspend
  activation.

## Current gaps

- No user unit, no XDG autostart entry, and no Hyprland exec-once exists.
- The repository has no reviewed unit template and no test covering it.
- The installed manager records `autostart: False`; if autostart is adopted,
  the documentation and a future release should reflect the new deployment
  reality (the release contract field itself stays untouched).
- Crash supervision is explicitly not part of this plan (see exclusions).

## Safety constraints

- Diagnose before changing configuration; nothing is enabled or started by
  this plan. Enablement, daemon-reload, and any first start are separate
  explicit approval steps.
- Do not edit `~/.config/hypr/hyprland.lua`, `~/.config/hypr/hyprbars.lua`,
  or any desktop, lock, PAM, sudo, firewall, or security configuration.
- Do not touch `hyprpaper.service`, `hyprsunset.service`, or any existing
  unit; the new unit is additive and independently removable.
- No Hyprland reload or session transition is triggered by this work; the
  first real test happens at the user's own next logout/login.
- Preserve the manual workflow: `~/.local/bin/omabuntu start|stop|status`
  must keep working exactly as before; the unit only adds an automatic start
  at login.
- Rollback must be simple and complete: `systemctl --user disable` plus
  removing the unit file, with no residue in other configuration.
- Keep machine-specific logs and dumps out of this plan and the repository.

## Proposed shape

A single systemd user unit, `omabuntu-shell.service`, authored in the
repository (template under `tools/` or `config/` with a content test), then
deployed to `~/.config/systemd/user/` after approval:

- `ExecStart=/home-free absolute launcher invocation` resolving to
  `~/.local/bin/omabuntu start` (written with the real home path at deploy
  time or via a packaged template; no environment expansion in ExecStart).
- Unit wiring copied from the proven hyprpaper pattern:
  `PartOf=graphical-session.target`, `Requires=graphical-session.target`,
  `After=graphical-session.target`, `ConditionEnvironment=WAYLAND_DISPLAY`,
  `Slice=session.slice`, `WantedBy=graphical-session.target`.
- `Type=oneshot` for the manager invocation is not suitable because the
  manager exits after `start()` returns while the child Quickshell process
  keeps running; the unit must use `Type=oneshot` + `RemainAfterExit=no`
  semantics deliberately, or better, be a `Type=oneshot` unit whose only job
  is to hand the process off (the manager already backgrounds Quickshell with
  `start_new_session=True` and owns the `running.json` identity record).
  The exact Type decision is part of implementation review.
- `Restart` decision (open, needs user confirmation before implementation):
  - Option A (default, pure autostart): no `Restart=` directive. The shell
    starts once per login; if it dies, it stays down until the user starts it
    manually. This matches "session lifetime is not crash supervision".
  - Option B (supervision, previously excluded): `Restart=on-failure` with a
    small `RestartSec`. This adds crash supervision and requires its own
    explicit approval beyond this plan's approval.
- Verification after the user's next login: `omabuntu status` shows
  `running` with the correct release, the startup log shows
  `Configuration Loaded` with no error, and `systemctl --user status
  omabuntu-shell.service` is consistent with the record.
- Rollback verification: after `disable` + unit removal, the next login does
  not start the shell and manual start still works.

## Explicit exclusions

- No crash supervision unless Option B is explicitly chosen and approved.
- No lock/idle/suspend activation, no authentication or recovery changes.
- No Hyprland configuration edits, reloads, or keybinding changes.
- No changes to hyprpaper, hyprsunset, portals, or the uwsm session stack.
- No package installation or new package sources.
- No modification of the installed release files, the manager contract, or
  the sealed release manifests on the host.
- No lock-screen deployment, no wallpaper daemon management, no publication.
- Not a claim of full production acceptance; the shell remains the reviewed
  trial shell deployment.

## Tasks

- [x] User decides Option A (pure autostart) vs Option B (autostart +
      restart supervision). Decided: Option A, no supervision.
- [x] Author the unit template in the repository with the chosen Restart
      policy and the hyprpaper-pattern wiring
      (`config/systemd/omabuntu-shell.service`).
- [x] Add a test that validates the template content (target wiring,
      ConditionEnvironment, launcher path, absence of unintended directives)
      plus isolated deploy/remove tests (`tests/test_autostart_unit.py`,
      `tools/deploy_autostart.py` with plan/apply/remove and a dry-run that
      writes nothing).
- [x] Run `python3 -m unittest discover -s tests -v` (470 tests pass).
- [x] Document the deployment and rollback in `docs/user-installation.md`.
- [x] Ask for and obtain explicit approval to deploy the unit. Approved
      2026-10-26.
- [x] Deploy the unit to `~/.config/systemd/user/`, run
      `systemctl --user daemon-reload`, and `systemctl --user enable`
      omabuntu-shell.service (enable only; do not start it manually).
      Deployed: `enabled`, `inactive`, nothing started.
- [ ] Verify at the user's next login: status running, log clean, unit state
      consistent.
- [ ] Verify rollback once (disable + remove; next login leaves the shell
      down; manual start still works).
- [ ] Update `WORKLOG.md` with the deployment record and rollback state.
