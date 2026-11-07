# Repair normal session actions and wallpaper reliability

## Goal and evidence

Implement the user's request following plan 108: ordinary logout/reboot/shutdown
must not require hidden flags, including after an application update. The picker
opens and permits image selection, but the guest stays black. Trace the entire
selection/record/IPC/login-restore/UI path and preserve useful diagnostic evidence.
Compare pinned Omarchy `ac2690cd7be4f47e4a255f5e2e78d904d436b068`, official
Hyprland 0.57.1 `acc1aa0bfd4bd575dcb0f76c35ccf12b660a1ab9` and Hyprpaper
0.8.5 `a8e93f4e60eabc432dde43449dfeb9a565c54da2`; references verified in
`work/session-wallpaper-108/`. Check official dispatcher/session documentation
before implementing logout. No third-party code or assets will be imported.

## Gaps and proposed shape

- Remove application-only gates for ordinary actions, retaining sleep gates and
  Ubuntu authorization/inhibitors. Updating the packaged helper repairs old
  installations without rewriting preference files. Logout must use the current
  validated Hyprland instance instead of assuming UWSM or terminating all sessions.
- Make background transport failures specific; no legacy preload fallback on
  unrelated errors. Separate recording, daemon acceptance, active-target report
  and actual visual acceptance. Surface failures in the existing picker.
- Repair missing-theme image listing and inspect startup restore timing. Add a
  bounded readiness retry only to login restoration, never a component lifetime.
- Provide read-only, bounded wallpaper diagnostics usable on the affected guest;
  never infer successful rendering from process health or IPC success.
- Preserve existing preference/default wallpaper choices and the application-only
  updater's no-wallpaper-restore boundary. Validate packaging of changed helpers.

## Safety and exclusions

Private pre-edit backups/metadata in ignored `work/session-wallpaper-109/`.
Source changes/tests only: no actual logout, reboot, shutdown, lock/sleep, daemon
start/restart/reload, live desktop change, package/source/security policy change,
VM graphics edit, commit/push or release. Earlier pending documentation is not
reverted. No new renderer/panel, force-close of applications, broad termination,
automatic sleep grant, autostart or crash supervisor. Remote EGL/GBM failures
cannot be declared fixed by source tests. Deployment and live guest acceptance
require separate review and approval; rollback selects the previous intact
release and does not erase independent preference changes.

## Tasks

- [x] Verify official logout behavior and back up affected source paths.
- [x] Implement ordinary-action defaults, validated current-session logout and useful failures.
- [x] Repair wallpaper failure propagation, selection and bounded login readiness handling.
- [x] Add read-only guest diagnostics and document remaining rendering acceptance.
- [x] Test fresh/legacy state, exact fake dispatch, errors, timeouts, startup race and packaging.
- [x] Run full tests and clean-source/whitespace checks; record results and deployment boundary.

## Implementation and evidence

Private pre-edit copies, modes/hashes and test/source reports are under
`work/session-wallpaper-109/`. Existing pending v0.2.2 publication documentation
was not overwritten. This request adds source changes only, not a deployment.

### Normal actions

`power_actions.py` now ignores application gates for ordinary actions without
rewriting their old files. A release update therefore repairs these defaults by
switching the packaged helper, even when old flags are missing/false. Legacy
`enable`/`gates` interfaces remain readable for compatibility. Suspend/hibernate
still require explicit safety grants and kernel capability; neither is enabled.
Normal systemctl authorization/inhibitors are not bypassed.

Logout requires current owned Wayland/Hyprland sockets, a unique matching instance
and owned compositor PID. Its cgroup identifies an exact UWSM compositor service;
MainPID must still match before that one service is stopped. A directly started
compositor uses the supported `hl.dsp.exit()` dispatcher. No wildcard termination,
forced app closing or inherited UWSM-flag assumption. Failures/missing commands/
timeouts are returned to the menu instead of escaping as a traceback. A zero-exit
dispatcher error is not success.

