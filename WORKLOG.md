# Development summary

This is a curated public development log, not a record of a particular machine's
processes, package transactions or desktop sessions. Detailed operational logs,
old deployment histories and cleanup backups are retained privately under
ignored `work/`. Historical Git objects are not changed by editing this file.

## Lock surface uses the recorded wallpaper (plan 039)

- The reviewed Hyprlock config now points at `~/.local/state/omabuntu/current/lock-background`, with three blur passes and the previous flat color when that still is missing. The clock and the Omabuntu wordmark are gone. The password field and the package PAM service stay. No screenshot path, reload command, or original lock plugin.
- Background set and restore update that symlink after the existing directory allowlist. The current recorded still was published there. The active release was not replaced and no lock was started.

## Elsewhen world clock (plan 038)

- Staged Jason Fried's Elsewhen panel to the right of the clock. Cities stay in
  the running process. Open-Meteo, GitHub profiles, notification delivery,
  system timezone changes and IPC registration are not included. Zone offsets
  use a read-only helper. The panel's own QML types are registered together.
  The recorded bar was restarted onto this panel.

## Left bar matches Omarchy (plan 037)

- Removed the authored Apps button and the focused-window title from the left
  bar. The left side is the menu mark and the workspace switcher. The app grid
  remains on the command menu and the floating dock. The recorded bar was
  stopped, the three installed shell files and their integrity entries were
  replaced from a private backup, and the bar was started again.

## Keyboard-layout visibility (plan 036)

- Removed the `alwaysShow` splice. The preview keyboard-layout widget is again
  a byte copy of pinned Omarchy `03ff1eff`, so a single layout and a single
  input method hide the label. The widget stays mounted between the tray and
  Bluetooth. The active shell copies were backed up and replaced; the running
  bar was not restarted. No second layout, input method or commit.

## Screen-lock lifetime correction (plan 035)

- Removed the 30-minute subprocess timeout from the actual Hyprlock invocation;
  bounded preflight probes and all session, version and configuration checks
  remain unchanged. The explicit lock now lasts until the process exits.
- Demonstrated the new mocked regression failing against the old timer, then
  passing after the fix, including successful and failed completion reports.
  All 566 unit tests pass without activating a screen lock.
- Backed up and narrowly updated the active installed helper and its integrity
  manifest entry; full installed-release verification passed. Private prior
  state and recovery copies remain under ignored `work/`.
- No lock activation, live authentication test, process restart, selector change,
  PAM/security-policy change or commit. Historical incomplete lock records fit
  the defect but do not prove every incident's cause.

## Ubuntu-native foundation

- Added read-only doctor reports, capability mapping, package planning and
  explicit safety/approval boundaries.
- Pinned upstream source candidates and retained third-party notices instead of
  running an Arch installer or exposing upstream helpers through PATH.
- Added contained runtime building, artifact verification and nonvisual import
  probes. Build success does not establish desktop or authentication acceptance.

## Selected original desktop components

- Retained selected original Omarchy presentation/layout sources with narrow
  Ubuntu backend adaptations and deterministic generated mirrors.
- Added bar/frame, tray, audio/network panels, calendar, application launcher,
  command menu, image picker, keybinding view and floating-workspace dock paths.
- Kept excluded startup, privileged, authentication and unsupported behavior
  explicit. The full unmodified original shell is not deployed.

## Local installation and desktop integration

- Added sealed versioned local releases, identity-checked session control,
  transaction backups, rollback/recovery and separately approved login autostart.
- Normal desktop components use an explicit untimed session grant. Autostart
  is not crash supervision, and lock/idle/suspend acceptance is separate.
- Added managed compositor settings, title-bar plugin registration and recorded
  wallpaper restoration, without arbitrary configuration replacement.
- Fixed login readiness and process-lifetime issues, then prevented wallpaper
  helper bytecode from invalidating installed releases.
- Added atomic per-workspace mode persistence, executable Lua regressions,
  delayed-state restore and serialized floating-window claims.
- Added the approved manual screen-lock chord `SUPER+CTRL+L`. It runs the
  installed `lock --apply` helper once, on key release, so the held chord is
  not delivered to Hyprlock. Super+K lists that row and does not launch it.
  Idle and suspend stay unbound. The two-column keybindings card is included
  in the approved shell update below.
