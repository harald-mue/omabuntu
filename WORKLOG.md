# Development summary

This is a curated public development log, not a record of a particular machine's
processes, package transactions or desktop sessions. Detailed operational logs,
old deployment histories and cleanup backups are retained privately under
ignored `work/`. Historical Git objects are not changed by editing this file.

## README project positioning

- Added a disclaimer before installation recommending Omarchy where users can
  choose their distribution. Explained that Omabuntu targets Ubuntu LTS constraints,
  especially corporate environments, and recreates selected workflows rather
  than replacing Omarchy or promising feature parity.

## Release-first README (plan 047)

- Put the one-command curl installation and identical update command first.
  End-user instructions no longer require a checkout, Makefile or local build.
- Removed obsolete channel/promotion wording and detailed legacy stage/deployment
  commands from the README. Kept development and publication in a short separate
  section linked to the operator documentation.
- Preserved the wordmark and honest publication, ABI, bootstrap trust and separate
  session-activation limitations. Added documentation regression and link checks.
  No publication, installation, Git commit/push or desktop changes were performed.

## Personal Git identity correction (plan 046)

- With explicit approval, corrected the corporate author/committer identity in
  main to the personal identity and set repository-local author defaults.
  Preserved all 16 commit trees, messages, dates and unrelated identities.
- Backed up the original history, Git metadata and pending files privately;
  published the verified history using an exact remote force-with-lease and
  verified the resulting remote main. No pending installer work was committed.
- Existing clones require coordination; cached or copied old commits are not
  guaranteed to disappear from hosting services after a history rewrite.

## GitHub release distribution (plan 045)

- Configured the user-approved Ed25519 publisher public key and recorded its
  fingerprint in the release guide. The private key and passphrase were not
  read, copied or tested. Signing access, publication and real installation
  acceptance remain separate gates.

- Separated `make build` (development) from `make release VERSION=x.y.z`
  (reviewed commit, isolated artwork-free build, checksums, SSH signature,
  annotated tag, atomic push and draft-to-public GitHub Release).
- Added a no-checkout HTTPS bootstrap that verifies the publisher signature,
  checksums and metadata before bounded safe extraction. Interactive installation
  uses the existing prerequisite and release review gates, never source builds.
- `make update` selects the latest published GitHub Release, not local mtimes or
  channels. Removed automatic stable promotion. Local channel tools remain
  deprecated compatibility only; existing pin files are not rewritten.
- Updated the README, Makefile help and release setup/trust/recovery guide.
  No publication, Git commit/push, key setup, package installation or desktop
  changes were performed. The public key and first real release remain pending.
  800 tests, clean-source verification, shell syntax and whitespace checks passed.
  Unit/fixture verification is not stock-VM or native-login acceptance.

## Fresh installation, updates and downloaded artwork (plan 043)

- Added memorable installer Makefile targets. The old stage packager is now
  `make package`; plan 045 supersedes the earlier `make release` build alias
  and automatic stable promotion behavior.
- Pinned the built release `source-447226aa17e9898a` as both `dev` and `stable`
  in `channels/omabuntu.json`. The file is an unsigned local pin. It was not
  published, installed, or used to start the desktop.
- Audited existing local-bundle/package/build and rollback tools. Documented the
  gap to stock Ubuntu 26.04, including PPA trust/candidates, native ABI coupling,
  Omasnap packaging, fonts, generic config and clean-VM validation. Updates must
  preserve private configuration/state and distinguish application rollback
  from system-package rollback. No live package, PPA or desktop changes.
- Added a locked-manifest artwork downloader: default plan, offline check,
  explicit bounded downloads, exact pinned length/blob verification, local
  SHA-256 reporting, cache reuse, no redirects/symlinks, no partial-file
  promotion and no clobbering user conflicts. No image downloads were run.
  Per-image redistribution rights remain unresolved; images stay outside Git.