Official evidence: exact 0.57.1 example plus Lua dispatcher registration, compared
with official wiki dispatcher/UWSM documents at
`ec1068fed41a68d9bace129de16aed785dd785ee` (BSD-3-Clause) and UWSM README at
`755e4b7d109e8800748fc8210f44dcfbf28c348b` (MIT), section "Stop". The website
returned HTTP 403; pinned official GitHub documents were used instead. They warn
against exiting the compositor directly under UWSM and document stopping the
exact `wayland-wm@` instance. Private copies retain licenses; no code/assets were
imported into product files. The current wiki was cross-checked against pinned
0.57.1 source rather than treated as version-specific runtime acceptance.

### Wallpaper

- A missing initial theme no longer hides downloaded theme stills. Existing theme
  and wallpaper selection files are not replaced with a new default.
- Each active output receives the image; failure details (including stderr) are
  preserved. Only explicit legacy "not preloaded" replies trigger preloading;
  unrelated failures do not. Legacy cleanup no longer unloads every client's
  preloads. Comma/control-separated image paths are refused before recording.
- Daemon command acceptance is checked against `listactive` on supported versions.
  Missing/wrong targets remain unapplied, including an empty zero-exit status.
  Explicitly unsupported old status queries retain acceptance but do not claim
  target verification (`active_reported: null`). No status proves rendered pixels.
- Both background selection and theme application retain wallpaper failure
  messages in the existing picker; saving colors is not wallpaper success.
- The existing login `restore` path now retries only transient daemon/output
  readiness within 13 seconds overall (5-second probe maximum). It never starts a
  daemon, becomes a supervisor or changes a component's session lifetime.
- `omabuntu wallpaper-status` invokes the installed integrity-checked helper's
  read-only `diagnose` command. Five bounded probes report session context, image
  selection/availability, daemon status/version, active targets and recent
  current-boot journal errors. Preference reads bypass the old creating
  `state_home()` reader: no new state directory or control lock. Reports always
  say `rendering_verified: false`; private paths should be reviewed before sharing.
- The application-only updater's no-wallpaper-restore policy is unchanged. The
  shell source was checked for a competing full-screen black background surface;
  no such replacement renderer was introduced by this repair.

### Verification

- `python3 -m unittest discover -s tests -v`: **1185 passed** (27 additional tests).
- Clean-source check passed at
  `work/clean-source/20261107T212124.418986Z/report.json`.
- Contained picker check passed at
  `work/picker-port/20261107T211843.552655Z/report.json`.
- Contained command-menu check passed at
  `work/menu-port/20261107T212124.453434Z/report.json`.
- The initial contained picker run exposed a stale fixture helper list missing
  three existing menu imports. It now stages those imports without stubs or
  bypasses. The menu fixture was updated to exercise safe out-of-session logout
  refusal instead of attempting newly ungated reboot. Deep clean-export paths
  required relative test-socket binding; no production socket checks were relaxed.
- Negative controls against backed-up code demonstrate old fresh-state reboot
  refusal and old false success for command acceptance without an active target.
- Private bundle `work/user-releases/session-wallpaper-109-review` verifies intact;
  manager and changed helpers match source, no bundle bytecode was added. It is
  neither installed nor started. Product helpers use only the standard library.
- `git diff --check` passes. Pre-existing release documentation remains separate.

## Acceptance and deployment boundary

No real session action, wallpaper apply/restore, service activation/reload, package
or VM graphics change, commit, push or publication was performed. The guest's
black image cannot be declared fixed from the tests. The user has clarified that
the picker itself works, so an empty picker is not the established cause there.
A next release/deployment must carry these changes before the new diagnostic CLI
is available. If a correctly reported target remains black, investigate actual
EGL/GBM/renderer evidence from that guest; no speculative graphics/permission fix.
Native UWSM/direct-session logout and graphical guest acceptance remain separate.
Rollback uses the prior intact release; ordinary-action flags and unrelated
wallpaper/theme preferences were not migrated or erased by this implementation.