- A window moved between a floating and a tiling workspace is arranged the way
  Omarchy's move handler does: the mode's own floated window is tiled again on
  the way out, and a tiled window dragged onto a floating workspace is claimed.
  A window floated on its own stays floating. Fullscreen-exit arranging and
  click-to-focus stay excluded. The approved bar restart now
  serves this shell, including the two-column Super+K card. Hyprland was not
  reloaded.
- Plan 032 prepares Omarchy's separate floating-workspace membership tag.
  Already-floating arrivals receive the titlebar without acquiring mode ownership;
  all departures lose membership, but only owned, unpinned windows are tiled.
  Workspace toggles and startup restore follow the same distinction. The pinned
  hyprbars compatibility rule now matches membership. Executable Lua regressions
  cover already-floating/fullscreen/pinned arrivals, unowned departures and whole
  workspace changes. The approved local update is now installed: the owned shell
  was restarted and the backed-up titlebar configuration reloaded without changing
  autostart or plugin binaries. A malformed empty-argv process record was reconciled
  only after explicit approval and matching live PID/start ticks/exact argv.
  The existing floating window initially lacked membership after startup; the
  reviewed claim eval added it successfully without claiming or resizing it.
  Automatic startup restoration and actual drag/drop/button rendering still need
  live confirmation; installation and a successful eval are not visual acceptance.
- Plan 033 prepares the missing Omarchy arrangement after maximization/fullscreen
  changes. The addressless socket event triggers a delayed, coalesced rescan of
  floating-workspace candidates through the existing serialized claim queue.
  Live Lua checks preserve fullscreen and already-floating geometry; a restored,
  still-tiled window is floated and placed. The QML event/timer regression fails
  without the handler and passes with it; real Lua tests cover maximized and
  fullscreen restore plus repeated-event geometry preservation. This follow-up
  is now deployed after explicit approval, with transaction backups and an
  owned-shell-only restart. Installed integrity and clean startup/configuration
  checks pass; compositor config, plugin binaries and autostart were unchanged.
  Live drag/maximize/restore/resize and startup restoration remain unconfirmed.
- Plan 034 investigates direct placement after cross-workspace drag completion.
  Versioned Hyprland source shows temporary floating during a tiled drag and a
  possible retile at dragEnd. The supported socket/Lua interfaces provide no
  explicit drag-end event. A coordinated passive trace now confirms floating-on,
  workspace move, then floating-off at release; the affected window is tiled and
  non-fullscreen afterwards, not maximized. That socket sequence can also result
  from intentional manual toggles, so reliable drag-only correlation is not yet
  established. The user explicitly approved correcting manual retile on floating
  workspaces as well. The source now defers an addressed, deduplicated claim on
  floating-off events and ignores floating-on events. Active/queued workspace-mode
  changes away from floating block claims, preventing correction feedback.
  Tiling/special workspaces, fullscreen and existing floating geometry are
  preserved. The recorded event-sequence regression fails without the correction
  and passes with it; all 565 unittests and the isolated QML fixture pass.
  The user-approved policy extension is now installed with backups and an
  owned-shell-only restart. Installed integrity and clean startup/configuration
  checks pass, with saved workspace modes and compositor config hashes unchanged.
  No Hyprland reload, autostart/plugin change or application test manipulation
  occurred. The user confirmed basic native drag/drop correction. Its brief
  release-time position change comes from the shared resize/center/cascade path;
  preserving drop position was discussed and explicitly deferred. Separate
  manual-retile/pointer-resize live acceptance and startup restoration remain open.
- App launches from the app grid and the floating dock now arm Omarchy's
  delayed "Launching …" notice. It appears only when no window has arrived
  after two seconds, passes clicks through, and is not a notification. The
  approved bar restart serves this notice, and the user confirmed it.
- The launch notice now waits one second instead of two. The fifteen-second
  limit is unchanged. The approved bar restart serves this delay. Hyprland
  was not reloaded.
- Plan 031 records an Omasnap screenshot path matching pinned Omarchy:
  Print and Super+Shift+S launch a reviewed local Omasnap, not grim or
  Satty. Omasnap 1.24.0 (`a432f40`) is pinned with its MIT, font, and icon
  notices. `tools/capture_screenshot.py` maps the Omarchy wrapper.
- The approved build is installed for this user. Print and Super+Shift+S
  are bound, the Omasnap layer is kept out of screen shares, and Hyprland
  was reloaded. Layer Shell Qt came from the Ubuntu packages unpacked under
  the user prefix, not from apt. Nothing was captured.