- Added `install.sh` and the Python readiness frontend with the user-approved
  compact two-line block OMABUNTU banner and "Your Ubuntu. Reimagined." tagline,
  ASCII fallback for dumb/limited terminals, TTY colors, numbered status cards,
  compact/plain/JSON modes
  and explicit incomplete-apply gates. Install/update/rollback are previews:
  no privileged actions, Git fetch, writes, downloads or desktop restarts.
  This is not a working fresh-machine provisioner yet.
- Added real prepared-bundle apply/update/rollback through `install.sh`: explicit
  bundle and approval, same manager control lock, native/runtime preflight,
  complete staging before stopping the bar, exact launcher/selectors backup,
  persistent outer journal, and synchronous bar-start failure rollback. New
  bundles declare state schema/native targets; mismatches are refused and
  unversioned installations need explicit acknowledgement. User config and
  preferences are not migrated. Identical reinstall is a no-op. Interrupted
  outer journals block retries for review; automated power-loss recovery is
  not claimed. Tests use fixture releases and mocked bar processes only.
- Added explicit PPA preparation/apply: pinned Launchpad identity and primary
  fingerprint, isolated GnuPG key/InRelease verification, fixed deb822/Signed-By
  destinations, conflict/duplicate/source-drift checks and private journals.
  A real read-only verification of the published resolute signature succeeded;
  no system source was written. Failed source/metadata apply retains evidence
  rather than deleting unrelated source files.
- Added base-only and merged compositor/runtime/build package planning and
  approved additive apply. Exact candidates/dependencies are simulated/pinned,
  native-version drift and existing-package changes/removals are blocked, and
  before/after state is verified. No auto-yes or explicit native-service restart;
  the UI warns about package maintainer scripts. The base-only review ran with
  zero changes on the development target. All sudo/APT mutation tests use fakes.
- Added `--build-release` source-to-bundle planning/apply: pinned runtime builds,
  exact returned-stage checks, source/required-package fingerprint binding,
  isolated Omasnap build/linkage/version probes, verified notices/fonts and
  release-local screenshot binary packaging. Archive and font bytes were checked
  against the source pin. No native compilation or capture was run by the suite.
  Lock-specific artwork caches reuse unchanged verified files across revisions.
  Build approval is not package, deployment or desktop-start approval.
- Pinned/reviewed the desktop Nerd Font and OFL notices. Its actual byte identity,
  family and icon glyphs were checked. Builds stage the font; `--font --apply`
  separately registers it per user with pre-state/backups and cache verification,
  retaining old versions and existing preferences. No live font install occurred.
- Standalone hyprbars now uses installed-binary JSON metadata, fresh output
  paths, library hashes and a post-build identity recheck. The historical builder
  remains separate from the new bootstrap-only isolated builder below.
- Added `--session-config` review/apply with a generic Hyprland 0.56.2 module
  and editable entry, validated XKB choice, original menu shortcuts and
  release-local screenshot/minimize binds. The source API was checked against
  the official pinned example/dispatcher implementation. Real Lua 5.4 tests use
  mock compositor objects. No startup, plugin loading or automatic locking.
- Ownership receipts preserve editable main-file/theme changes and options;
  foreign profiles or owned-module drift block apply. Live user Hyprland
  processes block writes, and pre-state/backups plus synchronous failure
  restoration preserve concurrent edits. The updater rejects candidates missing
  helpers referenced by an installed generic profile. The existing private
  profile was reviewed only and refused as unowned; no desktop config changed.
- Integrated the separate `build_plugin.py` with bootstrap source-to-bundle
  preparation: exact plugin/header archives and BSD notices, private generated
  headers, Bubblewrap compile/static-ELF/linkage/export checks, client ABI derived
  exactly as the pinned PluginAPI.hpp, and package/native drift gates. Preserve
  protocol notices and inert native library/descriptor bytes inside releases;
  updates recheck the descriptor before stopping the bar. Never dlopen, run
  plugin entry points, hyprpm, load/unload, or mutate the historical checkout.
  The two actual archives/notices and headless ABI metadata were verified;
  compiler/scanner/ELF outputs are simulated in tests, not native acceptance.