- Both screenshot keys reached the wrapper and then exited. The wrapper
  rejected the process environment, and Hyprland does not export
  `WAYLAND_DISPLAY`, so Qt fell back to X11. The wrapper now accepts that
  environment and passes the single Wayland socket through. No new capture
  and no Hyprland reload.
- A real login and workspace persistence were user-confirmed. Disabled
  hyprpaper's independent splash and obtained visual confirmation; the
  compositor's splash flag alone does not control the wallpaper daemon.

## Publication preparation (plan 023)

- Excluded local wallpaper and preview directories from Git without deleting
  their contents; retained source provenance and existing third-party notices.
- Made local image staging optional and removed imported-image dependence from
  the installer codec probe. Local bundles can still include local images and
  are not automatically cleared for redistribution.
- Required explicit verified runtime build directories rather than a fixed
  developer timestamp; help/plan modes remain non-activating.
- Refreshed README and installation guidance, added a central third-party notice
  inventory and a repeatable clean-source verification workflow.
- Passed 542 unit tests locally and in an asset-free candidate export. A new
  contained native build from pinned archives, all 32 runtime checks, desktop/
  command-menu/image-picker fixtures, asset-free packaging, installer preflight
  and release relocation also passed without reusing old work inputs.
- The native preflight exposed Qt rejection of a valid 38-byte 1x1 WebP fixture;
  replaced it with an authored 16x16 lossless gradient and repeated preflight.
- Reversibly archived two superseded build directories privately with their
  original paths/inodes recorded. The retained original runtime still verifies,
  and all 120 local images still match recorded upstream blob checksums.
  Plan 023 deleted no old build bytes, large diagnostic logs or recovery backups;
  permanent pruning required a separate approval (see plan 024 below).
- Archived the previous operational diary privately before this rewrite.
  Existing Git history is deliberately unchanged; no commit, remote or public
  upload is authorized by this cleanup.

Verification results and bounded local artifact cleanup are recorded in plan
023. Unit, isolated-runtime and clean-source checks have different scopes and
must not be described as fresh-machine, visual or security acceptance.

## Approved archived-build pruning (plan 024)

- After explicit user approval, permanently deleted only the two superseded
  build directories previously archived by plan 023: approximately 2.42 GiB of
  logical build data. Original paths/identities and deletion outcomes are
  recorded privately; metadata does not restore the deleted contents.
- Both the retained original runtime stage and the new clean-source runtime
  stage still pass integrity verification. Other backups, release bundles,
  images, diagnostic logs and recovery material were not removed.
- No desktop, service, package, Git index, commit or publication changes.

## Authorized source commit preparation (plan 025)

- Verified access to the user-named GitHub repository and prepared an explicit
  source-only commit candidate, excluding local images and all private work data.
- Checked the full current candidate and the existing commit's file history with
  local secret/privacy patterns. Reviewed the findings as UI text, systemd unit
  names and authored sandbox paths. No dedicated secret scanner was available;
  this bounded check is not exhaustive security or redistribution clearance.
- The full 542-test unit suite and independent clean-source verification pass.
  Preserve existing history and hooks; use the user-requested commit identity
  only for the commit process, without persistent Git configuration changes.
- Reviewed the explicit 295-file staged candidate. Fixed three existing authored
  whitespace defects; retained the imported QR generator's original formatting
  and license bytes. Its known upstream whitespace is the only diff-check
  exception; hooks and source verification are not bypassed.
- Remote creation, push and publication remain separate from this local commit.

## Approved GitHub history integration (plan 026)

- After the subsequent push approval, found an independent GitHub initial commit
  containing only an MIT license. The user explicitly approved preserving both
  histories with a merge rather than replacing either branch history.
- Resolved the sole LICENSE add/add conflict by retaining the copyright notices
  for Harald Müller and Omabuntu contributors. MIT permission/disclaimer and all
  third-party licenses remain unchanged.
- Prepared a normal merge commit and fast-forward push using the requested
  process-local author/committer identity. No force push, history rewrite,
  repository visibility change, binary release or desktop deployment is part
  of this operation. All 542 unit tests and clean-source verification pass;
  the 296-file text-only candidate excludes images, binaries and private work.
  Actual commit/push outcomes are recorded privately and in Git; validation
  precedes execution.