- Hardened new output/temp handling against collisions: never reuse a plugin
  workspace or remove a temporary file whose exclusive creation failed. The
  session writer shares this cleanup correction. Verification: 731 unit tests,
  clean-source verification and git diff whitespace checks passed. No native
  build, plugin load, config apply or desktop restart was performed.
- Added `--session-activate` for next-login files only: guarded load of the
  immutable release hyprbars library, reviewed titlebar rules with the release
  minimize helper, hyprpaper splash disabled, and the existing oneshot user unit.
  `--enable-login` can enable that unit; nothing is started, loaded or reloaded.
  Unowned files and a running Hyprland or hyprpaper block writes. Tests use
  fixtures and never call a real compositor or systemctl start.
- Added `./install.sh --guide`: a read-only ordered review of host, PPA, packages,
  font, build, release, session, activation and manual login. `--apply` runs only
  the next local stage after confirmation. It does not install packages, restart
  the bar, load a plugin or start Hyprland. System stages stay separate commands.
- Added `--recover-update` for exactly one interrupted application update. Apply
  restores the recorded selectors and launcher, keeps the journal, and does not
  resume the new release. A running bar is not force-stopped. `--restart-bar`
  starts only a bar that the interrupted update had already stopped. Tests use
  fixture journals and mocked startup.
- Added `--source-update` for the reviewed source pins. Apply fetches only missing
  exact archives into the private cache, refuses redirects and cache conflicts, and
  does not reset a checkout, build, or deploy. A checksum is recorded as a
  consistency check, not a publisher signature. Omarchy remains commit-pinned for
  its separate artwork downloader.
- Added a user-state schema policy. Schema 1 needs no migration. Any other schema
  is refused until a reviewed bidirectional migration exists, and no state file is
  rewritten. `./install.sh --state-schema` only names known files.
- Added package-closure simulation and guide orchestration for the next PPA or
  package stage. System apply requires `--guide --allow-system --apply` and still
  uses the existing approval path. Closure output is not VM acceptance and does
  not install packages by itself.
- Recorded the shared-library upgrade decision in code. Missing packages may be
  added; installed-package upgrades and removals stay refused, including Hyprland,
  Qt and Hyprlock. A caller-supplied name list is not approval. The current
  simulation did not need an upgrade to add the missing LayerShellQt packages.
- Compiled runtime, screenshot and plugin stages are reused only when exactly one
  verified directory matches. Multiple matches and symlinks are not treated as the
  newest build. Reuse does not skip isolated checks or package verification.
- Added `./install.sh --acceptance`, a read-only gate report for host, PPA,
  packages, font, bundle, session and activation. It never sets native-login
  acceptance, installs packages or starts the desktop.
- Next-login activation can record the first release still when no wallpaper choice
  exists. It writes the state file and lock symlink only, does not call hyprctl or
  start hyprpaper, and leaves an existing choice untouched.
- Added `--session-config --adopt-managed` for an untouched installer-owned
  omabuntu-managed snippet. Extra user lines are refused, the old snippet file is
  not deleted, and no session is started. The private workstation profile remains
  unowned and was not modified.
- The default `./install.sh` entry now shows the live read-only guide instead of
  only the static readiness preview. `--check` and `--json` keep the readiness
  report. Default mode does not apply, install, or start anything.
- Added `./install.sh --rehearse`, a fixture lifecycle for install, repeat install,
  failed bar start, update, rollback, generic session preparation and next-login
  activation. It uses a temporary home, simulates the bar, and does not change
  host configuration or claim VM acceptance.
- The guide now treats an unmanaged Hyprland PPA source as a manual review, not as
  a command to add the managed source. It does not rewrite or duplicate APT sources.
- The package guide stage now names the missing requested packages, bounded to
  the first five, and still does not install them.
- The package review now prints the addition names before any approval. The
  reviewed transaction remains three additions and no removals or upgrades.
  No package was installed.
- Long build steps now print a still-running line every 15 seconds. Compiler output
  remains in the private log. This does not change the already running build.
- Added local `dev` and `stable` channel pins. A channel file stores only a
  version and metadata SHA-256, never a URL, signature claim, or artwork grant.
  `--update --channel` resolves a local release directory and does not download
  or publish.
- Pinned the built release `source-447226aa17e9898a` as both `dev` and `stable`
  in `channels/omabuntu.json`. The file is an unsigned local pin. It was not
  published, installed, or used to start the desktop.
- Documented the current installer, stage order, development-target package and
  build results, and local dev/stable channels in `docs/installer.md`. README and
  the older installer pages now point there. Publication remains unapproved.
- The remaining stock-Ubuntu native first-login acceptance, ABI-gated live plugin activation,
  native build/upgrade acceptance and clean-VM testing remain tracked in plan 043
  and docs/fresh-installation.md. No live source, package or application apply
  was run during this installer work.

## Original weather location interaction (plan 042)

- Restored the original Omarchy weather city editor, suggestion list, persisted
  selection, and clear-to-IP behavior after explicit user approval. Replaced
  only upstream curl/command and state paths with a fixed-command Python
  adapter: wttr.in for current reports/IP city and Open-Meteo for city search
  and forecasts. No arbitrary URL, redirects, shell, or timezone changes.
- Location set/clear backs up the previous record and rejects symlinked paths.
  All 596 tests pass without live network in tests. Separate approved IP and
  city-search probes succeeded. After approval, backed up and deployed the
  location-parity panel, widget and probe, verified installed integrity, and
  restarted only the recorded bar. Startup has no QML or helper-launch errors.
  Native location-editor interaction still needs user acceptance. No lock or
  capture was triggered.

## Lock, screenshot, and weather follow-up (plan 041)

- Added source menu rows for System > Lock and Trigger > Capture > Screenshot.
  Exact registry tokens launch the installed lock manager and existing Omasnap
  wrapper without a menu-process lifetime limit or a shell. Packaged the capture
  wrapper alongside the menu helper. No lock or screenshot was triggered and
  these menu additions were later deployed after approval. All 583 unit tests
  passed before weather integration.
- After the user selected Vienna and Open-Meteo only, staged the original
  Omarchy 03ff1eff weather panel and model with witnessed Ubuntu adaptations.
  The bounded standard-library probe requests only Vienna's forecast; the
  panel refreshes every 15 minutes with metric units. No IP location, wttr.in,
  geocoding/editor, notification action, or IPC registration. MIT source and
  Open-Meteo CC BY 4.0 data attribution are recorded. A provider check returned
  a valid four-day report. All 590 unit tests pass; live QML/visual acceptance
  remains pending. After approval, backed up and deployed the weather and menu
  files, verified installed integrity, and restarted only the recorded bar.
  Startup logged Configuration Loaded without QML or helper-launch errors.
  Hyprland and applications stayed running; no lock or capture was triggered.

## Setup default browser and terminal (plan 040)

- Added Setup > Defaults > Browser and Terminal to the Super+Space menu. Rows
  list only installed `.desktop` entries. The browser choice uses
  `xdg-settings`; the terminal choice writes the Hyprland xdg-terminals
  preference list for `xdg-terminal-exec`. Nothing is installed from the menu.
  The active release copies were backed up and replaced; the bar was not
  restarted.

## Lock surface uses the recorded wallpaper (plan 039)

- The reviewed Hyprlock config now points at `~/.local/state/omabuntu/current/lock-background`, with three blur passes and the previous flat color when that still is missing. The clock and the Omabuntu wordmark are gone. The password field and the package PAM service stay. No screenshot path, reload command, or original lock plugin.
- Background set and restore update that symlink after the existing directory allowlist. The current recorded still was published there. The active release copies of the lock config and background helper were backed up and replaced. No lock was started.

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
