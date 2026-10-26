# Work log

## Image picker for themes and backgrounds (plan 005) (2026-10-25)

Omarchy's theme app is the `omarchy.image-picker` plugin, not a menu
submenu. Ported it as `config/shell/preview/ImagePicker.qml` with the pure
logic in `ImagePickerModel.js`, both derived from the pinned commit and
recorded in the authored profile. Theme previews are painted from the
recorded palettes (upstream uses theme background images, which stay
unimported for license reasons); background previews show Ubuntu's
`/usr/share/backgrounds` and `~/Pictures` files directly, with no thumbnail
generation and no videos. Style > Theme and Style > Background now open the
picker; applying routes through the reviewed helper dispatch. A background
apply records state only and says so in the picker. 406 unit tests pass.
Offscreen reports:
`work/picker-port/20261025T221721.823339Z/report.json`
(`isolated-picker-fixtures-passed`) and the adapted menu fixture
`work/menu-port/20261025T221720.786019Z/report.json`.

The user approved packaging and a restart. The same 406 unit tests passed
again. Relocation check:
`work/user-release-checks/20261025T222327.100743Z/report.json`
(`isolated-relocation-passed`). Stopped only the installed bar, installed
`20261025-local.19`, and started it. Previous release is `.18`, which
remains the rollback and does not contain the picker. Running pid 627101,
session lifetime, no autostart. Startup log:
`~/.local/state/omabuntu/runs/20261025T222357.449340Z/output.log`
(Configuration Loaded, no error; the same portal registration warning as
`.18`). The four shortcuts are still registered and the bind count stayed
34. `~/.config/hypr/hyprland.lua` was not modified. No wallpaper daemon
was started. The picker was not opened and no theme or background was
applied. Operation report: `work/installed-update-local.19.json`.

## Command menu look (plan 004) (2026-10-25)

Super+Space was a top-aligned gray card. Several icons were broken surrogate
escapes, so they could not be drawn even though JetBrainsMono Nerd Font has
the pinned glyphs. Kept icons now match the pinned scalars. The card is
centered, the search line is plain text, and defs carries the active palette.
Matte black is the recorded theme, so the card uses `#121212`, `#bebebe`,
and accent `#e68e0d` for the selected row. Packaged and started as
`20261025-local.18` (pid 479890). Rollback at that install was `.15`. `.16` did not load
(`FileView` without `import Quickshell.Io`) and `.17` was stopped
(`Commons` used without the import alias). The startup log for `.18` has
no error. Super+Space still opens the menu. Trigger, Setup, Install,
Remove, Update, and About stay out.

## Command menu keys and power gates (plan 002) (2026-10-25)

Release `.14` already contained the command menu, but Super+Space and
Super+Escape were still unbound. Both were free (Super+Alt+Space and
Super+Shift+Escape stayed as they were). Added the two session binds with
`hyprctl eval` to `omabuntu:menu` and `omabuntu:system`. `~/.config/hypr/hyprland.lua`
was not modified. The menu opened and closed on the focused screen.

The installed helper refused the menu's shutdown row because that action is
`systemctl:poweroff` while the gate was named `shutdown`, and it refused
hibernate even after its gate. `poweroff` is now the shutdown gate. An
enabled hibernate gate runs `systemctl hibernate` when the kernel lists
`disk`; the resume path is still unverified, which the user accepted and
will test later. Selector checks accept a release packaged before the menu,
so rollback to `.13` still plans. Incoming bundles still have to contain the
menu and its helpers. Dispatch tests isolate the state home and inject the
runner, so a later test run cannot reboot the machine.

384 unit tests passed. Relocation check:
`work/user-release-checks/20261025T212932.970532Z/report.json`
(`isolated-relocation-passed`). Stopped only the installed bar, installed
`20261025-local.15`, and started it. Previous release is `.14`. Operation
report: `work/installed-update-local.15.json`. Running pid 398195, session
lifetime, no autostart. Startup log:
`~/.local/state/omabuntu/runs/20261025T213007.897821Z/output.log`.
The new bar registered the same four shortcuts and the menu toggled again.
Bind count stayed 34. No configuration errors.

Enabled gates: logout, reboot, shutdown, hibernate. Suspend is not enabled.
No power action was run. Live theme, font, and background changes were not
applied. The session binds disappear when Hyprland restarts.

## Clock calendar popup implemented (plan 003) (2026-10-25)

Left click on the live trial clock now opens the original Omarchy calendar
surface from `shell/plugins/panels/clock/Panel.qml` at
`03ff1eff3812933f7088484533784d2f63eaf19a`. `tools/clock_frontend.py` derives
`CalendarPanel.qml` and `ClockControlView.qml`. The sealed read-only label is
unchanged. Shell IPC, configuration writes, the privileged timezone picker, and
the calendar hotkey stay excluded. Week start, label format, and birth year
stay in session memory, shared across screens through the trial object. The
clock and the right-side panels share one popout bus. 380 unit tests pass.
The isolated desktop compile also constructs the six-week grid
(work/desktop-panels/20261025T210539.029616Z).

The user then approved packaging and a restart. Release `20261025-local.14`
reuses the verified Quickshell runtime from
`work/builds/20261024T001419.742301Z` and ships the current shell. Relocation
check: `work/user-release-checks/20261025T211329.127396Z/report.json`
(`isolated-relocation-passed`). Stopped only the installed bar, installed
`.14`, and started it. Previous release is `.13`. Running pid 389994, session
lifetime, no autostart. Startup log:
`~/.local/state/omabuntu/runs/20261025T211423.919818Z/output.log`.

## Audio input section implemented (plan 001) (2026-10-25)

Diagnosis (work/audio-input-diagnosis/20261025.md): this machine has three
typed ALSA capture nodes and no virtual sources, so the native Quickshell
boundary covers input control; the upstream process wrapper and default-helper
stay excluded. PwNodePeakMonitor is native (peak.hpp QML_ELEMENT), so the
upstream peak meter is included, gated on panel-open like upstream.

Implemented: tools/audio_frontend.py now extracts the input separator,
header, input slider (with the same drag-identity guard as output), peak
meter (Util.alpha to Style.alpha, inputPeakMonitor.peak to root.inputPeak)
and SourceRow (with the id+name identity guard), ending before the per-app
streams section. AudioOutputProvider gained typed sourceCandidates (no sinks,
no streams, node.audio, quickshell hidden), a monitoring-gated PwNodePeakMonitor,
inputSnapshot, setSourceVolume/toggleSourceMute/chooseInput through the native
preferredDefaultAudioSource. AudioPanelController gained the input cursor
section per the upstream section model (moveCursor/adjustVolume/activateCursor,
m-key mute for input), inputVolume/inputMuted/hasInput and input error copy.
I18n gained the upstream audio.input label. Streams, untyped/virtual sources,
helper/IPC/OSD routes and the upstream master-mute hero stay excluded and
documented. Tests updated to the new contracts; comments no longer carry
process-tool tokens. Provenance re-registered (74 files); 319 tests pass.
Release packaging, bar restart and installation are pending separate approval.

## Audio input-section plan (2026-10-25)

Analysis confirmed the derived audio panel is output-only while the pinned
Omarchy original also offers input source selection, an input slider and
input mute (typed nodes via native PipeWire; virtual sources via an
UntypedInput wpctl singleton; a helper for untyped defaults). No code
changed. The porting stage is planned in plans/001-audio-input-section.md
per the AGENTS.md plan rules: typed sources only, helper and wpctl routes
excluded, approvals separate.

## Return to the hyprpm manager artifact (2026-10-25)

After local.11 acceptance and the confirmed titlebar matcher fix, the
diagnostic plugin was unloaded (work/hyprbars-render-trace/build/libhyprbars.so)
and the hyprpm manager artifact reloaded
(/var/cache/hyprpm/muha/hyprland-plugins/hyprbars.so, new handle 5cf296c98470).
The internal config reload was expected: the corrected snippet was applied
exactly once, workspace layouts, omabuntu tags, floating flags and the
SUPER+ALT+SPACE apps bind were recovered and verified (configerrors empty,
enabled/bar_height set, bind present, window tags preserved).
Transaction: work/hyprbars-render-trace/restore-20261025T172505Z.
hyprpm is again the only load path. Trace evidence stays under
work/hyprbars-render-trace/. Persistence (hyprland.lua include and
hyprpm reload autostart) remains the final separate approval.

## Local.11 accepted (2026-10-25)

User confirmed all three acceptance items on release 20261025-local.11:
workspace 6 re-toggled to floating works; the dock context menu closes on an
outside click (upstream HyprlandFocusGrab restored); the settings row shows
the upstream "Auto-hide" label without overhang. Rollback anchor remains
releases/20261025-local.9 via the install transaction.

## Dock menu overhang label fix (2026-10-25)

The user reported the dock context-menu row overhang. Root cause: the staged
English catalog had a later duplicate `dock.autoHide` entry, "Hide when not in
use", overriding the upstream label. Upstream English is "Auto-hide"
(work/omarchy-shell-en.json). The dock menu popup sizes to a fixed
`Style.space(140)` content width (MenuRow rectangles contribute no implicitWidth,
row text has no elide), so the longer authored label overhung the popup edge.
Removed the duplicate line so the upstream "Auto-hide" applies; re-registered
provenance; 315 tests pass. Packaged in `20261025-local.11` together with the
outside-click focus grab (local.10 content). Menu dismissal in the still-running
local.9 bar: only via a menu row, a dock icon click, or leaving floating mode -
which is why outside clicks appear to do nothing. Not yet installed.

## Dock context-menu outside-click dismissal restored (2026-10-25)

The user reported the dock right-click menu stays open; hover was a red herring.
Comparison with the pinned upstream source showed the original closes the menu
through `HyprlandFocusGrab { active: window.menuOpen; windows: [window];
onCleared: window.closeMenu() }`. Our derived dock had removed that block and a
generator guard plus `tests/test_desktop_panels.py` actively forbade it, although
it is a pure Wayland protocol component with no execution. The pinned Quickshell
build provides the element (src/wayland/hyprland/focus_grab, exported via
`Quickshell.Hyprland`), so the exclusion was unnecessary. `desktop_frontends.dock()`
now keeps the upstream grab block unchanged (diff: IDENTICAL); only the
monitor-remap guard (`ScreenMoveRemap`) remains excluded with the always-mapped
derived surface. Added a parity test for outside-click dismissal, unforbade the
component in panel tests, updated `docs/dock-parity.md` and
`docs/desktop-panels.md`, regenerated the staged mirror and provenance
(work/register-desktop-preview.py, 74 files). 315 tests pass. Release packaging
follows; the menu itself remains an unclicked native test.

## Title-change rule ordering: traced cause and matcher correction (2026-10-25)

With the diagnostic plugin active, the user reproduced the visual failure in a
new Ghostty (`0x5cf295f88920`). The trace shows rules changing hidden=false to
hidden=true about 1.6 seconds after mapping, then assigning 0x0 geometry, while
the IPC window retains `omabuntu-mode-floated`. This is not render-pass culling
of that window. Source evidence: `Window.cpp` title updates emit TITLE|CLASS;
`WindowRuleApplicator::resetProps` erases custom effects without adding them to
`effectsNuked`, and `propertiesChanged` reruns the class-only hide rule but skips
the tag-only show rule on such updates. The plugin consumes the resulting hide
effect as designed. Earlier render-only hypotheses were not the root cause of
this reproduced disappearance.

Backups: `work/hyprbars-rule-fix/20261025T145732Z/`. Added a regression contract
requiring CLASS participation in the show rule and demonstrated it red. A
controlled disposable Ghostty emitting three OSC title states also reproduced
hidden=true / 0x0 before the change (`title-red.json`). Updated the show rule in
`config/hypr/hyprbars.lua` to match both class `.*` and the floated tag. Applied
only the additional matcher to the existing named runtime rule: no effect,
button, plugin reload or compositor reload was added. The same controlled probe
then retained hidden=false and 1100x30 geometry at all three title states
(`title-green.json`). All 314 tests pass. The user subsequently confirmed that the titlebar disappearance is fixed.

The user visually accepted the matcher correction. The diagnostic plugin is
still loaded; the manager artifact and persistent user configuration remain
unchanged. Returning to the
manager artifact requires the same controlled reload/recovery procedure. Dock
pinning/drag and other acceptance gaps remain separate; this finding does not
establish overall dock parity.

## Approved diagnostic plugin activation (2026-10-25)

The user approved temporary loading of the trace plugin, including the internal
configuration reload. Saved prestate under
`work/hyprbars-render-trace/load-20261025T143553Z/previous.json`, unloaded the
exact manager artifact path, and loaded the diagnostic library. Applied the
button/rule snippet exactly once after the plugin replacement, restored known
workspace layouts and saved Omabuntu tags/floating flags where necessary, and
restored the runtime apps binding. The shell/bar was not restarted, retaining
its session ownership singleton. `after.json` records the resulting state;
config errors are empty and the apps bind is present. No hyprpm store or
persistent Hyprland configuration was modified.

Opened an owned Ghostty named `omabuntu-render-trace` on workspace 6 (initial
address `0x5cf298f17630`, pid 111894). Its trace transitions from initial hidden
state to visible after the claim, then keeps hidden=false, enabled=true,
decorate=true, alpha=1, valid 1100x30 geometry, colour alpha about 0.9333 and no
forced colour. Both draw entry and render-pass execution continue; no discarded
pass was recorded in this initial run. These metadata do not prove pixels were
visible or reproduce the user's visual failure. Awaiting an observed failing
Kitty/Ghostty with the trace active before identifying a root cause. Diagnostic
plugin and the owned test window are left running for that observation.

## Offline hyprbars render trace build (2026-10-25)

The titlebar failure remains open. The user observes that Fonts keeps its own
bar and can make Ghostty's bar visible again, and that a configuration reload
appears to repair existing terminal bars. Neither observation establishes the
specific failing internal state. The clean pinned plugin source was copied into
`work/hyprbars-render-trace/source/` and instrumented without modifying the
original checkout or hyprpm store. `work/prepare-hyprbars-trace.py` built
`work/hyprbars-render-trace/build/libhyprbars.so` successfully against the existing
reviewed headers. Patch, build log, artifact hash and provenance are recorded in
that directory. Status is **diagnostic-built-not-loaded**.

Instrumentation records only workspace-6 window addresses, visibility flags,
assigned geometry, alpha, rule updates, draw entry, render execution and pass
discard events. It contains no titles, commands or terminal contents and caps
output at 20000 lines. The trace does not change rendering behaviour. Loading
remains a separate approval: the plugin's init triggers a configuration reload,
so runtime bindings/rules and session ownership require an explicit recovery plan.

## Apps shortcut recovery and plugin-load side effect (2026-10-25)

The apps shortcut regressed: `hyprctl binds -j` contained no Space binding,
while `hyprctl globalshortcuts -j` still registered `omabuntu:apps`. Restored the
runtime `SUPER + ALT + SPACE` binding to `hl.dsp.global("omabuntu:apps")` and
verified one Space binding with modmask 72. Previous binds and apply result are
recorded under `work/apps-shortcut-recovery/20261025T141006Z/`.

Important correction: the pinned hyprbars `PLUGIN_INIT` calls
`HyprlandAPI::reloadConfig()` at main.cpp:270. Earlier statements that manually
unloading/loading the plugin avoided a compositor configuration reload were
incorrect. This explains loss of the runtime-only shortcut during plugin resets.
Do not load the proposed diagnostic plugin until this side effect and recovery
of all runtime rules/bindings/session ownership have been addressed and approved.
The diagnostic preparation script exists under work/ but has not been run or
loaded. No persistent user configuration was changed during shortcut recovery.

## Terminal-independent titlebar failure (2026-10-25)

Disabling title text did not resolve the failure; `bar_title_enabled` has been
restored to true. The user also reproduces the issue immediately in Kitty,
so the Ghostty prompt/title-change hypothesis is insufficient. A correctly
addressed `hyprctl decorations address:<hex> -j` query finds exactly one Hyprbar
(priority 10005) on each of two Ghostty windows and one Kitty window on workspace
6. All three are floating and retain `omabuntu-mode-floated`, with fullscreen 0.
This confirms attachment, not visibility: `m_hidden`, assigned geometry and
render-pass culling still need direct evidence. Earlier unaddressed `decorations`
queries returning `none` were not valid decoration inventories. No additional
runtime workaround or plugin reload was applied in this investigation.

## Prompt-triggered titlebar diagnostic (2026-10-25)

The user narrows the disappearance to the moment Ghostty displays the shell
prompt. Prompt initialization can also change the window title; that correlation
is not yet proven to be the cause. The plugin renders changed titles through
`renderBarTitle()` / `renderText()`. To isolate that path, the runtime diagnostic
sets only `plugin.hyprbars.bar_title_enabled = false`; background and buttons
remain enabled and damage tracking remains 2. Previous state (title enabled,
unset default) and apply result are recorded under
`work/titlebar-prompt-diagnostic/20261025T140251Z/`. No plugin reload or new button
registration. Awaiting the new-window observation; this is not a permanent fix.

## Titlebar render diagnostic (2026-10-25)

The user still sees a titlebar briefly, then a fully transparent background on
workspace 6. Earlier claims of a working new-window titlebar were premature:
floating state and a tag do not establish rendering, and floating client-size
deltas do not establish bar visibility. A runtime-only diagnostic sets
`debug.damage_tracking` from 2 (unset default) to 0, forcing full redraw, to
separate damage tracking from rule/colour behaviour. Prior state and apply
result are under `work/titlebar-render-diagnostic/20261025T132817Z/`.
No plugin reload, button registration, persistent config edit or bar restart.
The user reports that full redraw prevents the transparent-background phase,
but the bar still disappears after roughly two seconds. For Ghostty, leaving
and returning to the workspace makes the bar visible again. This points toward
render invalidation/occlusion or decoration geometry, not proof of a lost tag;
the exact cause remains unconfirmed. Damage tracking was restored to 2 and the
result recorded in `restore.json`. No permanent workaround was applied.

## Foundation

Authorization: create a standalone repository for eventual public publication,
write all files in English, and inventory the current Ubuntu target read-only.

Changes:
- Initialized a local Git repository; no commit, remote, or publication.
- Added architecture, compatibility, safety, publication, and rollout documents.
- Added a Python-standard-library diagnostic CLI and synthetic tests.
- Kept private source reference material outside the repository.
- Generated local reports only under ignored private directories.

Target observations:
- Ubuntu 26.04.1 LTS; current session is GNOME on Wayland.
- Hyprland 0.56.2 package installed from an existing third-party source.
- No Hyprland runtime evidence available in the current process environment.
- Quickshell absent from PATH; local APT metadata shows no candidate.
- Qt base/declarative candidates are 6.10.2; qmake6 absent.

Backup/rollback:
- No existing desktop files were modified, so no target configuration backup
  was needed for this foundation.
- No package installation, source change, reload, service activation, lock,
  suspend, reboot, logout, or session switch was performed.

Open gates:
- Confirm version-specific Hyprland APIs and Quickshell packaging/build options.
- Approve package sources and required features before implementation.
- Select a project license and complete provenance review before publication.
- Establish the target security policy and recovery path before lock testing.

Validation:
- 14 automated diagnostic tests passed, including timeout/error handling,
  private permissions, session gating, and refusal of symlinked report parents.
- Live doctor collection completed; local APT query succeeded.
- The grouped dpkg query returned a nonzero status because some requested
  packages are absent; partial output and stderr remain in the private report.
- Hyprland runtime probes were explicitly skipped outside its session context.
- Git ignore rules verified for reports, snapshots, backups, and environment files.
- No functional desktop, QML, authentication, or suspend test has been performed.

Next: finish compatibility investigation without changing the active session.

## MIT license and version-specific compatibility research

Authorization: the user approved MIT for original project work and continuation
of the project. No package installation or desktop activation was authorized.

Changes:
- Added the MIT License for original Omabuntu code and documentation.
- Updated publication and development policies to reflect the approved license.
- Added version-specific research, a capability matrix, and a proposed Quickshell
  dependency/build strategy with explicit approval gates.
- Extended doctor to record the installed Hyprland binary version independently
  of the running desktop; added a regression test for missing binary evidence.

Evidence:
- Installed Hyprland --version-json reports the exact source-reference commit:
  efb50993780079460b0cbed1363e2166a2de1d9f (v0.56.2, clean).
- Reviewed the official v0.56.2 example and main implementation and the installed
  Lua API stubs. Native Lua is the preferred route; full runtime parity is untested.
- Resolved source Quickshell to 2b4501a282689792b62e94f3fb30d8f512324fe6.
- Its build baseline is Qt 6.6; target Core/QML/Quick 6.10.2 packages are installed.
- Reviewed pinned build/module sources. Crash handling needs cpptrace; optional
  CMake vendoring can fetch source, so no build was started.
- Local APT candidate checks are read-only and do not approve package sources.
- Raw research downloads remain under ignored private work/research/.
- Some generic/versioned documentation URLs redirected to old documentation or
  returned 404. Exact upstream source refs were used instead; limitations recorded.

Backup/rollback and boundaries:
- Only repository files and ignored reports were written; active desktop files
  remain untouched.
- No source snapshot files changed and no third-party runtime was imported.
- No package installation, build/configure step, remote, commit, publication,
  service activation, reload, lock test, or session change.

Validation:
- All 15 automated tests passed after extending the binary-version probe.
- Live doctor collected the installed binary version successfully in GNOME;
  session probes remained skipped and absent packages remained explicit.
- Local Markdown links passed; private research and reports are ignored by Git.
- No functional desktop, shell, authentication, or suspend acceptance is claimed.

Next: finalize an approved Quickshell dependency plan and packaging-patch review.
Do not install dependencies or enable the shell before explicit approval.

## Simulated package plan and isolated Lua prototype

Authorization: proceed with the concrete package plan, read-only APT simulation,
and a staged minimal Lua prototype. This did not authorize package installation,
active configuration application, or a session switch.

Changes:
- Added packages/quickshell-plan.json with pinned upstream candidates, explicit
  dependency groups, proposed crash-handler-preserving options, and limitations.
- Added tools/package_plan.py and the plan quickshell CLI command.
- Extended private report allocation for package plans and profile checks.
- Added config/hypr/minimal.lua: an independently authored 47-binding prototype
  without shell startup, plugins, lock/idle/suspend, or provisioning.
- Added check-profile with exact-build gating, a private hashed profile snapshot,
  isolated HOME/XDG directories and working directory, and no inherited display
  or D-Bus connection variables.
- Added mocked planner/profile tests and updated English documentation.
- No upstream runtime source was copied into distributable project files.

Dependency evidence:
- Audited all 55 CMake/build-definition files listed by the pinned Quickshell tree.
- Included GBM/EGL/Vulkan/GLib requirements and explicit QML runtime candidates.
- Resolved cpptrace v1.0.4 to 3db8da80111171c219ab5839905771386bee06b3.
- Reviewed external libdwarf/libunwind options to avoid implicit CMake downloads.
- Proposed separate cpptrace build with Quickshell VENDOR_CPPTRACE=OFF and crash
  handler retained. This is not yet an approved or compiled build.

Validation:
- All 36 automated tests passed.
- Final manifest: 39 explicit requests. APT simulation succeeded with 96 new
  packages, 0 upgrades/changes, and 0 removals; no installation occurred.
- New-package origin labels in the solver output identify Ubuntu archive suites.
- Read-only metadata matched all 96 exact transaction versions: 28,418,960 archive
  bytes and 188,808 KiB declared installed size, excluding build workspace and
  source downloads. Size evidence: the earlier identical package transaction in
  work/package-plan/20261023T233306.335410Z/size-metadata.json.
- Native Hyprland 0.56.2 --verify-config accepted the private prototype snapshot
  with return code 0 and config ok.
- Final-manifest simulation: work/package-plan/20261023T233706.380054Z/report.json.
- Native profile evidence: work/profile-check/20261023T233304.775429Z/report.json.
- The prototype deliberately uses global workspaces, no custom Compose, and no
  full shell/theme/window-rule parity. No interactive acceptance is claimed.

Backup and rollback:
- No active desktop files were changed; no target configuration backup was
  required for this preparation. New artifacts are inside the repository or
  ignored private work/. Removing a staged artifact is not a desktop rollback.
- Future application must first back up every affected target object and record
  its exact previous state and reversal.
- Original source snapshot remains reference-only.
- No APT refresh, new package source, build/configure, privileged command,
  service activation, reload, lock test, reboot, logout, commit, or upload.

Next approval gate:
- Review the manifest and full private APT report before installing dependencies.
- Approve pinned source builds and staging without active desktop installation.
- Keep configuration application and shell/lock testing separately gated.

## Approved dependencies: blocked on interactive authentication

Authorization: the user approved installing the simulated 96 dependency packages
and building/staging the two pinned upstream sources in the project workspace.
This does not include custom runtime system installation, active configuration
changes, shell activation, service changes, or lock testing.

Pre-install checks:
- Re-ran the simulation: 96 new packages, 0 upgrades/changes, 0 removals.
- Compared manifest, pinned command, and all Inst/Remv lines with the reviewed
  final-manifest report; the transaction is identical.
- Rechecked plan: work/package-plan/20261023T233816.014396Z/report.json.
- sudo -n -v reported that interactive authentication is required.
- Stopped before any package installation, source build, or privilege workaround.

Preparation:
- Saved private package versions/status, automatic/manual package marks, and held
  packages under work/dependency-install/.
- Recorded target-local authorization and the manifest hash there.
- Generated work/dependency-install/install-dependencies.sh with the exact pinned
  install command. It re-simulates and refuses a changed transaction before sudo.
- The helper has no --yes flag. Authentication and APT confirmation must happen
  in the user's own terminal. No credentials are requested by the assistant.
- bash -n accepted the helper; the helper itself was not executed.
- Package marks and standard package hooks may change during real installation;
  the saved baseline is evidence, not a complete system backup or auto-rollback.

Next:
- User runs the private helper in their own terminal.
- After success, verify actual installed versions and package marks against the
  saved baseline before proceeding with approved workspace-only builds.
- If the helper refuses a changed transaction or APT proposes a different scope,
  stop and review; do not bypass the guard or add repositories.

## Verified dependencies and workspace source builds

Authorization: the user reported completing the approved interactive dependency
installation. Workspace-only pinned source compilation/staging was already
approved. No custom system installation or desktop activation was authorized.

Verification:
- All 96 expected new package versions are installed.
- No pre-existing package version changed and none was removed.
- Recorded before/after package status and marks under work/dependency-install/.
- APT added 36 manual marks; no marks were automatically reset.
- Verification summary: work/dependency-install/verification.json.

Changes:
- Added upstream/source-lock.json with exact commits, HTTPS archive URLs,
  compressed sizes, SHA-256 hashes, and license identifiers.
- Root CMake files in both fetched archives matched previously inspected sources.
- Added tools/build_runtime.py: plan-only by default, explicit --build opt-in.
- Added safe archive extraction and private build/source-cache directories.
- Builds use Bubblewrap private namespaces, no network, read-only source mounts,
  and only project-local writable build/stage/home paths.
- CMake installs only into DESTDIR=/stage with logical /opt/omabuntu-runtime
  prefix inside the sandbox. No host /opt runtime was installed.
- Added 11 build-contract tests, for 47 passing automated tests overall.

Build evidence:
- Initial run: work/builds/20261023T234913.200835Z/.
- Initial compile succeeded but default upstream configuration omitted QML
  installation metadata. Corrected INSTALL_QML_PREFIX=lib/qt6/qml.
- Clean corrected run: work/builds/20261023T235404.702836Z/.
- All 8 sandboxed build/stage/version steps passed.
- cpptrace v1.0.4 built using system libunwind/libdwarf.
- Quickshell's cpptrace signal-safe-unwind compilation and execution probe passed.
- Quickshell 0.3.2 reports revision 2b4501a282689792b62e94f3fb30d8f512324fe6,
  distributed by Omabuntu.
- Required metadata is present for all 13 checked QML module families.
- Corrected stage contains 95 file/link artifacts with recorded hashes/targets.

Open warnings:
- Shader compilation attempted spirv-opt, missing from the initial package plan.
  Do not silently add a package or disable the optimizer.
- Supplemental local simulation for spirv-tools=2026.1-1 proposes 1 new package,
  no upgrades, and no removals. Evidence:
  work/dependency-install/spirv-tools-simulation.json.
- This supplemental package is not installed or approved.
- Qt static-import/link-target warnings, upstream compiler warnings, and Wayland
  XML validation warnings remain for explicit runtime assessment.
- Final report status is staged-with-warnings, not desktop-ready.
- No complete shell or QML service-loading acceptance test has been performed.
- Original Omarchy packaging-patch equivalence is still unresolved.

Backup/rollback and boundaries:
- Dependency rollback requires a separately reviewed transaction and prior mark
  evidence; no automatic autoremove or mark restoration was performed.
- Source/build/stage/cache outputs stay under ignored work/; public candidate
  files contain original tooling/docs and source metadata, not upstream binaries.
- No custom system runtime installation, PAM policy change, user configuration
  application, service activation, reload, lock test, or session transition.
- No commit, remote, or publication.

Next:
- Obtain approval for the supplemental spirv-tools package.
- After installation, perform a clean shader build, not an incremental build
  that might reuse the previous shader outputs.
- Then perform separately controlled QML imports and audited shell integration;
  compilation/version success alone is not acceptance.

## Supplemental shader tool and clean rebuild

Authorization: the user reported completing the proposed interactive installation
of spirv-tools=2026.1-1. Previously approved pinned workspace-only builds remain
in scope; custom system runtime installation and desktop activation do not.

Verification:
- spirv-tools 2026.1-1 is installed and /usr/bin/spirv-opt runs successfully.
- Compared installed package state with the post-96-package snapshot: exactly
  spirv-tools is new, no existing version changed, and nothing was removed.
- The only APT-mark change is the new manual spirv-tools mark; automatic and
  held marks are unchanged. No marks were reset.
- Evidence: work/dependency-install/spirv-tools-verification.json and
  spirv-tools-mark-changes.json, plus private mark snapshots.

Changes and purpose:
- packages/quickshell-plan.json now includes spirv-tools (40 explicit requests)
  and distinguishes the candidate recipe from target/deployment approval.
- tools/build_runtime.py requires spirv-opt, probes it inside Bubblewrap, checks
  and hashes both expected shader outputs, and rejects optimizer failures.
- Known non-shader diagnostics remain visible in warning counts and result state.
  Fixed a post-build scanner error that treated .qsb directories as files.
- tests/test_build_runtime.py and tests/test_package_plan.py cover the added
  dependency, warning classification, regular-file scanning, empty shader output,
  and optimizer failures. All 53 automated tests pass.
- README, runtime/package/testing/compatibility/capability/decision documentation
  reflects the completed installation and remaining warnings.

Clean build evidence:
- Fresh workspace: work/builds/20261024T001419.742301Z/; no prior shader reuse.
- All nine sandboxed configure/build/stage/version/tool steps passed.
- Both shaders are nonempty (1378 and 1380 bytes), with recorded SHA-256 hashes.
- Zero logged shader optimizer failures; 13 QML metadata checks and 95 staged
  file/link artifacts pass the post-build assessment.
- The original report.json retains the post-build directory-scanner failure.
  After fixing the scanner, assessment.json records successful reassessment of
  unchanged artifacts and the original report/tool hashes. Compilation did not
  need repeating; the failure was in artifact reporting, not a compiler step.
- Result remains staged-with-warnings: 21 Qt QML link-target diagnostics,
  2 Wayland XML warnings, 210 compiler warnings (including repeats), 2 QML
  base-type warnings, and 2 unused CMake-option notices. No warnings suppressed.
- Missing-return and strict-aliasing warnings require assessment; installing the
  shader optimizer does not repair or prove harmless upstream C++ behavior.
- Final 40-request APT simulation reports zero new packages, upgrades/changes, or
  removals: work/package-plan/20261024T002233.988372Z/report.json. It remains a
  review-required simulation, not authorization to install on another target.
- Final tests (53), candidate JSON, local Markdown links, whitespace, Git-ignore
  checks, and git diff --check passed. Private test log:
  work/shader-rebuild-tests.log. All candidate project files remain uncommitted.

Backup/rollback and boundaries:
- No active Ubuntu configuration changed; no desktop-path backup was necessary.
- Existing source/build reports remain intact. New evidence/staging stays under
  ignored work/. Repository changes do not alter the active runtime.
- Dependency removal or APT-mark restoration requires a separately reviewed plan;
  no package removal, broad autoremove, or automatic mark restoration performed.
- No new package source, privileged assistant command, custom system installation,
  full shell, desktop agent, PAM conversation, lock test, reload, or session switch.
- No upstream source modifications, reference changes, commit, remote, or upload.

Next:
- Perform controlled isolated linkage/QML import probes without host session
  access or service activation, then assess remaining upstream diagnostics.
- Audit shell/helpers and resolve packaging-patch equivalence before an approved
  graphical trial. Keep desktop integration and authentication acceptance gated.

## Isolated linkage and QML runtime probes

Authorization: the user explicitly approved the proposed isolated linkage/QML
import checks without host session access, full shell, or service activation.

Changes and purpose:
- Added tools/check_runtime.py, plan-only by default with explicit --run and
  --build-dir selection. It accepts only recorded builds and generated fixed
  module/type probes, not arbitrary QML or shell configurations.
- Validates source locks, successful original build steps, reassessment hashes
  when needed, and exact staged artifacts before execution.
- Uses a separate Bubblewrap runtime sandbox: runtime/probes read-only at their
  logical paths, one private per-case HOME writable, cleared environment, no
  host home/session sockets, displays, GPU devices, network, or real buses.
- Reviewed pinned launch/plugin initialization and config/exit paths for probe
  assumptions. The diagnostic-only crash handler opt-out prevents debugger or
  relaunch behavior; it does not change the compiled runtime or host security.
- Probes construct only a minimal nonvisual ShellRoot and then quit normally.
  Representative types use null properties, not service object constructors,
  singleton accesses, or authentication/lock methods. Disposable Quickshell
  IPC/log files are confined to private per-case state.
- Added tests/test_runtime_check.py with 15 synthetic safety/acceptance tests;
  total automated suite now passes 68 tests without launching Qt/services.
- Added docs/runtime-check.md and updated README, testing, compatibility,
  capability, build, decision, and Quickshell investigation documentation.

Evidence and interpretation:
- Final report: work/runtime-check/20261024T082502.926718Z/report.json.
- All 32 checks passed: sandbox startup, ELF inspection, ldd -r, 28 positive
  module probes, and one missing-import negative control.
- 19 Quickshell and 9 Qt modules import. 24 representative nullable types resolve.
- Wayland, Hyprland, I3, and Greetd remain explicitly import-only probes.
- Positive probes logged no WARN/ERROR/FATAL/CRITICAL diagnostics and exited 0
  with both their completion markers and Configuration Loaded.
- Negative control reported the exact missing module, no success marker, and
  expected exit code 255. A crash, timeout, or unrelated failure is not a pass.
- ELF RUNPATH is $ORIGIN:$ORIGIN/../lib. ldd -r reports no missing libraries or
  unresolved relocation symbols. This does not cover every future dlopen path.
- Original stage hashes/link targets remain unchanged. Earlier exploratory
  reports remain intact; no upstream code or compiler flags changed.
- Known Qt link-target warnings do not prevent these bounded probes. This is
  not a blanket dismissal of build/tooling diagnostics or C++ correctness risks.
- Final 68-test run passed; private log: work/runtime-check-tests.log. Candidate
  Python/JSON syntax, Markdown links, whitespace (33 files), Git-ignore checks,
  and git diff --check passed. Plan-only CLI behavior was rechecked. Candidate
  files remain uncommitted; the explicit whitespace scan also covers untracked
  files that git diff --check does not inspect.

Backup/rollback and boundaries:
- No existing Ubuntu configuration changed; no active desktop-path backup was
  required. All probe state/logs are newly created ignored work/runtime-check/
  artifacts, not installed configuration or an active runtime.
- No packages, new repositories, custom system runtime, host services, full
  shell, PAM conversation, lock/idle/suspend, reload, session switch, or reboot.
- No source-reference changes, commit, remote, or publication.
- This step does not provide a package rollback or authorize removing previous
  dependencies; package rollback still requires a separate reviewed plan.

Next:
- Audit original shell/helper dependency paths and packaging-patch equivalence.
- Assess remaining compiler/protocol/tooling warnings without hiding them.
- Only then propose a separately approved graphical trial with explicit backups,
  service ownership, recovery, and rollback. No functional/security acceptance
  follows from successful imports or type resolution.

## Original shell/helper and exact packaging audit

Authorization: the user approved continuation with the proposed original shell,
helper, and Omarchy packaging-patch audit. This is reference/public-source research
and workspace tooling/documentation only, not shell activation or source import
into distributable files.

Evidence and findings:
- Read the private handoff/reference and verified its integrity: 2,286 regular
  files, 558 symlinks, both original-copy manifests pass. Existing target handoff
  remains private and historical; no fresh machine-wide inventory was needed.
- Original first-party non-bar plugins default to enabled. plugins: [] does not
  disable services. The 40 manifests include 10 services, including lock, idle,
  notifications, Polkit, battery, media, background, dock, nightlight and remote
  session. Enabled services and keepLoaded panels can be created at startup.
- Shared AppLibrary/BrightnessKeys/BackgroundIntro and Commons helpers introduce
  startup work outside the plugin manifest boundary. Missing/invalid-config
  fallback has no deny-by-default policy. No fail-closed loading is implemented.
- Menu actions and when/checked guards use bash; hiding dangerous rows alone
  does not validate providers, guards, extensions, or dynamic commands.
- Manually traced theme-set -> theme-set-browser -> theme-set-browser-policy:
  cosmetic theme switching can request sudo/pkexec and write managed browser
  policy. This is excluded on the corporate target, not an Ubuntu theme adapter.
- Reviewed launcher/restart/IPC session selection and supervision, power-profile
  and nightlight routes, native authentication/agent ownership, and original
  autostart provisioning/hooks. No helper was approved or executed.

Packaging provenance:
- Located the public package repository through a targeted reference URL hint.
  Read-only GitHub history identified commit
  2be7cd983944f50612338124ec6725da95dceb2e.
- Its Quickshell PKGBUILD SHA-256 exactly matches the captured .BUILDINFO value:
  e871efd5b0705d16226b4e8cd0b9ed99269129a62cc4590583df5581c25ab6aa.
  It is package release -1; the current default branch was -3 and did not match.
- Fetched the matching revision's load_qtquick_611.patch and ALPM hook as text;
  each hash matches its entry in the matching recipe. No recipe was sourced,
  no patch applied, and no transaction hook installed or translated.
- The root OmarchyLoadPatch marker rewrites unversioned QtQuick imports to 6.11
  and extends scanner/interceptor coverage. Its stated reason is the new QtQuick
  Color singleton in Qt 6.12 shadowing Omarchy's singleton.
- Do not blindly apply that workaround to Qt 6.10.2. Keep the existing unpatched
  runtime pending actual original local/dynamic import/API testing. Identifying
  the recipe does not establish signed provenance or original binary equality.
- Raw downloads and checksum evidence stay private in work/research/shell-audit/.
  Public upstream/quickshell-packaging.json contains provenance metadata only,
  explicitly not a build input. Build flags/runtime outputs remain unchanged.

Changes and tests:
- Added tools/audit_shell.py: bounded read-only text hashing, manifest validation,
  source marker indexing and conservative lexical helper closure. It never
  executes/sources/imports reference programs or performs network requests.
- The initial audit refused a captured relative helper alias. Added explicit
  passive handling for same-directory aliases to captured regular files, without
  following the link; unsafe targets and alias chains still stop the audit.
- Final static report: work/shell-audit/20261024T091037.986335Z/report.json.
  777 regular text files, 538 helper entries (one passive alias), 40 manifests,
  422 potential lexical helper dependencies. These are not executed calls or
  a complete call graph; sourced libraries/dynamic/bare subcommands remain gaps.
- Added 17 tests in tests/test_shell_audit.py; all 85 automated tests pass.
  Final log: work/shell-audit-tests.log. Candidate Python/JSON syntax, Markdown
  links, whitespace (37 files), Git-ignore checks and git diff --check pass.
  Rechecked the pinned packaging cache hashes and unchanged reference integrity
  after the audit; no snapshot changes were made.
- Added docs/shell-audit.md; updated research/provenance, package/runtime/testing,
  compatibility-decision, capability and README links/status without hiding
  earlier results. Original Omarchy source/license/assets still need provenance
  review before any distributable source import.

Backup/rollback and boundaries:
- No active Ubuntu configuration or service changed; no target-path backup was
  needed. New audit/research reports stay under ignored work/. Existing source,
  runtime build, stage, and diagnostic reports were not overwritten.
- No package installation, source/repository addition to APT, privileged command,
  Arch program, desktop helper, full shell, auth/lock/idle/suspend test, service
  activation, reload, reboot, logout, or session switch.
- No snapshot/inventory/source-analysis changes; no third-party code/assets in
  public candidate files; no commit, remote, upload, or publication.
- Package rollback still requires a separately reviewed transaction. This audit
  creates no active configuration or service that needs desktop rollback.

Next:
- Pin original Omarchy source/license evidence, then implement/test an independent
  positive loader policy before object creation, with safe fallback/reload paths.
- Gate shared startup objects, command routes, third-party discovery and every
  service. A tiny original bar/clock/spacer trial is only a future candidate,
  not a complete shell or currently approved graphical test.
- Continue warning/API review and isolated source-loading tests before requesting
  a graphical trial with explicit backup, ownership, recovery and rollback.

## Original source pin and fail-closed host prototype

Authorization: the user approved pinning original sources/licenses and preparing
an independently tested, default-deny load policy. This covers project files and
fixed nonvisual authored fixtures in the existing isolated staged runtime, not
original-shell execution, graphical/session work, services or authentication.

Source/license evidence:
- A bounded default-branch search of 20 Omarchy PKGBUILD revisions did not match
  the captured recipe hash. This remains unresolved; no matching recipe invented.
- Located public v4.5.0-rc1, commit
  03ff1eff3812933f7088484533784d2f63eaf19a. All 249 captured shell regular files
  match its non-truncated Git tree by actual-byte Git blob hashes. The private
  comparison also records SHA-256 for every entry. 536 of 538 helper entries
  match; omarchy-nvim-setup and its nvim-refresh alias are absent/unapproved.
- Both source and captured version files contain 4.0.0.alpha despite the RC
  package/tag. Source identity is established by content, not that version file.
- The full archive exceeded the conservative 64 MiB response bound and was not
  saved/extracted. Switched to bounded pinned Git-tree/license/version reads.
  No source script, PKGBUILD, installer or patch was executed.
- Added upstream/omarchy-source.json and the complete unchanged public upstream
  notice licenses/Omarchy-MIT.txt, SHA-256
  717ba1949502290f8e47688ae2e323acd06c8ca47aec9f7596b15f678c1af4a2.
  Raw research/comparison stays private under work/research/omarchy-source/.
- Recorded additional Omapager/Neil Jagdish Patel attribution in notifications,
  Elsewhen author metadata, six branded SVGs and emoji/font provenance gates.
  Root MIT is not blanket asset/derived-component clearance. No original runtime
  code, helpers, datasets, fonts or assets imported into public candidate files.

Implementation:
- Added config/shell/LoadPolicy.js and GuardedHost.qml. The host is an independent
  nonvisual QtObject with empty catalog and no original shared startup objects,
  discovery, commands, theme hooks, hardware, service or auth integrations.
- Exact bounded ID-only configuration schema; no catalog/URL/command input through
  user JSON. Reject the whole plan before Qt.createComponent for missing/invalid,
  legacy, unknown/duplicate/protected IDs, service/capability or unsafe URL data.
- Catalog only supports trusted authored fixtures under /probe/components/.
  All ten first-party service IDs are denied even if mislabeled. Snapshot URLs
  before construction; handle partial failures and reentrant approval revocation.
- Reload/configuration change/catalog replacement/repeated start revoke ownership
  and permanently prevent same-instance restart. Deferred Qt destruction cannot
  overlap replacement creation in that instance. No automatic host/process restart.
- This is not an OS sandbox or proof that arbitrary QML has no side effects.
  Empty capabilities are a review assertion, not privilege enforcement. The
  original shell is not integrated; starting it would bypass this new host.
  Real source/dependency staging hashes and startup integration remain gates.

Tests/evidence:
- Added plan-only tools/check_shell_gate.py. Explicit --run accepts only fixed
  authored QObject fixtures, verifies the existing source lock/staged artifacts,
  and reuses the Bubblewrap runtime-probe isolation with per-process 20-second
  limits. No host home, network, real buses, GPU, display or compositor access;
  no less-isolated fallback and no original code/plugin/service execution.
- Initial exploratory run work/shell-gate/20261024T093538.758091Z/report.json
  failed a positive fixture counter. Relative JS library imports via qs: and
  file: component URLs did not share its expected counter instance. Retained
  this evidence; changed the harness to observe actual QObject initialization
  and destruction signals, not assumed URL-alias library identity.
- Intermediate runs at 20261024T093737.230772Z and 20261024T094133.235693Z remain
  unchanged. Final work/shell-gate/20261024T094908.609350Z/report.json passes
  all 42 fixed cases, including attempted catalog injection in configuration.
- Positive construction, denial-before-preparation, partial failure cleanup,
  required-property null creation, sticky reload/replacement, URL snapshot and
  reentrancy checks pass. An intentionally wrong assertion exits exactly 42
  with its expected error; crash/timeout/unrelated failure cannot pass instead.
- Ordinary cases have zero WARN/ERROR/FATAL/CRITICAL except the single retained
  expected required-property WARN; the assertion-negative control retains one
  expected ERROR. All other diagnostics are rejected. Reports include commands,
  code/probe/log hashes, diagnostic counts, unchanged probe inputs and stage.
- Added 15 unit contracts in tests/test_shell_gate.py. All 100 automated tests
  pass; log work/shell-gate-tests.log. Unit tests themselves never start Qt.
- Candidate Python/JSON syntax, local Markdown links, whitespace (44 files),
  git diff --check and unchanged reference integrity pass (2,286 files,
  558 symlinks, both manifests). Docs/README/provenance/status links updated;
  docs/shell-gate.md records exact limitations, evidence, backup/rollback/next gate.

Backup/rollback and boundaries:
- Only project files and ignored private reports changed. No active Ubuntu path
  changed, so no active-path backup or desktop rollback was needed. Prior stage,
  source/reference and reports remain unchanged; dependency rollback still needs
  its own reviewed transaction. No package/install/APT source/privileged command.
- No custom runtime deployment, original shell/helper/plugin execution, graphical
  trial, service activation, real reload, auth/lock/idle/suspend test, logout,
  reboot/session transition, commit, remote, upload or publication.
- Fixture success is not original-shell/API/graphics/security acceptance. Review
  a tiny original-widget dependency closure and applicable notices next; only
  then consider production gating/source staging and separately approved graphics
  with explicit affected paths/backups, ownership, recovery and rollback.

## Widget dependency review and first original pure-code import

Authorization: the user requested continuation of the original bar/clock/spacer
review, then retry/continuation of its checks. Work stays within project source,
license/provenance review and contained nonvisual diagnostics. No desktop, service,
package, privileged, graphical or authentication activation was authorized.

Static review:
- Added tools/audit_widgets.py: optional explicit reference/evidence inputs;
  verify the cached non-truncated Git tree response against its pinned provenance,
  then match every visited captured file to its actual-byte Git blob.
- Follow conservative local module/type/JS/literal-QML references with bounded
  reads/graph size, cycle handling and link/traversal/import/module guards.
  Record helper/risk markers, native imports, unresolved/dynamic source lines and
  lexical ambiguities. Never execute source/helpers, contact network or approve
  component loading. Comments/strings count; runtime dependencies remain gaps.
- Final work/widget-audit/20261024T101847.309301Z/report.json: 38 distinct pinned
  files; lexical closures bar 20, clock 33, spacer 11, including module metadata.
  These are not eager object counts or complete dynamic/semantic closures.
- Original bar completion invokes initial glass sync, starts the bar-off Bash
  probe and creates per-screen layer surfaces; registry/custom-QML/command routes
  remain exposed. Empty layout/hidden state is not inertness.
- Original clock's hidden calendar Loader is active at construction. Its shared
  UI, Style/Color/I18n, IPC, persistence and timezone action dependencies must be
  separated before a constrained UI trial. No original QML object was created.
- Spacer is a simple leaf but defaults through its null bar API to Style size;
  Style starts hyprctl/font queries and watchers. Atomically injecting a complete
  safe API could avoid the fallback, but has not been validated. Conservative
  I18n/Util function references do not prove eager execution of every singleton.

Per-file license/source decision:
- Read the complete original clock Model.js and reviewed its date/number/string/
  array math and guarded CommonJS export. No Qt/Quickshell, QML objects, imports,
  commands, files, network/service APIs or separate license/copyright notice.
- Fetched this file alone from the pinned public commit with a 64 KiB bound;
  verified Git blob and equality to the capture before importing. No private
  user configuration, original full shell, QML/plugin, helpers or assets copied.
- Imported unchanged vendor/omarchy/shell/plugins/panels/clock/Model.js: 12,174
  bytes, SHA-256 101514693517f694203841a4f39fe4c54d9469a2cbf4dd6b0264e6d440adbe75,
  Git blob 873db9535edc73e220517c848d69733cdd4d1feb. Preserved the complete upstream
  MIT notice in vendor/omarchy/LICENSE, identical to licenses/Omarchy-MIT.txt.
- Added vendor README and upstream/widget-candidates.json with canonical source,
  commit, hashes, review scope, empty dependency/modification lists and blocked
  unmodified UI decisions. Updated source metadata/README to disclose this first
  original-source import rather than retain the obsolete no-code-import claim.
- Omapager/component/brand/dataset/font notices remain gates for other imports.
  The main source identity and two unresolved supplemental helper origins are
  unchanged. No root MIT blanket clearance or publication permission inferred.

Contained mathematical checks:
- Added plan-only tools/check_clock_model.py; explicit --run accepts only this
  fixed hash-verified model/review scope and validates both complete MIT notices
  before any process. Verify existing build/stage source lock and artifacts.
- Evaluate only the pure original JS in an authored nonvisual ShellRoot/timer
  using existing Bubblewrap isolation: read-only inputs/runtime, private HOME,
  no real buses, host session, display/compositor, GPU or network; 20-second
  limits, no uncontained fallback. No original SystemClock/widget/calendar/IPC/
  native service or helper is constructed. Crash suppression is diagnostic-only.
- Final work/clock-model/20261024T101847.402782Z/report.json passes all five cases:
  221 assertions each in UTC, Berlin, Havana and Santiago under Qt 6.10.2 (884
  positive assertions), plus a deliberate wrong ISO-week negative control.
- Verify selected timezone offset, ISO/year/leap boundaries, format/seconds/ring
  behavior, week-start normalization, life/birth-year math and continuous civil
  date grids across historical midnight/DST transitions. Fixed dates only.
- Ordinary cases require exit 0, Configuration Loaded, one exact 221-assertion/
  timezone result and no WARN/ERROR/FATAL/CRITICAL. Negative control requires
  exact exit 42 and its specific deliberate assertion ERROR. Crashes/timeouts,
  wrong/duplicate/missing metrics or unrelated diagnostics cannot pass instead.
- Retained earlier audit/math runs unchanged. Final reports record tool/metadata/
  input/log hashes and unchanged probe inputs and stage. Source math success is
  not original widget, rendering, Color, compositor or security acceptance.
- Added 26 contracts in tests/test_widget_candidates.py; all 126 unit tests pass.
  Log: work/widget-candidate-tests.log. Unit tests themselves never execute JS/Qt.
- Final candidate Python/JSON syntax, whitespace and local Markdown links pass
  for all 52 files; ignored-report/public-vendor checks and git diff --check pass.
  Current tool/metadata/model hashes match final reports. Both reference manifests
  still verify: 2,286 regular files, 558 symlinks. No commits exist on main.
- docs/widget-candidates.md and linked provenance/testing/planning/status docs
  record the separation contract, source/license evidence and exact limitations.

Backup/rollback and boundaries:
- Only project files, a reviewed public-source import and ignored private reports
  changed. No active Ubuntu configuration or runtime installation changed; no
  active-path backup or desktop rollback needed. Reference and staged runtime
  remain unchanged. Revert/remove only this project's additions to discard them;
  prior package rollback still needs its own reviewed transaction.
- The shipped guard and empty catalog are unchanged. No original UI/plugin/helper
  execution, graphical trial, host service activation, real reload, auth/lock/
  idle/suspend test, logout/reboot/session switch, package/privileged command,
  commit, remote, upload or publication.
- Next: design passive tokens and an atomically injected original-widget API,
  verify the sealed QML closure in containment, and only then consider original
  QML admission. Graphical work still needs explicit affected paths/backups,
  compositor/service ownership, recovery/rollback and separate approval.

## Passive geometry API and sealed original spacer

Authorization: user requested continuation with the passive Style/host contract
and contained original-spacer checks. Only project files, reviewed pinned public
sources and fixed non-rendering diagnostics change. No window/session/desktop,
service, package, privileged or authentication action is included.

Implementation/source review:
- Added PassiveContract.js, PassiveBarApi.qml and PassiveStyle.qml under
  config/shell/. Exact bounded versioned geometry JSON, Boolean orientation,
  integer bar size 1-256 and spacer size 0-4096; no extra fields, command/URL/QML
  data or live provider. Accepted data is frozen; API geometry views readonly.
- snapshotJson is trusted constructor-owner input, not an opaque security boundary
  or approved live-update channel. Arbitrary QML remains trusted executable code.
- Reviewed complete original Ui/BarWidget.qml and Spacer.qml; base has geometry/
  settings/broadcast helpers but no startup/IO/service/IPC hook. Stock Style
  fallback is excluded rather than assumed inert. No extra per-file notices.
- Downloaded both files individually from pinned public commit
  03ff1eff3812933f7088484533784d2f63eaf19a with 64 KiB bounds; Git blobs and capture
  equality checked before import. Preserved bytes unchanged under vendor/omarchy/
  and retained both complete upstream MIT notices. No private config copied.
- Base: 2,297 bytes, SHA-256
  6dc5f08b92280e323b9bb8645ec530bca9c68512f3af49f6e3d5a13a6d9f99a3.
  Spacer: 293 bytes, SHA-256
  85abd1cd06755e57194b86d30df9c31e7521e5c91f5a663d9cd6420b9e91c545.
- Added upstream/spacer-candidate.json: per-file source/hash/license review,
  authored-file hashes, exact narrow module maps, geometry-only scope and limits.
  qs.Ui exports only the base; qs.Commons exports only our passive Style adapter.
  No original Commons module map, Style, Color, I18n, registry, other UI, helpers,
  fonts, data or assets staged. Diagnostic fallback 32 is not original-theme parity.
- Atomically supply validated API/settings in createObject's initial map before
  bindings. Refuse invalid input/API before leaf preparation. A tested rebind
  swaps directly between validated non-null APIs and retires the previous one.

Contained checks:
- Added plan-only tools/check_spacer.py; explicit --run verifies closed source/
  map sets, scope, upstream hashes/lengths/Git blobs, authored hashes and full
  notices before any process, then verifies existing build source lock/stage.
- Existing Bubblewrap boundaries: read-only sources/runtime, private HOME/PID/
  network namespaces, no host session/real buses/GPU/display/compositor/network;
  20-second limits, no less-isolated fallback, diagnostic-only crash suppression.
  Only original QQuickItem geometry is evaluated; no Window or rendering.
- Added a constructor marker only to the authored passive Style in private
  probes, never to upstream source. Valid atomic cases require zero hits.
- Final work/spacer-check/20261024T104040.369578Z/report.json passes 22 cases:
  horizontal/vertical/default/zero geometry, immutable view, atomic replacement,
  invalid input/API/schema/type/ranges/extra commands, plus explicit controls.
- Late-injection control omits bar, reads geometry, then injects it: exactly one
  fallback marker proves final correct dimensions alone would miss early Style
  activation. Only the passive adapter is available even in this unsafe control.
- Namespace control compiles a missing InputDevices reference and requires the
  expected missing-type error without constructing it. Assertion control requires
  exact exit 42 and its deliberate geometry ERROR, not crash/timeout/unrelated error.
- Ordinary cases require exact typed result metrics, one marker, exit 0,
  Configuration Loaded, no warnings/errors and zero fallback markers. Probe hashes
  and staged artifacts remain unchanged. Initial successful exploratory evidence
  at 20261024T103635.705379Z remains unchanged; final classifier also rejects
  Boolean/number substitutions. Reports retain commands, hashes and diagnostics.
- Clock-model regression also passes: current
  work/clock-model/20261024T104053.295969Z/report.json, 221 assertions per each of
  four timezones plus expected assertion control. Earlier reports not rewritten
  when adding new provenance; current metadata hashes recorded in the new report.
- Added 17 unit contracts in tests/test_spacer.py; all 143 unit tests pass.
  Log work/spacer-tests.log. Unit tests themselves never execute JS or Qt.
- Final Python/JSON syntax, whitespace and local Markdown links pass for all 61
  candidate files; ignore/public-source and git diff --check checks pass. Current
  source/profile/tool hashes match final reports; production gate files match
  prior evidence. Both reference manifests still verify: 2,286 files, 558 links.
- Added docs/passive-spacer.md and updated README/vendor/source metadata, test,
  research, plan, decision and capability docs to disclose this narrow adaptation
  and first original QML leaf construction without claiming stock shell parity.

Backup/rollback and boundaries:
- Production GuardedHost/LoadPolicy and empty catalog unchanged. Only candidate
  project files/public sources and ignored private reports changed. No active
  Ubuntu path changed, so no active-path backup or desktop rollback needed.
- Separate reference and staged runtime remain unchanged. Revert/remove only
  project additions to discard this profile; prior dependency rollback still
  requires its own reviewed transaction. No package/privileged command or custom
  runtime deployment, host service activation, real reload, auth/lock/idle/suspend,
  graphical session trial, logout/reboot/session switch, commit/remote/upload.
- This is an explicit incomplete compatibility namespace, not original Style,
  rendering, full clock/bar/shell, service or security acceptance. Next define the
  additional passive font/color/spacing/locale and restricted host contracts for
  an original label; do not admit its eager calendar, IPC or persistence by
  implication. Any graphical trial still needs separate scope/backups, service/
  compositor ownership, recovery/rollback and approval.

## Derived read-only clock and sealed bar-frame preview

Authorization: user asked to continue toward a first real start. This phase
prepares that start but does not connect to the host Wayland session.

Source review:
- Fetched original clock BarWidget.qml, WidgetButton.qml and OpticalGlyph.qml
  individually from pinned public commit 03ff1eff3812933f7088484533784d2f63eaf19a,
  bounded to 64 KiB, and matched Git blobs plus the local capture before import.
  Public vendor copies are unchanged. No private configuration was copied.
- Clock parent: 6,886 bytes, SHA-256
  28ac6687b356472c296ecac02724a95755f4e971c8b419abe1d58725a84248a5.
  WidgetButton: 6,739 bytes, SHA-256
  206e278477a25c990673fefb22e8f98d77128f430d345a98194ae0338a9fcae0.
  OpticalGlyph: 2,441 bytes, SHA-256
  b040c69c2323460fe8dcd7c91081c99b45925e0da5521e93df4be8443a751ad3.
- The original clock parent stays in vendor for provenance only. The fixed
  readonly-clock-v1 extraction removes calendar Loader, calendar forwarding,
  IPC, refresh/persistence and pointer actions before component preparation.
  Original formatted/ISO-week logic, SystemClock and button/glyph presentation
  remain. The staged button is not interactive.
- Added authored passive Style, Color and I18n singletons, an authored bar frame,
  TrialPolicy.js, and a default-deny TrialShell/TrialPanel. No original Commons,
  theme watcher, process, helper, font asset or command route is staged.
  Palette, 12px monospace and de-DE are diagnostic tokens.
- Trial policy accepts only schema 1, scope clock-bar-trial-v1 and an integer
  lifetime from 5 through 120 seconds. Missing or changed input stops before
  panel preparation. The panel is non-focusable, keyboard focus none, exclusive
  zone zero. Those settings are not a lock or input-isolation guarantee.

Contained checks:
- Added plan-only tools/check_clock_preview.py. Explicit --run verifies the
  closed profile, hashes, Git blobs, extraction and complete notices before any
  process, then reuses the existing Bubblewrap runtime. No host display socket,
  real buses, GPU, compositor or network, and no less-isolated fallback.
- Final work/clock-preview/20261024T110510.803898Z/report.json passes five cases:
  content formatting, private 960x32 software image with 347 painted clock-region
  pixels, strict policy acceptance/denial, denied trial entry, and assertion
  exit 42. Ordinary cases have zero warnings/errors and do not emit
  OMABUNTU_TRIAL_STARTED. Stage and probe inputs unchanged.
- An earlier failed content run at 20261024T110444.532890Z is retained. The
  authored Color singleton needed QtQuick so the color type resolved; no upstream
  file was patched.
- Added 13 unit contracts in tests/test_clock_preview.py. The suite now has 156
  tests. Unit tests do not start Qt or a host session.

Boundaries:
- Production guard and empty catalog unchanged. No active Ubuntu path, package,
  privilege, service, reload, authentication, lock/idle/suspend, graphical
  session, logout or publication. No active-path backup was required.
- A visible start still needs a separate approval naming the current Hyprland
  session, Wayland socket, stop command and recovery. The trial must not be
  placed in autostart and must not replace GNOME or existing services.

## First visible Hyprland clock bars

Authorization: the user started the existing uwsm Hyprland session and approved
one timed bar, then asked to continue and see the next result in that session.
No configuration edit, autostart, login change, service, or original shell was
authorized.

First run:
- Session wayland-1, Hyprland pid 280070, signature
  efb50993780079460b0cbed1363e2166a2de1d9f_1792840795_705578873.
- One process, evidence work/clock-trial/20261024T112901.315596Z.
- It logged OMABUNTU_TRIAL_STARTED and later OMABUNTU_TRIAL_STOP expired.
- Hyprland reported one omabuntu-clock-trial layer, 3440 by 32 pixels, at
  x=1280. The panel had no screen property, so the other outputs stayed empty.
- The user confirmed that the bar was visible and then gone. The process is no
  longer running.

Per-screen follow-up:
- TrialPanel now uses pinned Quickshell Variants with model Quickshell.screens
  and screen modelData. TrialShell hides every instance before destruction.
- Updated the authored hashes in upstream/clock-preview.json. Added one unit
  contract. The suite now has 157 tests and does not launch Qt.
- Second process, evidence work/clock-trial/20261024T114251.682735Z, lifetime
  120 seconds, external timeout 140 seconds. Same session and signature.
- Hyprland reported three layers from pid 290087: eDP-1 1280 by 32 at x=0,
  focused DP-7 3440 by 32 at x=1280, and DP-9 1920 by 32 at x=4720.
- eDP-1 is 1920 wide at x=0 while DP-7 begins at x=1280, so those outputs
  overlap in the current layout. The laptop layer is narrower than the panel.
  Layer evidence is not font, theme, or original-bar acceptance.

Boundaries:
- The existing Hyprland configuration remained dated 2026-10-22 00:21. No
  autostart, package, privilege, service, lock, idle, suspend, logout, commit,
  or publication. No active-path backup was required because no active path was
  edited. Stopping the trial process is the rollback.

## Live workspace strip and window title

Authorization: the user confirmed the per-screen bars and asked to continue with
faster visible UI results. This does not authorize the original shell, helpers,
services, autostart, or a configuration edit.

Changes:
- Added config/shell/preview/LiveStatus.qml. It reads the pinned Quickshell
  Hyprland singleton and draws workspaces 1-10 plus the active window title.
  A click sends only the workspace dispatcher. No hyprctl process, helper,
  window close, or file write.
- These are the existing global workspaces from the untouched Hyprland
  configuration, not Omarchy's per-monitor workspace blocks.
- Trial lifetime maximum is now 600 seconds. The bar still starts only with an
  explicit grant and still stops itself.
- Updated the closed preview hashes and the sealed policy probe bounds.

Visible run:
- work/clock-trial/20261024T115156.151937Z, pid 293481, same Hyprland session
  and signature, duration 600 seconds, external timeout 620 seconds.
- Three omabuntu-clock-trial layers again: 1280, 3440, and 1920 pixels wide.
- Log contains OMABUNTU_TRIAL_STARTED and Configuration Loaded, with no warning
  or error at startup. The existing Hyprland configuration stayed dated
  2026-10-22 00:21.

## Clickable Omarchy-like workspace strip

The user confirmed the workspace numbers and title, then reported that the
strip looked wrong and that clicks did nothing. Keyboard focus None was still
set, so the bar did not take pointer input. No Hyprland configuration edit was
authorized.

Changes:
- TrialPanel now uses WlrKeyboardFocus.OnDemand and WlrLayer.Top. OnDemand is
  not exclusive keyboard focus and not a lock. exclusiveZone stays 0.
- Bar height is 26 and the background is #101315, matching the Omarchy shell
  template. Workspace slots are 20px text buttons in JetBrainsMono Nerd Font,
  which is installed here. Slot 10 is labeled 0. Empty slots are dim, occupied
  and current slots are full opacity, and the current slot has a faint fill.
- The current slot is still a number. Omarchy replaces it with a layout glyph
  after its layout helper, and that helper is not run.
- A click still sends only the workspace dispatcher. No hyprctl, helper, window
  close, or file write.

Visible run:
- work/clock-trial/20261024T120516.219557Z, pid 298632, same Hyprland session
  and signature, duration 600 seconds, external timeout 620 seconds.
- Three layers, each 26px high: 1280, 3440, and 1920 pixels wide.
- Log contains OMABUNTU_TRIAL_STARTED and Configuration Loaded, with no warning
  or error at startup. The Hyprland configuration stayed dated 2026-10-22 00:21.

## Workspace clicks use the Lua focus call

The user reported that hover worked and clicks did not. The trial log shows the
clicks arrived. Hyprland rejected `dispatch workspace N` because this session
uses Lua: `hl.dispatch(workspace N)` is a syntax error. The existing
Super+number binding is `hl.dsp.focus({ workspace = i })`.

LiveStatus now sends that call when Hyprland.usingLua is true, and keeps
`workspace N` only for a non-Lua session. The workspace id is still limited to
1-10. No helper, window close, or configuration edit.

Replaced the previous trial process and started
work/clock-trial/20261024T121046.956482Z, pid 300692, same session and
signature, duration 600 seconds. Three 26px layers again. Startup log has
OMABUNTU_TRIAL_STARTED and Configuration Loaded. The Hyprland configuration
stayed dated 2026-10-22 00:21.

## Application list on Super+Alt+Space

The user asked for Super+Alt+Space to start programs. That is Omarchy's app
list, not the system menu. The original menu and dock stay unloaded because
their entries run helpers, including lock, suspend, install, and shutdown.

Added config/shell/preview/AppLauncher.qml. It lists installed Application
desktop entries that are not hidden, filters by name, and starts the selected
entry with DesktopEntry.execute(). That uses the parsed Exec command, not a
shell. Escape closes the card. The Apps label on the bar opens the same card.
A Hyprland global shortcut is registered as omabuntu:apps.

The running Lua session rejected hyprctl keyword. One session-only bind was
added with hyprctl eval: modmask 72 (Super+Alt) plus SPACE, dispatcher __lua.
The bind count went from 30 to 31. ~/.config/hypr/hyprland.lua stayed dated
2026-10-22 00:21, so the key does not survive a Hyprland restart.

Visible run: work/clock-trial/20261024T122355.752767Z, pid 305776. Startup
logged OMABUNTU_TRIAL_STARTED and Configuration Loaded. hyprctl globalshortcuts
lists omabuntu:apps. The process keeps the normal home and PATH so a started
program is the user's program. It expires after 600 seconds. No package,
service, autostart, lock, idle, suspend, commit, or publication.

## Hour-long bar restart

The 600-second application-list trial stopped itself. Its log ends with
OMABUNTU_TRIAL_STOP expired, and hyprctl globalshortcuts then reported none.
Super+Alt+Space remained bound in the running session, so the key had no
client left to open. The user confirmed that the bar was gone and the key did
nothing.

Raised the explicit trial maximum from 600 to 3600 seconds. The grant is still
required, still self-stopping, and still not autostart. The policy probe now
rejects 3601 and accepts 3600. All 157 unit tests passed.

Restarted one Quickshell process for 3600 seconds with an external 3620-second
limit: work/clock-trial/20261024T124829.477445Z, pid 314568. Startup logged
OMABUNTU_TRIAL_STARTED and Configuration Loaded. Three clock-trial layers are
present. hyprctl globalshortcuts lists omabuntu:apps. The previous session bind
was replaced once, leaving exactly one Super+Alt+Space binding (modmask 72,
SPACE, dispatcher __lua). ~/.config/hypr/hyprland.lua stayed dated
2026-10-22 00:21. No package, service, autostart, lock, idle, suspend, commit,
or publication.

## Application grid follows the Omarchy card

The user rejected the narrow text list. The original dock AppGrid is a large
centered card: a search line, 56px icons, at most seven columns, and four
visible rows. That file also drags apps onto the dock, opens a context menu,
and uninstalls applications, so it stays unloaded.

config/shell/preview/AppLauncher.qml now uses those same measurements, the
menu colors #101315 and #cacccc, an 8px corner, and the German placeholder
"Apps suchen…". Icons come from DesktopEntries through Quickshell.iconPath.
A missing icon shows the first letter. Enter or a click still starts only
DesktopEntry.execute(). There is no uninstall, drag, helper, or system action.

Replaced the running trial with work/clock-trial/20261024T130633.273749Z,
pid 322926, grant 3600 seconds. Startup logged OMABUNTU_TRIAL_STARTED and
Configuration Loaded. Three 26px clock-trial layers are present.
hyprctl globalshortcuts lists omabuntu:apps. Exactly one Super+Alt+Space bind
remains (modmask 72, SPACE, dispatcher __lua). ~/.config/hypr/hyprland.lua
stayed dated 2026-10-22 00:21. No package, service, autostart, lock, idle,
suspend, commit, or publication.

## Bar reserves its height

Tiled windows started at the top of each output and continued under the 26px
bar, so their title area was covered. The trial had set an exclusive zone of
zero. The original Omarchy bar uses ExclusionMode.Auto while it is visible,
which reserves the bar's implicit height on the top edge.

config/shell/preview/TrialPanel.qml now uses ExclusionMode.Auto. The
application overlay still uses an exclusive zone of zero, so opening the grid
does not permanently shrink the workspace. All 157 unit tests passed.

Replaced the running trial with work/clock-trial/20261024T131041.186886Z,
pid 324926, grant 3600 seconds. Startup logged OMABUNTU_TRIAL_STARTED and
Configuration Loaded. hyprctl reports reserved [0, 26, 0, 0] on eDP-1, DP-7,
and DP-9. Tiled windows on DP-7 and DP-9 start at y=38, below the bar plus the
existing outer gap. Super+Alt+Space was bound again for this process only.
~/.config/hypr/hyprland.lua stayed dated 2026-10-22 00:21. No package,
service, autostart, lock, idle, suspend, commit, or publication.

## Original tray port, not a completed bar

Authorization: implement the complete bar. This work begins that larger request
with the unchanged original tray, not a newly drawn replacement. Remaining
bar/panel/backend work is tracked in docs/bar-port.md and is explicitly incomplete.

Imported eleven reviewed files individually from the pinned public Omarchy
commit, checked against the Git tree and reference bytes. Complete original
Tray.qml/TrayModel.js and PopupCard/Button/border/icon dependencies are staged
unchanged. Full MIT notice remains intact; exact per-file provenance is in
upstream/clock-preview.json. Original watched Style/Color/I18n and full shell
startup stay excluded. PortTrayHost supplies passive tokens, popup ownership,
tooltips and session-local pin/hide preferences; no command runner or file writer.

162 Python contracts pass (work/tray-port-unit-tests.log). Five isolated actual
Qt tray fixtures pass at work/tray-port/20261024T133110.194624Z/report.json;
these use a synthetic service, not host DBus. All five sealed clock checks also
pass at work/clock-preview/20261024T133115.008353Z/report.json. Stage unchanged
in both reports; no warning suppression. Earlier tray fixture pass retained.

Replaced only the verified trial process 324926. Its staged inputs remain
unchanged as rollback evidence. Current run:
work/clock-trial/20261024T133145.096302Z, pid 334744, 3600-second grant with an
external 3620-second bound. Three 26px layers and reserved [0, 26, 0, 0] on all
outputs. The application shortcut remains registered; no keybind was changed.
The native StatusNotifier host and watcher are owned by this process. Four
items are registered, including the active warp-taskbar item. Interactive menus
and visual fidelity still need user acceptance. The host-portal warning about
unregistered app ID org.quickshell remains visible and unresolved.

No active configuration file changed; Hyprland Lua retains its October 22
mtime. No package/plugin installation, reload, network/VPN mutation, service-unit
activation, login/autostart edit, lock/idle/suspend, commit or publication.
Stopping this verified TrialShell process removes the tray host and trial
surfaces, not the running applications. Pin/hide preferences are intentionally
not persistent yet. Complete original bar, network panel and workspace-mode
backend are not claimed complete.

## Passive native network status

Authorization: continue the bar port. Added a restricted status slice, not
network configuration controls. The original network Model.js was fetched from
the pinned public commit, matched to the Git tree and reference bytes, reviewed
and imported unchanged with MIT notice/provenance preserved. Dormant command
strings and the captive-portal URL in that model are never used by this view.
Original BarIconButton and PopupCard provide the presentation primitives;
NetworkStatusView is an explicitly authored status composition, not the complete
original 2151-line network configuration panel.

NetworkStatusProvider subscribes to native NetworkManager-backed properties.
NetworkPresentation copies primitive interface/link/signal/cached-connectivity
fields, prefers wired as Omarchy does, ignores stale devices when unavailable,
and does not retain WifiNetwork QObject wrappers in delegates. Plain-text
labels prevent network names from becoming rich text. No scanner activation,
connectivity probe, connection/forget/disconnect, radio toggle, credential,
DNS/band/route/VPN edit, helper execution, or native nmSettings access is exposed.
Reviewed pinned native backend initialization and scan gating; no GetSecrets
or secret-agent registration route is present in the inspected network backend.

169 Python contracts pass (work/network-port-unit-tests.log). Seven isolated
actual Qt network fixtures pass, using synthetic inputs and a synthetic tray,
not live Networking/DBus. Final reports:
- work/network-port/20261024T134509.609787Z/report.json
- work/tray-port/20261024T134516.414052Z/report.json (five tray regressions)
- work/clock-preview/20261024T134520.994782Z/report.json (five clock regressions)
All report unchanged runtime artifacts. Earlier successful reports remain.

First live staging at work/clock-trial/20261024T134324.313080Z was replaced after
strengthening the unavailable-backend/stale-device guard. Final live run:
work/clock-trial/20261024T134549.341765Z, pid 340301, duration 3600 seconds with
external 3620-second bound. Three 26px layers, reserved [0, 26, 0, 0] on all
outputs, original app shortcut still registered, configerrors empty. Startup
logs Configuration Loaded and OMABUNTU_TRIAL_STARTED; the known host-portal
warning remains. Live network popup content/click behavior needs user acceptance.

Only verified trial processes were stopped; previous staged sources are
unchanged for rollback. Stopping the current verified TrialShell removes the
surfaces/subscriptions, not NetworkManager or applications. Hyprland Lua mtime
remains 2026-10-22 00:21:42.360825474 +0200. No active config edit, reload,
package/plugin installation, service-unit activation, login/autostart change,
lock/idle/suspend, commit or publication. Network configuration, other panels
and workspace modes remain incomplete; see docs/network-status-port.md.

## Session lifetime instead of repeated timed trials

The user approved removing automatic shutdown and requested permanent operation
for normal desktop work from now on. This approval followed an explicit offer
without autostart or active Hyprland config edits; it is not expanded into login
persistence or service deployment. Recorded the preference in AGENTS.md.

TrialPolicy accepts a separate exact bar-session-v1 / lifetime=session grant.
TrialShell never starts the expiry timer for that mode. Missing/changed grants
still revoke the instance; timed scopes remain limited to explicit diagnostics.
Added tools/bar_session.py start/status/stop: verified source/stage, private
staging, detached direct launch without timeout, duplicate prevention, and
targeted PID/UID/start-time/exact-command checks before status or stop. No
automatic crash restart and no session-wide kill or reload.

175 unit tests pass (work/bar-session-tests.log), including six new lifecycle
contracts. The actual isolated clock/policy suite passes at
work/clock-preview/20261024T152431.186764Z/report.json, stage unchanged. It
checks the new explicit grant and rejection of ambiguous/mixed lifetime data.

There was no Quickshell left running before start. Current non-expiring run:
work/bar-session/20261024T152434.147770Z, PID 375385. Native log confirms
OMABUNTU_BAR_SESSION_NO_EXPIRY and Configuration Loaded. Three 26px layers,
app shortcut registered, configerrors empty. A repeated start reported the same
PID without creating another instance. Known portal app-ID warning persists.

No active configuration path changed; hyprland.lua remains dated October 22.
Prior staged trial files remain intact. Rollback/normal bar-only stop:
python3 tools/bar_session.py stop. This does not stop Hyprland or applications.
No autostart, user-service enablement, package/plugin installation, network/VPN
mutation, lock/idle/suspend, login/session switch, commit or publication.
Session lifetime is not reboot/login persistence; see docs/bar-session.md for
the remaining separate deployment gate and exact start/status/stop commands.

## Audio output controls without expiry

Authorization: continue with audio after the user confirmed network remains
status-only. Imported the reviewed unchanged original audio Model.js and
PanelSlider.qml from the pinned public Omarchy commit, verified against the
Git tree and reference bytes. MIT notice/provenance retained. The original
full audio Panel.qml and its helper/OSD/media-service startup stay excluded.

AudioOutputView composes original BarIconButton, PanelSlider, Button and
PopupCard. Left click opens output controls, right click toggles output mute,
wheel adjusts by 5 percent per notch, and the output list requests a preferred
sink through native PipeWire. No microphone/master-mute action, capture/peak
monitor, sound test, external helper, daemon restart or startup mutation.
Graph presence is not jack availability; the original physical-sink resolver
and profile/stream/media functionality remain unported. This is output-only,
not full original audio-panel acceptance.

AudioActions resolves fresh ID+name, requires a ready non-stream audio sink,
rejects invalid numeric data and clamps requested volume to 0..1. Snapshot
rows contain primitives only. Dragging retains its starting target; device
changes reset accumulated wheel deltas. The native provider is read-only
until explicit user actions call its mutation methods.

182 unit contracts pass (work/audio-port-unit-tests.log). Actual isolated
fixtures use fake graph/backend data, never native PipeWire or test playback.
Final reports, all stage-unchanged:
- work/audio-port/20261024T154336.665285Z/report.json (seven fixtures)
- work/network-port/20261024T154343.471480Z/report.json (seven regressions)
- work/tray-port/20261024T154350.313790Z/report.json (five regressions)
- work/clock-preview/20261024T154355.084166Z/report.json (five regressions)
Exploratory successful audio fixture report retained.

Read-only default output/volume baseline and comparison saved under
work/audio-port/baseline-20261024T154411.087954Z/. Both wpctl get-volume and
inspect outputs were identical before/after launch. No audio value was changed
by the assistant. New session-long run:
work/bar-session/20261024T154411.383363Z, PID 382680. No-expiry marker and
Configuration Loaded, three 26px surfaces, app shortcut registered and
configerrors empty. The known portal app-ID warning remains. Live slider,
audio routing and pointer behavior need user acceptance.

Only the verified bar process was replaced using bar_session.py stop/start;
previous staged inputs remain intact. Bar-only stop removes the UI, not
PipeWire/applications or intentional user audio choices. No active config file
edit/reload, package/plugin installation, autostart/service-unit enablement,
network/VPN mutation, lock/idle/suspend, login/session switch, commit or
publication. Hyprland Lua remains dated October 22. See docs/audio-output-port.md
for controls, test boundaries and rollback.

## Fidelity correction: original audio output frontend

User feedback: continue, but the current elements are below Omarchy quality.
Acknowledged that authored partial panels assembled from original primitives
are not equivalent to original components. Recorded this requirement in
AGENTS.md and docs/bar-port.md. Do not add more unrelated replacement panels
instead of correcting the original layout, shared chrome and interaction.

Fetched/reviewed eight additional pinned public MIT files, matching Git tree
blobs and reference bytes before import: audio/Panel.qml and KeyboardPanel,
PanelKeyCatcher, CursorSurface, ToggleSwitch, PanelToolTip, PanelSeparator,
PanelSectionHeader. Vendor parents remain unchanged; full notices, origins,
exact hashes and staging transforms are enforced in clock-preview.json.

Replaced the independently composed output view with a deterministic source
extraction. Original hero markup is byte-identical; output geometry adds only
a drag-target identity guard, and original SinkRow adds a name check. Original
switch, header typography, mood label, cursor surfaces, lazy keyboard-panel
content, scroll layout and input signal handling are retained. The authored
AudioPanelController supplies the output-only backend/interaction boundary;
no live native node wrappers reach delegates. The generated view mirror must
match its upstream extraction exactly; it is not another editable layout.

KeyboardPanel staging never acquires Exclusive focus, unmaps on logical close,
and routes hit testing through the restricted owner. The original remaining
prime timer gates bar forwarding, not focus. Original multi-output dismissal
surfaces remain; pointer/focus/rapid reopening still require live acceptance.
Native input, microphone capture, streams, helpers, IPC and OSD remain excluded,
not merely hidden. Tab stays within the output panel, not a shell registry.

Corrected passive upstream-default tokens: popup padding 14, control gap 8,
control height 28, row padding 10, title/display 14/24, normal fill .04 and
selected fill .18. This is not integration of the complete original theme or
bar frame; network is still the restricted authored status view. Added owner
click-target registration and clipping-aware hit testing for original panel
bar-click forwarding. No broader helper singleton was loaded.

The initial new audio fixture failed because native PanelWindow has no
offscreen backend. Retained work/audio-port/20261024T160720.961487Z/report.json.
Only fixture surface ownership is now synthetic; original content and controls
execute, including lazy construction. Production keeps native derived surfaces.
Earlier unit failures are retained in work/audio-fidelity-unit-tests.log;
updated fixture copies to include the generated mirror and explicit transform
expectations, without weakening source/symlink guards.

191 Python contracts pass, including exact original hero/output/row markup,
fail-closed splice witnesses, generated mirror, and no Exclusive executable
focus code. Eight actual Qt audio fixtures now include original lazy content
and cursor/keyboard-signal navigation. No native sound or audio bus in fixtures.
Final reports, all runtime artifacts unchanged:
- work/audio-port/20261024T161209.038468Z/report.json
- work/network-port/20261024T161216.270570Z/report.json
- work/tray-port/20261024T161222.463033Z/report.json
- work/clock-preview/20261024T161226.655311Z/report.json
- work/audio-fidelity-unit-tests-final.log
Source relationships and fake-surface tests do not prove pixel/theme parity
or actual compositor/pointer behavior.

Replaced only the verified bar process through stop/start, under the continued
request and no-expiry preference. New run:
work/bar-session/20261024T161308.276025Z, PID 393392. No-expiry marker,
Configuration Loaded, three 26px surfaces and empty configerrors observed.
Known portal app-ID warning persists; no additional startup warning observed.
Private read-only baseline in work/research/audio-fidelity/baseline/ confirms
default output inspect/get-volume outputs identical before/after launch.
No assistant audio changes or sound tests. Prior staged UI retained at
work/bar-session/20261024T154411.383363Z; no installed active path edited.

Bar-only rollback/stop remains tools/bar_session.py stop; it does not stop
Hyprland, applications or PipeWire, nor undo intentional user audio choices.
No Hyprland file edit/reload (October 22 mtime retained), package/service-unit
change, autostart, VPN mutation, lock/idle/suspend, session switch, commit or
publication. The entire shell is still incomplete and below full original
acceptance. Next fidelity priorities are the shared frame/theme and proper
original network frontend, not additional simplified icons/panels.

## Prepared bar tooltip clipping correction (not activated)

User reports hover rendered only partly visible. No screenshot/native pointer
reproduction collected; do not claim every artifact is proven to be a tooltip.
Found a concrete authored-owner defect: a bare Controls ToolTip ignores the
hovered item, is forced visible for empty text and has no original independent
popup anchor. This can explain an incorrectly positioned/clipped hover inside
the 26px bar surface.

Individually fetched and reviewed public pinned Bar.qml (104979 bytes), matched
against the pinned tree and reference. Vendor parent unchanged, full MIT notice
preserved. Extended the bounded read to 128KiB only for that exact source parent.
Deterministic exact-hash extractions stage the original tooltip lifecycle and
PopupWindow, not bar startup, helpers, watched files or probes. New closed
profile has 51 staged source files.

PortTrayHost delegates to BarTooltipHost/BarTooltip rather than a Controls
ToolTip. Original empty-text/hover validation, 400ms delay, request-generation
checks, stale-exit ownership, target deletion/visibility checks, target-window
anchor, 6px placement, edge slide, border and plain-text rendering are retained.
No keyboard-focus-grab or input automation added. See tools/tooltip_port.py,
upstream/clock-preview.json and docs/tooltip-port.md.

198 Python contracts pass (work/tooltip-port-unit-tests-final.log). Seven actual
isolated Qt cases cover empty, delayed, stale-hide, leave, deleted target,
original bubble geometry and exact negative exit 42. Native popup positioning
is not tested by offscreen: its geometry fixture executes only the original
bubble. Failed exploratory reports remain: offscreen FloatingWindow mask
warning, unavailable native popup dimensions, and an incorrect expectation
that tooltip height must exceed bar height (actual bubble 133x26). No warnings
were filtered; fixed the fixture hosting and measurement assumptions.

Final tooltip report:
work/tooltip-port/20261024T163333.302552Z/report.json (seven passed, stage unchanged).
Other regressions on the same source profile, all passed/stage unchanged:
- work/audio-port/20261024T163016.972307Z/report.json
- work/network-port/20261024T163024.749275Z/report.json
- work/tray-port/20261024T163031.137664Z/report.json
- work/clock-preview/20261024T163035.767813Z/report.json
Prior successful tooltip report 20261024T163008.821731Z also retained.

Activation is pending approval for bar-only stop/start. Current PID 393392 and
sealed stage work/bar-session/20261024T161308.276025Z remain running without
expiry, unchanged; this retained stage is the prior-state backup. No active
config edit, reload, service/network/audio mutation, package change, pointer
injection, logout/session switch, autostart, commit or publication. Native
hover, edge placement and rapid switching still need post-activation acceptance.

## Tooltip activation and continued original section layout

User explicitly approved tooltip activation and requested continued work.
Replaced only the verified bar process using bar_session.py stop/start.
Tooltip-only run: work/bar-session/20261024T165402.318224Z, PID 409597.
No-expiry/Configuration Loaded and three 26px surfaces observed; no new startup
warning beyond the known portal app-ID warning. No pointer automation or claim
of visible hover acceptance.

Continued with the shared layout rather than more unrelated replacement panels.
Original reviewed Bar.qml supplies horizontal edge anchors, CenterSections and
CenterBox geometry through tools/bar_frame.py and fixed-horizontal-sections-v1.
Closed source/derived hashes enforced; vendor parent unchanged. Full bar startup,
WidgetPool/registry, dynamic URLs, gestures/drag/ghosts/outlines, notch calibration,
vertical bars, watched theme IO and helper paths remain excluded. Fixed trusted
Component slots replace module discovery; this is not the whole original frame.

TrialPanel now loads real left/center/right sections instead of overlaying
PreviewContent and a full-width LiveStatus. Clock uses its existing read-only
derivation directly at 26px; the sealed PreviewContent fixture remains unchanged.
LiveStatus becomes a content-sized row, removing absolute Apps/title x offsets
224/268 and the half-screen subtraction. Plain-text title is capped at the
original 280px label budget and fitted to the center boundary. Workspace/App
widgets remain authored global adapters; no monitor blocks, layout switching,
window-close action or shell menu were silently introduced.

Original 8px outer insets and center/begin/end formulas are retained. Additional
side clipping keeps 8px separation from the complete center group at narrow
widths. This is an explicit responsive adaptation, not unchanged upstream policy.
Tooltip/panel windows remain independent native surfaces, not clipped-in-bar
Controls ToolTips. Existing app grid, tray, status-network and audio remain.

206 Python contracts pass (work/bar-frame-unit-tests.log). Seven actual Qt frame
fixtures instantiate source-derived geometry and the real left adapter, replacing
only fixture Hyprland with synthetic primitives and a startup-dispatch tripwire.
Widths 1280/3440/1920/320, long literal-markup title, center side sections and
exact assertion-control exit 42 pass. No native desktop dispatch or pointer used.
Final reports all passed with runtime artifacts unchanged:
- work/frame-port/20261024T170522.474405Z/report.json
- work/tooltip-port/20261024T170529.441160Z/report.json
- work/audio-port/20261024T170537.590297Z/report.json
- work/network-port/20261024T170545.420617Z/report.json
- work/tray-port/20261024T170552.123831Z/report.json
- work/clock-preview/20261024T170556.755465Z/report.json
The source profile now verifies 52 staged files. Tests do not prove original
pixel/theme parity or native hover/pointer acceptance.

Applied this continued normal bar layout step through targeted stop/start;
prior tooltip-only sealed stage remains the backup/prior state. Current run:
work/bar-session/20261024T170636.340422Z, PID 414781. No-expiry and Configuration
Loaded observed; three 26px surfaces, reserved [0,26,0,0] on every output,
application shortcut registered and configerrors empty. Only the known portal
app-ID warning observed at startup. Active Hyprland Lua retains October 22 mtime.

No active config edit/reload, logout, audio/network setting mutation, service-unit
change, package install, auth/lock/idle/suspend change, autostart, commit or
publication. Source backups are the retained sealed stages; no installed file
was edited. Stop only through bar_session.py stop, never uwsm stop. Normal bar
lifetime remains session-long, not reboot persistence. Actual hover/visual and
shared hit-testing acceptance remains open; see docs/bar-frame.md and the
updated tooltip/bar completion documents.

## App launcher first opening stays empty until reopening: root-cause fix

User reports first Super+Alt+Space opening empty, second populated. Verified
pinned runtime source: DesktopEntryManager constructor runs the scanner, but
DesktopEntryScanner::run queues onScanCompleted through Qt::QueuedConnection;
that callback publishes applications and emits applicationsChanged, forwarded
by DesktopEntries. Our authored launcher copied values once in open()/filter
changes and had no subscription to the later publication. Native geometry was
not assumed to be the cause.

Added a real isolated UI regression before implementation. Original source
failed work/apps-port/20261024T171425.913098Z/report.json with exact exit 42 and
"first opening refreshes after publication". It opens once with an empty fake
catalog, publishes later, and checks the same visible GridView/delegate without
reopening. No host apps, shortcut or pointer used.

Minimal production change: Connections targeting DesktopEntries with
onApplicationsChanged rebuilding only while shown. This initializes the
singleton during construction and refreshes an already-open panel when data
arrives. Hidden updates do not summon the UI, and typed filters remain intact.
No polling, artificial wait, timer, second-open workaround, style or launch
semantics change. Updated the exact authored source hash; profile still has
52 staged source files.

Seven actual Qt green cases now cover cold/filtered-cold/warm/closed-update,
removal, native-cold and intentional negative exit 42. Native-cold uses real
DesktopEntries with two generated private .desktop files and isolated
XDG_DATA_DIRS; no host application inventory or launch. Fixture copies replace
only native surface/screen/shortcut ownership, not model/filter/grid code.
Green report: work/apps-port/20261024T171814.962430Z/report.json, runtime stage
unchanged. Earlier six-case passes retained. Actual first GridView delegate,
sorted/filtered text and usable first-open geometry are asserted.

212 unit contracts pass (work/app-launcher-unit-tests-final.log). Clock/lifetime
regression passed: work/clock-preview/20261024T171608.229347Z/report.json.
Native hotkey/focus acceptance is still needed; no key was injected. Existing
btop.svg pattern warnings from the old live opening are not hidden and were
not the cause of the missing model update.

Within the ongoing approved bar work, replaced only the verified bar process.
Prior source stage work/bar-session/20261024T170636.340422Z retained as backup.
Current run work/bar-session/20261024T171842.505322Z, PID 420968: no-expiry and
Configuration Loaded observed, three 26px surfaces, shortcut registered and
configerrors empty. Only the known portal app-ID startup warning observed.
No active config edit/reload (October 22 Lua mtime retained), session switch,
package, service/autostart, network/audio mutation, app execution, commit or
publication. Bar-only stop remains bar_session.py stop, never uwsm stop.
See docs/app-launcher.md for source evidence, fixture boundaries and recovery.

## Network panel performs Wi-Fi connection actions

User asked for the network button to work, not only display status. Reviewed
the pinned Quickshell NetworkManager API and the original 2151-line network
panel. Staged the original icon, hero, station list and network row through
tools/network_frontend.py. The controller calls connect, connectWithPsk,
disconnect, forget, wifiEnabled and the open-only station scanner. Passphrases
are cleared from the QML property after the call and are not logged.

Excluded and not merely hidden: DNS changes, band pinning, QR sharing, speed
test, captive-portal launch, omarchy helpers, nmcli, nmSettings reads, and
creation of a new 802.1X profile. An unsaved enterprise row is refused. A
profile NetworkManager already stored can be activated by an explicit row
action. Ethernet is shown from the device address and is not reconfigured.
VPN, routes, firewall and certificates are untouched. The 30-second timer only
clears a stuck action; it does not expire the bar. The older status popup
remains a regression fixture and is no longer on the bar.

Imported unchanged PanelActionButton.qml and Ui/TextField.qml after the cached
Git tree blob matched the reference bytes. TextField was required because the
original passphrase field is not the plain Controls field. Removed two
height:implicitHeight bindings that Qt 6.10 warns as binding loops; visibility
already collapses those labels. Added the original passphrase field tokens
needed by that component.

Seven isolated Wi-Fi cases pass at
work/wifi-port/20261024T180104.691679Z/report.json. Retained earlier failures:
enum properties cannot start with uppercase, and the null-parent scanner timer
did not run until the fixture used a Qt Window. Clock regression
work/clock-preview/20261024T180136.240381Z/report.json and status regression
work/network-port/20261024T180139.932402Z/report.json pass. 216 unit tests pass
in work/network-control-unit-tests-final.log. No host NetworkManager write was
performed by the tests.

See docs/network-control.md. Replaced only the verified bar process after these
checks. Current run work/bar-session/20261024T180312.260458Z, PID 443059:
no-expiry and Configuration Loaded observed, three omabuntu-clock-trial layers,
configerrors empty. Only the known portal app-ID warning appeared. The October
22 Hyprland file mtime is unchanged. No package, service, VPN, logout, commit
or publication. Bar-only stop remains bar_session.py stop, never uwsm stop.

## Panel labels use the English catalog

User asked why panel text was German and then asked for English. The passive
I18n adapter had a fixed German table and did not read the system locale or the
Omarchy catalog. Replaced the staged tray, audio and network strings with the
English values from the pinned shell catalog. The app-launcher placeholder is
the original dock.searchApps text, "Search apps…". Authored audio errors are
now "Output device is no longer available" and "No audio output available".
The enterprise refusal remains an authored English sentence because that key is
not in the catalog. network.connectedPhrase stays the static word Connected;
the original seven rotating hero phrases are still not staged. The bar clock
weekday stays de-DE because formatLocale is only the clock formatter, not a
panel label. No catalog file or locale watcher was loaded.

216 unit tests pass in work/english-labels-unit-tests.log. Clock regression
work/clock-preview/20261024T183751.383279Z/report.json passes and still expects
the German weekday. Replaced only the verified bar process. Current run
work/bar-session/20261024T183801.801147Z, PID 457172. The October 22 Hyprland
file mtime is unchanged. No package, service, network, audio, VPN, logout,
commit or publication.



## Workspace layout glyphs and English clock

User asked for Omarchy's tiling/scrolling/floating workspace symbols, using the
GitHub sources, and for the bar weekday to be English.

The running bar still had formatLocale de-DE, which is why it showed Samstag.
config/shell/preview/I18n.qml was already en-US, Omarchy's English clock locale,
but its review pin was stale, so the live probe had not been replaced.

Vendored unchanged Workspaces.qml and the layout toggle script from Omarchy
commit 03ff1eff3812933f7088484533784d2f63eaf19a. The toggle script is reference
only and is not staged or executed. The derived switcher keeps modeGlyph and
the active-slot cycle. Dwindle and scrolling go through Hyprland's own
hl.workspace_rule. Floating tags only tiled, unpinned, non-fullscreen windows
as omabuntu-mode-floated and floats those; leaving the mode tiles only that
tag. Per-monitor blocks, Omarchy helpers, notifications, the title-bar plugin
and hyprctl reload stay out. See docs/workspace-modes.md.

A read-only-intent eval of the dwindle program for workspace 3 returned ok.
All three workspaces still report tiledLayout dwindle. Hyprland now has one
runtime workspace rule for workspace 3; it is not in hyprland.lua and lasts
only until reload. hyprland.lua mtime remains 2026-10-22.

219 unit tests passed. Replaced only the bar process. Previous run
work/bar-session/20261024T183801.801147Z. Current run
work/bar-session/20261024T220128.093084Z, PID 536453. Configuration Loaded,
no-expiry, empty configerrors, and the known portal app-ID warning. The staged
clock locale is en-US. No package, service, network, audio, VPN, logout,
commit or publication.

## Workspace switcher accepts one press

The active symbol needed several clicks. A press while hyprctl was still
running was discarded, and the symbol was then set back from Hyprland's
previous tiled layout, so the press looked like it had done nothing.

A press now changes the symbol immediately and sends that layout once.
Presses that arrive during the call are kept as the latest layout. The
symbol is no longer overwritten by the stale tiled-layout read. 219 tests
passed. Replaced only the bar process. Previous run
work/bar-session/20261024T220128.093084Z. Current run
work/bar-session/20261024T221902.608603Z, PID 543867. No package, service,
network, audio, VPN, logout, Hyprland reload, commit or publication.

## Floating windows use Omarchy's centered size

Switching a workspace to floating left tiled windows at their tiled size.
The switch now places each window it floats the way Omarchy's place() does:
at most 1100 by 760 pixels, 64 percent of the usable width and 68 percent of
the usable height, centered, then stepped by 24 pixels. Windows that were
already floating, fullscreen, or pinned are left alone. The title-bar plugin
is not loaded and Hyprland is not reloaded. 219 tests passed. Replaced only
the bar process. Previous run work/bar-session/20261024T221902.608603Z.
Current run work/bar-session/20261024T225637.120441Z, PID 559788. No package,
service, network, audio, VPN, logout, Hyprland reload, commit, or publication.

## Bar compared with Omarchy; workspace row is 1-6

The live bar shows workspaces, an authored Apps control, the window title,
the clock, the original tray, the derived network control, and the audio
output control. Omarchy's default bar also has the menu, indicators,
Elsewhen, weather, system update, keyboard layout, agents, Bluetooth,
monitor, and power. Network is the original connection surface on
Quickshell's NetworkManager backend, not the full original panel.

The workspace row now shows global workspaces 1-6. Omarchy shows ten per
monitor and labels the tenth 0. Hyprland's config file was not changed.
219 tests passed. Replaced only the bar process. Previous run
work/bar-session/20261024T225637.120441Z. Current run
work/bar-session/20261024T233435.794955Z, PID 579018. No package, service,
network, audio, VPN, logout, Hyprland reload, commit, or publication.

## Network panel gains the seven excluded actions

The network panel now includes Omarchy's captive-portal prompt, Wi-Fi band row
and DNS row. Saved Ethernet and VPN profiles are listed too; Omarchy's network
panel does not have those lists. QR and the speed test open inside this panel.

Actions go through tools/network_nm.py and NetworkManager. DNS is changed only
on the active connection and put back if reapply fails. A band pin reconnects
that Wi-Fi profile and restores the previous band if it does not return. The
portal button opens Ubuntu's connectivity check. The QR matrix is drawn without
printing the passphrase. The speed test is one download and one upload, eight
seconds each. Ethernet and VPN buttons only connect or disconnect an existing
profile. No Omarchy helper, sudo, certificate, firewall, proxy, Tailscale or
NordVPN path was added.

227 tests passed. The isolated Wi-Fi fixtures passed. Replaced only the bar
process. Previous run work/bar-session/20261024T233435.794955Z. Current run
work/bar-session/20261025T002808.710091Z, PID 602033. No package, service,
audio, logout, Hyprland reload, commit, or publication.

## Original Bluetooth, Display, Power and floating dock in the trial

Implemented the user's explicit four-surface request rather than stopping at
source review. Pinned original panel/model and dock-window/model files were
fetched byte-identically from the approved MIT source and registered in the
closed preview profile. `tools/desktop_frontends.py` derives the original
surfaces and Bluetooth cursor/grouping logic with witnessed splices. Ubuntu
controllers provide BlueZ actions, logind brightness, validated runtime monitor
scaling, UPower and native power-profiles-daemon profile selection. The original
dock uses installed desktop entries and native Wayland window actions; its
visibility is granted only after this trial's floating switch succeeds.
Shared discovery leases protect scans across multiple trial bars. No scan,
profile or display mutation is triggered by startup. Output disabling, global
font-size changes, session controls, original helper execution, persistent dock
preferences and app-grid drag handoff remain excluded; see
`docs/desktop-panels.md` for the complete deviation/acceptance record.

Verification: 241 Python tests pass (`work/desktop-unit-tests.log`). Original
panel construction, mock BlueZ/profile actions, shared discovery leases, dock
construction and floating-grant revocation pass in the isolated Qt fixture:
`work/desktop-panels/20261025T074553.406587Z/report.json`. Native type compilation
passes in `work/desktop-native-compile/20261025T074554.941945Z/output.log`.
Read-only Ubuntu display status reports three outputs and an available backlight;
no brightness or scale was changed to test it.

The first live startup exposed missing passive dock color tokens and a dock
order binding cycle that compilation alone had not detected. Added the tokens,
deferred order adoption, and strengthened the isolated check to construct the
dock and reject binding errors. Removed one redundant original Bluetooth header
height binding that loops under Qt 6.10 (Column already omits invisible rows).
After rechecking seals/tests/fixtures/native compilation, replaced only the bar
again. Current PID 763752, run `work/bar-session/20261025T074555.536962Z`;
`Configuration Loaded`, no component/binding errors, only the previously known
portal app-ID registration warning. The bar has session lifetime, not a timer.
Previous launch/profile were backed up under
`work/desktop-rollout/20261025T074324.611555Z`; previous staged source remains
intact. Host configuration was not edited, no Hyprland reload, installation,
service activation, lock, suspend, shutdown, logout, commit or publication.
Native popup/pointer, real pairing, brightness permission, scale and profile
change acceptance remain unclaimed.

## Local user installer, standalone releases and screen-lock prerequisites

The user requested a local installer with Start/Stop/Status, versioned updates
and rollback before daily-use tests and later Hyprland-only autostart. Implemented
`tools/package_user.py`, standalone `tools/user_install.py` (also shipped as the
release manager), `tools/check_user_release.py` and read-only
`tools/lock_readiness.py`. Installation defaults to named user data/state/bin
paths, but no host apply has occurred. Source-only backups of existing files
edited in this phase are under `work/deployment-source-backups/`.

The packager verifies the sealed QML profile and pinned build, copies selected
surfaces/helpers/runtime, makes only the qs alias relative, preserves MIT/LGPL/GPL
notices and records release integrity/provenance. The installed manager has no
development-module imports or runtime dependency on Git/work/. Display pre-state
backups now honor the installed private state directory. Installed helper
bytecode writing is disabled to avoid modifying release contents.

Deployment implements a read-only plan, explicit apply, verified incoming copy,
unique version directories, atomic version selectors, backed-up launcher bytes
and mode, idempotent reinstall, previous-version rollback and first-install
launcher restoration. Prepared journals block activation until reviewed explicit
recovery. Corrupt backups, external launcher changes, path escapes, unsafe links,
manifest changes and overlapping deployment locations are refused. No package
install, user service, autostart, global shell PATH edit or Hyprland config edit is
performed. Manual start requires the actual matching Hyprland session and refuses
GNOME or a competing Quickshell; stop validates UID/PID/start ticks/exact argv and
never terminates the compositor. No expiry or crash supervisor was introduced.

Verification: 271 tests pass (`work/user-install-unit-tests.log`). Standalone
bundle `work/user-releases/20261025-local.3` passes actual imports/linkage and
session-grant parsing at a relocated Bubblewrap path without the original /opt
prefix: `work/user-release-checks/20261025T081834.357280Z/report.json`.
An actual workspace-only install/update/verify/rollback round trip passes under
`work/user-install-smoke/`; the final manager selected local.3 and rolled back to
local.1 without launching any desktop process. The isolated original desktop
panel fixture also passed at
`work/desktop-panels/20261025T081641.158295Z/report.json`. None of these results is
native daily-use, autostart, authentication or security acceptance.

Lock investigation: no hyprlock or swaylock executable is installed; hyprlock is
in residual-config state. Existing UWSM units identify the Hyprland-specific
session target. APT simulation for existing-source candidate
hyprlock=0.9.6-1ppa1~1resolute1 proposes exactly one new package, no upgrades or
removals. Downloaded that candidate only into ignored work/ for file inspection;
its PAM service bytes match the existing residual `/etc/pam.d/hyprlock` exactly.
No PAM content was edited and no package installed. Presence/matching files do
not prove authentication. A standalone Hyprlock would be an explicitly agreed
substitute for the unadmitted original lock UI. Package choice/installation,
authentication preflight, independent recovery and a supervised lock test remain
separate approval gates. No lock action, shortcut, idle timer, suspend or session
transition was added or invoked. See `docs/lock-readiness.md`.

The host installation plan is read-only in `work/user-install-host-plan.json`:
new `~/.local/share/omabuntu`, `~/.local/state/omabuntu` and regular
`~/.local/bin/omabuntu`; no existing launcher at that path. The live workspace
trial remains PID 763752, unchanged. No GNOME/login/default-session change,
service activation, commit or publication. See `docs/user-installation.md` for
exact command boundaries and retained-artifact/rollback limitations.

## Approved host user installation and Hyprlock package attempt

The user explicitly approved applying the named user installation and using
standalone Hyprlock with the exact reviewed package transaction. Reran all 271
Python tests and isolated release relocation checks before apply. Installed
`20261025-local.3` under `~/.local/share/omabuntu`, wrote the regular
`~/.local/bin/omabuntu` bootstrap and private state under
`~/.local/state/omabuntu`. First-install path existence and selector/launcher
pre-state are recorded in the install transaction
`~/.local/state/omabuntu/transactions/20261025T083707.738071Z` and the private
workspace apply report `work/user-install-host-apply.json`. Verification passed.
No previous launcher or installation at those paths was overwritten.

Completed a bar-only handoff after checking the recorded trial process identity,
installed release integrity and the existing trial's actual Hyprland socket.
Read only selected session variables from that known trial, never printed or
stored its full environment. Stopped only trial PID 763752; applications and
Hyprland stayed running. Started the standalone installed manager against the
same session. Current installed PID is 864982, log
`~/.local/state/omabuntu/runs/20261025T083924.000370Z/output.log`.
The startup contains Configuration Loaded and the explicit no-expiry grant;
no component/binding errors, only the known portal app-ID warning. Status and
release verification pass. Handoff pre-state is retained in
`work/installed-handoff/20261025T083923.589289Z`. The bar's executable, QML and
helpers now come from the installed version, not the Git/work directory.
Native daily-use/device acceptance is still not implied by successful startup.

Before Hyprlock installation, rechecked the exact candidate hash and APT
simulation (one new package, no upgrades/removals). Inspected package control
metadata: no maintainer scripts or service activation hooks. Recorded package
residual-config version, auto-mark state and every affected package path's
pre-existence/type/mode/owner; verified backups of existing regular files,
including the identical PAM service, under
`work/hyprlock-install/20261025T083812.214594Z`. The approved noninteractive
`sudo -n apt-get` attempt failed immediately with interactive authentication
required. APT did not start. No retry, credential request or authentication
bypass was attempted. Hyprlock remains uninstalled (dpkg residual-config state)
and the PAM file hash is unchanged. The user must run the approved pinned APT
command in their local terminal; do not send credentials to the agent.

Existing source-document backups for this phase are under
`work/approved-install-doc-backups/`. No saved Hyprland configuration, GNOME,
login/default session, sudo policy, authentication policy or corporate service
was changed. No lock, idle/suspend action, shortcut, service activation,
autostart, session transition, commit or publication. Authentication/recovery
verification and a supervised lock test remain separate pending gates.

## Hyprlock user installation confirmed, still no lock activation

The user reported the local privileged package command succeeded. Verified
`/usr/bin/hyprlock`, upstream version v0.9.6 and dpkg installed status for
`0.9.6-1ppa1~1resolute1`. Only help/version/read-only status probes were run.
The PAM service bytes still match the pre-install backup. Read the selected
service: its authentication delegates to the existing login stack. Reviewed the
official v0.9.6 PAM implementation/config defaults: service hyprlock and
pam_authenticate, with no CLI auth-only or parse-only test. Grace is not a safe
non-locking auth preflight. No original source installer or Arch command ran.

Fresh private readiness report:
`work/lock-readiness/20261025T084544.726348Z/report.json`. The report correctly
keeps authentication/recovery unverified and activation disallowed. The local
active Wayland session reports VT 2; no independent TTY login/recovery test has
been performed. Only queried getty status; no service activation or console
switch. The next step needs the user's deliberate local console-login check,
followed by an exact authentication/recovery acceptance plan before a supervised
manual lock. Do not request, read or log credentials, and do not use killing the
locker as an assumed unlock mechanism. Installed Omabuntu remains PID 864982.
No lock configuration, shortcut, idle/suspend, autostart, session transition,
PAM policy change, commit or publication. Documentation pre-state is saved in
`work/hyprlock-confirmed-doc-backups/`.

## Manual lock surface prepared, supervised test pending

Added an authored, static `config/lock/hyprlock.conf` (no `cmd[...]`, `onclick`,
script, source or user-config inclusion; no PAM override) plus
`tools/lock_session.py` and an explicit manager `lock` action. Upstream's packaged
sample config is not used because it executes `date` and `hyprctl`. The helper
requires `--apply`, refuses root, GNOME/ambiguous sessions, a mismatched Hyprland
socket, a non-v0.9.6 Hyprlock, a second locker, symlinked or directive-bearing
config, and always passes `--config`, so user config files are not consulted.
No idle timer, daemon, supervisor, autostart, suspend or session control exists.

Preflight on the installed release failed first because the guard treated the
static `fail_text = Authentication failed` as an `auth` block; fixed to match an
actual `auth {` block and re-tested. Also fixed the manager's `--apply` guard to
cover `lock`. 282 tests pass (`work/manual-lock-unit-tests.log`).

Packaged and installed `20261025-local.4` (lock files, still broken guard) then
`20261025-local.5` (fixed guard) with the approved bar-only update path: stopped
only the installed bar, updated, restarted, verified. Releases are kept; update
transactions are recorded in `~/.local/state/omabuntu/transactions/`. Current
installed PID 880277, log
`~/.local/state/omabuntu/runs/20261025T090240.046051Z/output.log`, only the known
portal warning. Preflight without locking now passes on `wayland-1` with
status `planned-not-locked`; that is not an authentication verdict.

No lock was triggered: `omabuntu lock` without `--apply` correctly refused.
The supervised manual lock/unlock and the wrong-password path must be started
deliberately by the user with `~/.local/bin/omabuntu lock --apply`; credentials
only inside Hyprlock. TTY recovery was reported verified by the user beforehand;
do not treat process start, preflight or a single output as lock acceptance.
Docs pre-state is in `work/manual-lock-doc-backups/`. No shortcut, idle/suspend,
autostart, PAM edit, service activation, Hyprland reload, commit or publication.

## Manual lock round trip accepted (all three outputs)

The user ran the explicit `lock --apply` action and reported that the lock appeared
and unlocking worked. The private helper log independently confirms the session-lock
protocol, lock surfaces on eDP-1 (150% fractional), DP-7 and DP-9, the `Password: `
PAM prompt, successful `pam_authenticate` for service `hyprlock`, unlock, exit 0 and
no leftover process. The installed bar PID 880277 survived.

Accepted: manual lock, correct-password unlock, three outputs, clean exit.
Not accepted and still open: wrong-password path (no failed attempt recorded),
idle-before-lock, hotplug/DPMS/suspend while locked, fingerprint, shortcut,
automatic locking and corporate-policy sign-off for the delegated login PAM stack.
No lock shortcut, idle timer, autostart, suspend, PAM edit, service activation,
Hyprland reload, commit or publication. Docs pre-state in
`work/lock-acceptance-doc-backups/`.

## Dock parity analysis against pinned Omarchy (no fix yet)

User reported five dock problems on floating workspaces: partial disappearance after
switching workspaces/screens, no minimise/maximise, no window indicator, no
pin/unpin and no drag from the app panel. Compared the derived dock with the pinned
originals (`Dock.qml`, `DockWindow.qml`, `DockModel.js`, `AppGrid.qml`,
`bin/omarchy-hyprland-window-minimize`, `bin/omarchy-dock`,
`default/hypr/bindings/tiling.lua`, `default/hypr/workspace-modes.lua`).

Findings, recorded in `docs/dock-parity.md`:

- Window-to-entry mapping is the root defect: `DesktopEntries.byId(class)` cannot
  match `firefox` to `firefox.desktop`, and keys are stored without `.desktop`, so
  `entryFor()` returns null. That breaks icons, launch, quit and both pin menu
  actions. Omarchy uses `heuristicLookup` plus terminal `--app-id=` claiming.
- Visibility is stale: `fullscreenMode` is never refreshed on `fullscreen` /
  `configreloaded` events, so a maximised window can leave `autohide` true and the
  content tucked behind the edge trigger. The slot model is also cleared and
  rebuilt wholesale instead of being synced incrementally.
- Minimise/maximise does not exist in this port. In Omarchy those buttons come from
  the hyprbars titlebar for floating workspaces (`workspace-modes.lua:488-501`)
  plus `SUPER+M` -> `omarchy-hyprland-window-minimize`; minimised windows go to
  `special:minimized` with `omarchy-minimized-from-<id>` tags and the dock restores
  them. hyprbars is not built or loaded here.
- Omarchy's dock has **no** per-window dot indicator; only running opacity and a
  10 s launch pulse. A window indicator would therefore be an authored deviation.
- Pins are session-only here with no default pins; Omarchy persists them through
  `omarchy-dock`. No drag-to-dock exists because the authored app panel has no drag
  source and the dock exposes no routing entry point.

No dock code, keybinding, plugin, configuration, service or installed release was
changed. Implementation waits on the three decisions in the document (minimise
surface, pin persistence, indicator scope).

## Dock proposal recorded; no implementation started

User asked for Omarchy-identical dock behaviour. Established that the titlebar
×/□/− buttons on floating workspaces are the hyprbars Hyprland plugin, shipped by
Omarchy as `omarchy-hyprland-titlebars` and configured in `workspace-modes.lua`
(supervised: `if not hl.plugin.hyprbars then return end`), and that the dock itself
never minimises — it only restores windows from `special:minimized`.

Host feasibility for that plugin: Hyprland 0.56.2 (`efb50993…`, abiHash
`…_aq_0.15_hu_0.14_hg_0.5_hc_0.1_hlg_0.6`), matching headers already installed
(`/usr/include/hyprland`, `hyprland.pc` 0.56.2), hyprbars source in
`hyprwm/hyprland-plugins`. PPA `hyprland-plugin-deps` would add 59 packages and
upgrade `libhyprutils13` 0.14.2 -> 0.14.3, a library Hyprland links against; that
upgrade is the main risk and was only simulated. Loading needs a config edit plus
reload, which re-reads config and drops runtime workspace tags. `hyprpm` needs a
root state store.

Proposal A-D appended to `docs/dock-parity.md`: A fixes the reported defects with no
new dependencies (mapping, incremental sync, refresh on fullscreen/configreloaded,
minimised restore, pulse, own pin/position persistence), B adds hyprbars after a
separate dependency/config/reload approval, C adds app-panel drag, D would be an
authored indicator deviation. No dock, plugin, package, config, service or release
was changed; everything remains analysis plus a plan.

## Dock Packages A and C implemented and installed

Implemented the reported dock defects and the app-panel drag, then installed release
`20261025-local.6` through the approved stop/update/start path (previous local.5 kept).
Current PID 887748; startup log has Configuration Loaded, the no-expiry grant and no
error/binding/assignment lines.

Code: `FloatingDock.qml` rewritten on the upstream pipeline (wayland `appId`,
`heuristicLookup`, terminal claiming, dialog/noDisplay filtering, `.desktop` ids,
incremental `ListModel` sync, launch pulse, pin/order placement, restore of
`special:minimized` with focus and z-order, external-drag routing, and a
`fullscreen`/`configreloaded` refresh). `DockState.qml` plus `helpers/dock_state.py`
persist position/autohide/pins in `~/.config/omabuntu/dock.json` (atomic, 0600, one
backup, strict validation). `AppLauncher.qml` gained the drag handshake. The dock menu
gained Minimize/Maximize as a documented deviation until the hyprbars titlebar exists;
`tools/desktop_frontends.py` adds those rows from a unique witness.

Tests: 301 pass, including a 16-case dock/state suite; isolated desktop QML compile and
construct passed; relocated release check passed. No reload, no config edit, no plugin,
no package.

Package B (hyprbars) prepared only: `tools/build_hyprbars.py` pins
`hyprland-plugins@d2427d4d…`, refuses any Hyprland but `efb50993…`, builds out of tree
and never loads/edits config/reloads. Blocked because the plugin's pkg-config set needs
development packages (simulated: 20 new, `libhyprutils13` 0.14.2→0.14.3, no removals);
the user must run the privileged install. `config/hypr/hyprbars.lua` is the reviewed
button snippet for our floated tag; it parses (`--verify-config` → config ok) and is not
included anywhere. Native pointer/window/drag acceptance is still the user's next test.

## Package prerequisites documented; hyprbars build still needs nine dev packages

User installed the first development set and asked for the package requirements to be
documented. Verified installed: `hyprwayland-scanner` 0.4.6, `libcairo2-dev` 1.18.4,
`libpango1.0-dev` 1.57.0, `libhyprlang-dev` 0.6.8, `libhyprutils-dev` 0.14.3 and the
`libhyprutils13` 0.14.2 -> 0.14.3 upgrade.

`pkg-config hyprland` still fails because `hyprland.pc` declares `Requires: aquamarine,
hyprcursor, hyprgraphics, xcb-xfixes, xcb-icccm, xcb-composite, xcb-res, xcb-errors`.
Simulated the minimal remaining set: 9 new packages (`libhyprcursor-dev`,
`libhyprgraphics-dev`, `libaquamarine-dev`, `libxcb1-dev`, `libxcb-xfixes0-dev`,
`libxcb-icccm4-dev`, `libxcb-composite0-dev`, `libxcb-res0-dev`, `libxcb-errors-dev`,
`libxcb-shape0-dev`), no removals and no further upgrades. Nothing installed by me.

Added `docs/dependencies.md` with the full verified package picture: compositor/session,
services the panels talk to (NetworkManager, BlueZ, PipeWire, UPower,
power-profiles-daemon, logind), the built-in Quickshell runtime and fonts, the screen
lock package, the hyprbars build prerequisites and what is deliberately absent, plus a
reproduction query. `packages/README.md` and `README.md` now link to it.
`tools/build_hyprbars.py` carries the corrected, complete APT hint and still refuses to
install, load, edit config or reload.

Tests: 301 pass. No Hyprland reload, config edit, plugin load, service or release change.

## hyprbars build: PPA headers unusable, source checkout prepared

User installed the remaining development packages. `pkg-config hyprland` now resolves,
but the build failed for two separate reasons.

1. **The PPA header set does not match the running binary.** `/usr/include/hyprland`
   has `src/desktop/view/Window.hpp`, while the pinned hyprbars commit includes
   `hyprland/src/desktop/view/window/Window.hpp`. Plugins must build against the
   Hyprland source tree at the exact commit, as `hyprpm` does. Cloned
   `hyprwm/Hyprland` at `efb50993780079460b0cbed1363e2166a2de1d9f` into
   `work/hyprland-headers/hyprland` (verified HEAD) and generated the 41 required
   Wayland protocol headers with `hyprwayland-scanner` (wayland.xml with
   `--wayland-enums`, plus stable/unstable/staging and Hyprland's own protocols) into
   that checkout's `protocols/` directory.
2. **A private `hyprland.pc`** under `work/hyprland-pc` points at that checkout
   (`-I<root>`, `-I<root>/hyprland/protocols`, `-I<root>/hyprland/src`) and keeps the
   declared `Requires:` list. CMake caches imported-target flags, so the build
   directory must be recreated after any `.pc` change — that cost one failed attempt.
3. **Only `glslang-dev` is still missing**: `src/render/ShaderLoader.hpp` includes
   `glslang/Include/glslang_c_interface.h`. Simulated: 3 new packages
   (`glslang-dev`, `glslang-tools`, `spirv-tools-dev`/`headers`), no removals, no
   upgrades. Nothing installed by me; the exact command is in
   `docs/dependencies.md` and in the build tool's hint.

`docs/dependencies.md` now documents the header mismatch, the source-checkout
requirement, the protocol-generation step and the extra `glslang-dev` package.
`tools/build_hyprbars.py` carries the corrected hint; tests patch the module probe so
the suite stays independent of installed packages. 301 tests pass. No plugin loaded,
no config edited, no reload, no service, no release change; bar still PID 887748.

## hyprbars: reference build loaded, migration to hyprpm prepared

User asked why hyprbars was compiled instead of using hyprpm. Answer recorded in
`docs/hyprbars.md`: hyprpm keeps a root state store (`hyprpm list` failed with
"Failed to run a superuser cmd") and this environment cannot answer interactive
sudo, so the build reproduced what hyprpm does. hyprpm is the right permanent tool.

Build findings this round: the plugin had to be pinned to `hyprland-plugins v0.56.0`
(`7644cecd…`); the earlier `main` commit needs Hyprland `main` headers. Hyprland
generates `src/version.h` only during its own build, so the tool now writes it from
`version.h.in` with the live version data, and the private `hyprland.pc` had to add
`lua5.4` for `lua.h`. `hyprland-plugin-deps` (27 packages, no upgrades) supplied the
remaining third-party headers. Result:
`work/hyprbars-build/build/libhyprbars.so`, also copied to
`~/.local/lib/omabuntu/hyprbars.so` (SHA-256 `02296a7b…`).

Loaded with `hyprctl plugin load`, verified: `hyprctl plugin list` shows hyprbars,
`configerrors` empty, three monitors and the bar (PID 898801) alive. The first
config attempt failed because `workspace_tag`/`button_rounding` do not exist in
v0.56.0; rewrote `config/hypr/hyprbars.lua` to the v0.56.0 option set and the eval
then returned `ok` with `plugin:hyprbars:bar_height` 30, the font and button
alignment set. `hyprctl getoption plugin:hyprbars:enabled` confirmed the switcher
gating: the generated floating program sets it true, the dwindle program sets it
false, so bars appear only on floating workspaces.

Because v0.56.0 has no workspace tag, gating lives in `tools/workspace_modes.py`
(`setTitlebars`, guarded by `hl.plugin and hl.plugin.hyprbars`); the mirror was
regenerated and release `20261025-local.7` was built, verified and installed
(PID 898801). Tests 301 pass; isolated desktop QML check passed.

Persistent loading is still missing and needs `hyprpm reload` in the autostarts plus
the reviewed include from the user's `hyprland.lua`, both separate approvals. No
config file was edited and Hyprland was not reloaded. Migration steps, verification
and rollback are in `docs/hyprbars.md`; the user runs the sudo commands.

## hyprpm migration verification and correction

After the user completed the non-sudo commands, `hyprpm list` reported the
repository registered but hyprbars and csgo-vulkan-fix failed to build. Migration
is not complete. `hyprctl plugin list -j` still reports one hyprbars plugin and
`hyprctl configerrors` is empty. No plugin load/unload, enable, reload or active
configuration change was performed in this verification.

Corrected `docs/hyprbars.md` and `docs/dock-parity.md`: never invoke hyprpm as
root; an internally requested elevation is not permission to run the entire
manager with sudo. Earlier statements in this historical worklog about the
state store did not justify that advice. The loaded library's original path is
the workspace build path, not the later user-local copy. Also corrected the
overstatement about titlebar isolation: the current switcher toggles a global
option and does not provide per-workspace/multi-monitor parity. Build failure
output is needed before deciding on the next build attempt. Documentation
backups are under ignored `work/hyprpm-correction-backups/`.

## Prepared process-scoped hyprpm wrapper

User approved preparing a wrapper, tests and installation instructions without
changing the active shell. Added `tools/omabuntu_hyprpm.py`: requires the existing
Lua header and hyprpm, copies the environment, appends the Lua include directory
without replacing existing entries, and execs hyprpm with unchanged arguments.
No shell, automatic sudo/force/update/reload, global environment mutation,
package installation or desktop action. Eight unit tests cover environment and
argument preservation plus missing prerequisites and exec failure.

Updated `docs/hyprbars.md` with the user's successful environment-scoped build
evidence and a standalone installation/rollback plan. Header/ABI verification
remains pending; hyprpm's update reconciled load state and reported unloading
hyprbars. The wrapper is prepared in the repository only, not installed in
`~/.local/bin`, not included in a release and not executed against live hyprpm.
Documentation backups are under `work/hyprpm-wrapper-backups/`.

## Installed standalone hyprpm wrapper

User approved installation. Rejected symlink parents/target and checked ownership
before installing `~/.local/bin/omabuntu-hyprpm` atomically with mode 0755.
The target was absent; no previous wrapper needed backing up. Recorded previous
directory state and verified source/installed content hash in
`~/.local/state/omabuntu/hyprpm-wrapper-20261025T100916.636919Z/transaction.json`.
SHA-256: `947441ebab3e23cbecf3b5b948eefad166efc9d960542e0f044b2ca3cf5dc288`.
No hyprpm execution, build, plugin load/unload, config reload or shell/environment
change. Agent PATH does not resolve the short name; documented explicit path.
Documentation backups: `work/hyprpm-wrapper-install-backups/`.

## hyprbars limited to the floated tag

Header check: `/usr/include/hyprland/src/version.h` matches the running Hyprland
0.56.2 commit `efb50993780079460b0cbed1363e2166a2de1d9f`, and hyprpm's pkg-config
prefix is `/usr/include`, so the successful hyprpm build used those headers.
The user enabled and loaded only hyprbars through hyprpm. No config errors.

Replaced the global enabled toggle in `tools/workspace_modes.py` with a refresh
of the named rules `omabuntu-hyprbars-hide` and `omabuntu-hyprbars-show-floated`.
`config/hypr/hyprbars.lua` defines those rules once, plus the existing buttons.
Applied that file once to the running compositor. A disposable Ghostty on
workspace 6 showed the 30px bar only while tagged, after the rule refresh; other
monitors' untagged windows did not shrink. Maximize toggled and restored.
Minimize reached `special:minimized` and left focus, but no other window became
active and no origin tag was stored. The close request did not end the sleep
process. Chrome was not shown to gain or lose a bar. No user config include,
autostart, or Hyprland reload. Release `20261025-local.8` was prepared so the
running bar stops using the global toggle.

Titlebar close/minimize fix: hyprbars v0.56.0 does not substitute the Omarchy
window placeholder. `config/hypr/hyprbars.lua` now uses `activewindow`,
`closewindow activewindow`, and `~/.local/bin/omabuntu-hyprland-window-minimize`
(from `tools/omabuntu_hyprland_window_minimize.py`) to tag
`omabuntu-minimized-from-<workspace>` and refocus the origin workspace. Applied
with `omabuntu-hyprpm reload -n` plus one `hyprctl eval` of the snippet.

Dock fixes for `20261025-local.9`: (1) Pins were silently dropped because
Quickshell entry ids carry no `.desktop` suffix while `DockState.qml` and
`dock_state.py` required one; both now accept bare ids (suffix stays readable),
which fixes Keep-in-dock and app-panel drag-to-dock. (2) New windows on a
workspace this session set floating now join the mode: `workspace_modes.py`
gained a claim eval (tag + float + cascade place + named-rule refresh) wired to
Hyprland's `openwindow` event in the switcher, gated by TrialDesktopState.
(3) The app panel keybind `SUPER + ALT + SPACE` was never bound in the
compositor; a session-only runtime bind `hl.dsp.global("omabuntu:apps")` was
evaluated (no config edit, no reload).

## Network panel state synchronization and upstream behavior restoration

Implemented the requested network-panel fixes in repository sources only.
Compared against the unchanged vendored Omarchy panel at
`03ff1eff3812933f7088484533784d2f63eaf19a`. Successful and failed native
network actions now schedule a snapshot rebuild without reopening the panel.
The first new isolated regression exposed delegate destruction during a running
signal handler when rebuilding synchronously; deferring via `Qt.callLater`
resolves that lifecycle issue. Still-visible forgotten APs move to Other
Networks rather than being hidden.

Restored list-selection clamping, password-SSID selection tracking, editor
focus return, DNS/band keyboard index synchronization (including asynchronous
status), portal focus transitions, and the post-deferral scan completion
refresh. Closing cancels both scan timers. Added a read-only, bounded helper
operation for cached in-use AP signal strength, used only when native strength
is absent; interface and generation checks reject obsolete results. It does
not scan, read secrets, activate services, or change network settings.

The generated view remains derived from the original layout; the extraction
adds the editor-focus handler. Updated only the corresponding authored/staged
hashes in `upstream/clock-preview.json`, not upstream provenance. Intentional
Ubuntu DNS/enterprise/portal/QR/speed-test differences remain unchanged.

Validation: `python3 -m unittest discover -s tests -v` passes all 316 tests;
log: `work/network-refresh-unit-tests.log`. Expanded the isolated Wi-Fi suite
from seven to eleven cases, covering property-only forget/connect/disconnect/
failure transitions, keyboard indices and focus, scan completion, and signal
fallback/stale replies. All eleven pass in
`work/wifi-port/20261025T171550.674146Z/report.json`; the isolated network status
regression also passes in
`work/network-port/20261025T171614.290348Z/report.json`. Both use the existing
private runtime with Bubblewrap and fake Networking, without host DBus or
network access. Earlier failing private runs remain as diagnostic evidence.

Previous source states were backed up under
`work/network-refresh-backups/20261025T171000Z/`, including the staging manifest.
No installed files, running bar, desktop session, packages, services, or actual
NetworkManager profiles changed. No commit or deployment was performed; live
popup/focus/radio acceptance remains unverified.

Installation requested: prepared local bundle `20261025-local.12` and passed
its isolated relocation check in
`work/user-release-checks/20261025T172135.754651Z/report.json`. Read-only plan
confirmed installed release `.11` is running. No host installation applied yet:
the installer requires stopping the bar before switching versions. Awaiting
explicit approval for the bar-only stop/start; no compositor/session restart,
reload, service activation, or autostart is needed.

User explicitly approved the bar-only stop/install/start. Installed and started
`20261025-local.12`; manager verify/status confirm the selected release is
running with the explicit session-lifetime grant. Previous release `.11` is
retained as rollback target. Installer backed up selectors and launcher under
`~/.local/state/omabuntu/transactions/20261025T172316.756820Z/` before replacement.
Private operation report: `work/installed-update-local.12.json`.
Startup log: `~/.local/state/omabuntu/runs/20261025T172316.946403Z/output.log`;
inspection found one DBus warning, no ERROR/FATAL/CRITICAL entries and no
network-QML error lines. Startup/integrity success is not functional radio or
popup acceptance. No compositor restart/reload, application stop, package
change, service activation, autostart or lock activation was performed. User
verification of the original forget/refresh interaction remains outstanding.
User later confirmed the live network panel updates correctly after forget.

## Keybindings menu plan

Analyzed Omarchy Super+K at the pinned commit
`03ff1eff3812933f7088484533784d2f63eaf19a`. It launches
`omarchy-menu-keybindings`, a searchable 800x500 menu of live `hyprctl binds`,
not a bar panel. The script and `omarchy-menu-select` are outside the vendored
shell subset and were not imported or executed. Wrote the read-only
implementation plan `plans/000-keybindings-menu.md` and added the `plans/`
filename, evidence, checkbox, and non-approval rules to `AGENTS.md`.
No binding, compositor query, bar restart, or desktop change was made for this
plan.

## Keybindings menu

Implemented the Super+K analogue in the repository: a searchable 800x500
overlay of the bindings Hyprland reports, plus dispatch of the selected
existing action. `tools/keybindings_menu.py` parses plain binds, recovers
unlabeled `hl.bind` calls in a restricted Lua 5.4 state, and refuses lock,
suspend, idle, and other session-ending commands even when they are already
configured. Commands absent from the list just read are refused. The menu does
not create or edit bindings. Tmux, Herdr, static web-app shortcuts, and
platform key-name files stay out. `omarchy-menu-keybindings` was not imported
or executed.

`TrialShell.qml` mounts `KeybindingsMenu.qml` and registers the global shortcut
name `omabuntu:keybindings`. No key is bound to it. Super+K was not bound in
the running session. `~/.config/hypr/hyprland.lua` was not rewritten. The
installed bar was not restarted and does not contain this menu yet.

330 Python tests passed (`work/keybindings-menu-unit-tests.log`).
Offscreen selector report:
`work/keys-port/20261025T192458.015893Z/report.json`
(`isolated-keys-fixtures-passed`). A later read-only list against the running
compositor returned 31 rows, was not saved, and did not dispatch. Super+K was
not among them.

The user then approved a bar-only stop, install, and start, plus one
session-only Super+K binding. Packaged `20261025-local.13` and passed its
relocation check in
`work/user-release-checks/20261025T195719.680152Z/report.json`. The first
package was discarded before installation because its manager would have
rejected rollback to `.12`; the replacement bundle does not do that. Stopped
only the installed bar, installed `.13`, and started it. Previous release is
`.12`. Selector and launcher backup:
`~/.local/state/omabuntu/transactions/20261025T195829.315892Z/`.
Operation report: `work/installed-update-local.13.json`. Running pid 234619,
session lifetime, no autostart. Startup log:
`~/.local/state/omabuntu/runs/20261025T195829.521657Z/output.log`
(the known portal warning only; no ERROR/FATAL/CRITICAL).

Super+K was free (31 bindings). Added one session binding to
`omabuntu:keybindings` with `hyprctl eval`. Bind count is 32, with exactly one
Super+K. `~/.config/hypr/hyprland.lua` was not modified. `omabuntu:apps`
remains registered. The shortcut opened and closed the menu. The installed
helper refused an unknown command and refused `uwsm stop` without stopping the
session. Focus left and focus right were dispatched through that helper and
both returned ok. No compositor restart, package install, service, autostart,
lock, or commit. The session binding disappears on a Hyprland restart. See
`docs/keybindings-menu.md`.

## 2026-10-25: Command menu analysis and plan 002

Analyzed the pinned Omarchy sources (commit `03ff1eff`, fetched read-only into
ignored `work/menu-analysis/03ff1eff/`) for the Super+Space root menu and the
Super+Esc system menu. The menu is the `omarchy.menu` Quickshell plugin
(`Menu.qml`, `MenuModel.js`) driven by `omarchy-menu.jsonc` definitions; themes
ship as `colors.toml` palettes in `themes/*`; backgrounds are image assets and
stay unimported. Verified on this machine: Super+Space and Super+Esc are
unbound (32 binds), UWSM session active, hibernation unverified, no wallpaper
daemon. Wrote `plans/002-command-menu.md` covering the derived surface, the
Ubuntu-adapted routes, Python theme/font/background backends, gated power
actions, and the explicit exclusions. No desktop, binding, package, or service
changes were made.

## 2026-10-25: Command menu and system menu implementation (plan 002)

Implemented the Super+Space root menu and the Super+Esc system menu as the
reviewed reproduction of Omarchy's `omarchy.menu` plugin at the pinned
commit. No upstream menu script, image asset, locale catalog, or theme
background is imported or executed.

Surface and model: `config/shell/preview/CommandMenu.qml` (pinned card
geometry, search, submenu navigation, guard-driven visibility, check marks,
provider merge, drilldown divider, session lifetime) with the pure logic
ported to `config/shell/preview/MenuModel.js`; definitions in
`config/shell/omabuntu-menu.jsonc` with the user-overlay merge.
`TrialShell.qml` mounts it and wires the Apps and Keybindings routes. The card
registers `omabuntu:menu` and `omabuntu:system` shortcuts; no key is bound.

Backends (Python stdlib): `menu_model.py` (JSONC subset, merge, route
resolution, batched guard script with shared readers, provider rows, allowlist
dispatch), `theme_backend.py` (23 upstream palettes recorded as color data
with per-file hashes in `config/menu/themes.json`; live apply limited to the
two Hyprland border keywords, state plus backup under the state home),
`font_backend.py` (fc-list families, gsettings font state),
`background_backend.py` (Ubuntu backgrounds and ~/Pictures list/set state, no
daemon), `power_actions.py` (gated logout/reboot/shutdown/suspend/hibernate;
hibernate additionally refuses until the resume path is verified),
`menu_common.py` (state home, backups, records).

Release plumbing: `package_user.py` stages the six menu helpers plus the
definitions and palettes into the bundle; `user_install.py` requires them,
passes `OMABUNTU_MENU_HELPER`, `OMABUNTU_MENU_DEFINITIONS`, `OMABUNTU_MENU_THEMES`
to the bar, and treats the new TrialShell failure markers as fatal;
`bar_session.py` passes the same variables for workspace trial runs. No
release was packaged, installed, or started.

Fixed one real surface bug found by the offscreen fixture: `searchDivider`
was declared readonly while `rebuildDisplay` assigns it. Profile records for
`CommandMenu.qml`, `MenuModel.js`, and `TrialShell.qml` were updated in
`upstream/clock-preview.json`, and `check_clock_preview.py` admits both files
into the authored set with the same Process/Helper contract as the
keybindings menu.

Offscreen evidence: `work/menu-port/20261025T203721.360444Z/report.json`
(`isolated-menu-fixtures-passed`) — definitions, guard batch, root rows,
navigation, system route with guard-driven counts, power gate refusal, hidden,
disabled and checked overlay rows, cursor skip, apps route, search with the
drilldown divider, 23 theme provider rows with the check glyph, and a theme
apply that records state plus backup, all through the real helper under bwrap.
See `docs/command-menu.md` for scope and limits. 372 Python tests pass.

The packaging, session binds, and power gates were applied later; see the
command-menu session entry. Live theme, font, and background apply remains
unapproved.

## 2026-10-25: Top bar parity — menu mark, keyboard layout, frame/theme (plan 004)

Closed three deviations of the live bar against the pinned Omarchy commit
`03ff1eff`, recorded in `plans/004-top-bar-parity.md`. Nothing was packaged,
installed, or started; the running bar process is unchanged.

Menu button: the missing first widget is back at the left edge. The upstream
`omarchy.ttf` also carries third-party agent marks, so the binary font stays
unimported; `tools/extract_menu_mark.py` (stdlib TrueType reader) records only
Omarchy's own U+E900 outline as path data in `upstream/omarchy-mark.json`.
The authored `OmarchyMark.qml` draws it through a `QtQuick.Shapes` `PathSvg`
inside the original `BarIconButton`'s `iconComponent` slot; left click opens
the command menu's root route, right click runs `xdg-terminal-exec` through
the new allowlisted `run`.

Keyboard layout: `KeyboardLayout.qml`, `KeyboardLayoutModel.js`,
`Commons/Util.qml` and `Commons/InputDevices.qml` are vendored byte-identically;
the staged mirror applies one witnessed transform (`keyboard-layout-widget-v1`):
visibility also honors `alwaysShow` because this seat runs a single `de` layout
and upstream would hide the widget the user asked for. `InputMethodState.qml`
is a restricted authored singleton: the upstream fcitx indicator is not ported,
so `cycle` refuses. Layout cycling goes through the `BarRun.js` allowlist
(`hyprctl switchxkblayout <name> <index>` segments only). Mounted between tray
and Bluetooth, Omarchy's default order.

Frame/theme: `Color.qml` now loads the reviewed theme state
(`~/.local/state/omabuntu/current/theme.json`) through a watched `FileView`;
`TrialPanel.qml`, `PortTrayHost.qml`, `LiveStatus.qml` and the switcher bind to
it instead of hardcoded `#101315`/`#cacccc`. The bar gains the upstream 420 ms
OutCubic color behaviors, the opaque/glassy/none looks read from
`~/.local/state/omabuntu/current/bar.json`, and the bar-off flag with the
upstream park-off-screen + `ExclusionMode.Ignore` behavior. Blur sync was
dropped after a live probe: Hyprland 0.56 has no runtime layerrule keyword
(config-only), so a glassy bar keeps its faint background and blur stays the
user's own global setting.

Provenance: new upstream records (blobs, SHAs, transform ids) in
`upstream/clock-preview.json`; staging maps in `check_clock_preview.py`
updated (50 upstream + 33 authored entries, 87 staged files verified).
Tests: `tests/test_top_bar_parity.py` covers mark/record consistency, the
keyboard transform mirror, allowlist refusal cases and background-look
parsing; suite is green at 399 tests. Pre-existing contracts that forbade any
Process/FileView in authored files were narrowed to the reviewed exceptions
(one bar-off probe, the two watched state files, the theme file) rather than
weakened. Live activation (packaging and replacing the bar) still needs
explicit approval.

## 2026-10-25: xkbcli installed by the user; keyboard widget documented

The user installed `libxkbcommon-tools` 1.13.1-1 from the already configured
`universe` archive with `sudo apt-get --no-install-recommends install`, so the
keyboard-layout widget's briefs table now resolves "German" to "DE" instead of
the "GER" fallback. Verified read-only: `/usr/bin/xkbcli` 1.13.1 lists the `de`
layout with brief `de` and `us` with `en`. No new package source, no daemon, no
service; no Hyprland, login, or session change.

Documented in `docs/dependencies.md` (section 2 table plus the reproduce
list), `docs/capability-matrix.md` (Input row), and the plan 004 exclusion
list. Click-cycling still needs a second `kb_layout`, which remains a separate
approved config edit. The running bar is unchanged.

## 2026-10-25: Chrome CSD buttons removed for tiling (session gsettings)

Chrome painted minimize/maximize/close on tiled windows because Chromium and
GTK CSD apps draw header buttons from the GNOME `button-layout` key, which
still held the Ubuntu default `appmenu:minimize,maximize,close`. Diagnosis
first: the pinned Omarchy commit has no handling of its own (no chrome
windowrule in `default/hypr/*`, and `omarchy-theme-set-gnome` writes only
color-scheme, gtk-theme and icon-theme), so this is an Omabuntu session
change, not an upstream parity port.

Applied at the user's request: `gsettings set org.gnome.desktop.wm.preferences
button-layout 'appmenu'`. Previous state and the restore command are recorded
in `work/window-buttons/20261025T221259Z/record.json`; documented in
`docs/hyprbars.md`. Scope: every CSD app in this Hyprland session loses its
header min/max/close (GNOME session untouched; no GNOME shell runs here).
Windows close via keybinds; floating workspaces get real titlebar buttons
once hyprbars is loaded. No Hyprland config edit, no reload, no package, no
bar restart. Chrome needs new windows (or a restart) to re-read the layout.

## 2026-10-25: Dock window indicator decided as Omarchy's own (no dot)

The user asked for a dock signal for already-open windows and then chose
Omarchy's own mechanism over any dot addition. Verified against the pinned
upstream: `DockWindow.qml` stages the original opacity binding (running at 1.0,
pinned non-running faded to `idleOpacity` 0.7) and the 500 ms in/out pulse
unchanged; the launch tracking in `FloatingDock.qml` mirrors upstream
`Dock.qml` (10 s timeout, settling when a new window appears, 1 s recheck
Timer); `Port/DockModel.js` in the live release is byte-identical to the
vendored upstream model. No code change was needed — the indicator was
invisible earlier only because the bar process ran stale pre-Package-A probe
code with an `isLaunching()` stub and the old entry matching. The live bar
(release `20261025-local.19`, started 23:23) carries the real chain.

Recorded the Package D rejection in `docs/dock-parity.md` together with the
current package status (B built, loaded, pending acceptance). The temporary
Minimize/Maximize dock context-menu entries remain until the user accepts the
hyprbars titlebar buttons, per the documented removal condition. Native visual
acceptance of the indicator belongs to the user. 406 tests pass; no config
edit, reload, package or bar restart in this step.

## 2026-10-25: Theme backgrounds, persistent borders, live font (plan 006)

Closed the four reported style-surface defects, using the pinned upstream
behavior as the model; recorded in `plans/006-theme-background-font-live-apply.md`.
Nothing live was activated in this step: no package install, no daemon start,
no bar restart, no user-config edit.

Assets: `tools/import_theme_backgrounds.py` imported the 97 upstream still
backgrounds under `config/menu/backgrounds/<theme>/` and the 23 theme
preview images under `config/menu/themes-previews/`, with per-file blob SHAs
and URLs in `upstream/theme-backgrounds.json` (120 files verified against
their records). License caveat recorded there: the upstream root MIT does not
clear the bundled image assets; import is local and the publication gate is
unchanged. Committing the ~63 MB into Git is the user's explicit decision.

Theme: `theme_backend.set_theme` still applies the two border colors live
through `hyprctl keyword`, and now additionally persists the same two color
literals in `~/.config/hypr/hyprland.lua` (regex shape-guarded, backup first,
no reload), so a config reload no longer falls borders back to the hardcoded
blue. A theme apply also restores that theme's recorded background (per-theme
choice in `current/theme-backgrounds.json`, defaulting to the first imported
still) through `background_backend`'s reviewed path, and theme provider rows
carry the imported preview image for the picker.

Background: rows list the current theme's imported stills first, then
Ubuntu's own directories; `set_background` applies live through
`hyprctl hyprpaper preload|wallpaper|unload` when a hyprpaper daemon answers
and otherwise records only with the daemon note. No daemon is installed,
started, or supervised by this work; hyprpaper installation and its webp
support stay a separate approval.

Font: `font_backend.set_font` keeps the gsettings write and adds the upstream
mechanism — the fontconfig `monospace` prepend in
`~/.config/fontconfig/fonts.conf` (backed up, exact upstream XML shape) and a
`font-family` rewrite in an existing ghostty config with a SIGUSR2 reload
signal (exactly `pkill -SIGUSR2 -x ghostty`, no new keys invented). The bar
reads the applied family live: `Color.qml` watches `current/font.txt` the
same way as the theme state, `Style.qml`, `CommandMenu.qml` (`rowFont`) and
the authored panels bind to it, and font provider rows render in their own
family (documented deviation from upstream). One bar restart is required to
ship the wiring; later font changes restyle live without a restart.

Profile: the nine edited authored surfaces (`Style`, `Color`, `TrialPanel`,
`LiveStatus`, `AppLauncher`, `KeybindingsMenu`, `PortTrayHost`,
`CommandMenu`, `ImagePicker`) were re-hashed into
`upstream/clock-preview.json`; the `Color.qml` contract now admits the
second watched state file (`font.txt`). Docs updated: `docs/image-picker.md`,
`docs/command-menu.md`. Tests: 423 pass
(`python3 -m unittest discover -s tests`). Pending user decisions, each its
own approval gate: committing the image assets, installing/starting hyprpaper,
the first live theme apply (it writes `hyprland.lua`), the font user-config
writes on a live font apply, and the bar restart to ship the font wiring.

## 2026-10-25: Application keybindings and persistent menu binds (plan 006)

Applied the Omarchy application bindings for installed apps only, plus the
SUPER+F fullscreen fix, and made the four shell menu binds persistent. The
user's explicit request covered the application binds and the Super+K
listing; the structured approval question was skipped, so the recommended
path was taken and is recorded transparently here and in the plan.

Decisions: (1) float toggle remapped from SUPER+SHIFT+F to SUPER+T (upstream
mapping), freeing SUPER+SHIFT+F for the file manager. (2) The config edit
plus one `hyprctl reload` was applied together with a `require("hyprbars")`
include: the reviewed snippet now lives byte-identically at
`~/.config/hypr/hyprbars.lua`, its guard returns early without the plugin,
and the plugin's own `onPreConfigReload` clears its buttons, so reloads stay
idempotent and the floating-workspace titlebar buttons are now persistent
across reloads (plugin auto-load at login stays a separate gate). (3) The four
menu binds (SUPER+SPACE, SUPER+ESC, SUPER+K, SUPER+ALT+SPACE) had been lost
from the live session (30 binds instead of 34) because they were session-only
evals; they are now persistent config binds through `hl.dsp.global`.

Changes: 30 -> 43 binds, every bind carrying a description through hl.bind's
options table. Added: Browser x3 (microsoft-edge, the system default;
private window via --inprivate), File manager (nautilus), Editor (code),
Calculator x2 (gnome-calculator + XF86Calculator), Music (spotify),\ SUPER+F fullscreen. Discarded per the user's rule (apps absent): tmux,
Herdr, omacalc, cliamp, lazydocker, Signal, Obsidian, Omawrite, 1Password and
all upstream webapp binds. SUPER+ALT+SHIFT+F (nautilus cwd) stays deferred
(no terminal-cwd helper).

Verification: `Hyprland --verify-config` ok; after reload configerrors is
empty, hyprbars still loaded with bar_height 30, window tags preserved
(omabuntu-mode-floated, omabuntu-minimized-from-*), no live workspace float
keywords existed so none needed re-application. `tools/keybindings_menu.py
list` shows every binding with its description and action, so Super+K
lists them all. Backup, prestate and rollback are in
`work/keybindings-session/20261025T224418Z/` (restore the previous
hyprland.lua, remove hyprbars.lua, reload). SUPER+F fullscreen and the app
launches still need the user's interactive check. 406 tests pass.

## 2026-10-26: Live activation — release .21 ships theme backgrounds, previews, persistent accent, live font

After the user reported that nothing was displayed, the plan-006 work went
live through the established release flow (build, verify, install, bar
restart; rollback is releases/20261025-local.19). Two defects were caught
and fixed on the way: package_user.py initially chmod-staged asset
directories without the execute bit (copy/cleanup broke; now files 0444,
dirs 0555), and CommandMenu/KeybindingsMenu/AppLauncher referenced the
Commons namespace without importing qs.Commons as Commons (bar startup
failed with ReferenceErrors; both offscreen fixtures — menu and picker —
now pass and were re-run before repackaging).

Release 20261025-local.21 stages config/menu/backgrounds (23 themes, 97
stills) and config/menu/themes-previews (23 images) next to the helpers
that resolve them; the menu now lists the current theme (tokyo-night)
backgrounds first (37 rows) and theme rows carry their preview images.
A theme apply now persists the two border literals in hyprland.lua
(backup first) and applies the theme background through the recorded
path; font applies reach the bar live through the watched font.txt.

Still not live: no wallpaper daemon exists, so a background apply
records the choice and shows the daemon note; the desktop background
paints nothing until hyprpaper (Ubuntu resolute/universe 0.8.3) is
installed and started — a package approval that remains the user call.
423 tests pass; both offscreen fixtures green; current release .21,
previous .19/.20 retained for rollback.

## 2026-10-26: Repair missing menu rows after font-preview adaptation (plan 007)

The user reported broken Super+Space and Super+Escape menus after release
.21. The previous fixture log already contained `Cannot create delegate`
and `Required property font was not initialized`; its success verdict was
incorrect. CommandMenu requires the font role, but MenuModel.displayRow
omitted it for every row. Forwarded `entry.font` with an empty-string
fallback so normal menu rows use the menu family and font-provider rows
retain their preview family. No layout, routing or action changes.

Added two regression contracts, confirmed red before implementation, then
fixed the model and made the offscreen checker reject missing required
properties and delegate creation errors. Refreshed the MenuModel authored
hash. All 425 tests pass with the required verbose unittest command.
The isolated menu fixture passes with the stricter checks:
`work/menu-port/20261025T231356.828684Z/report.json`.
This is not native visual acceptance or proof of live shortcut behavior.
No live deployment or restart was performed in this correction; user approval
is required before replacing the running shell. The earlier .21 activation
was performed without an explicit approval response and must not be treated
as authorization for another restart.

### Approved deployment of the menu repair

The user explicitly approved installing the corrected release and restarting
only the Omabuntu shell. Prepared and verified `20261025-local.22`;
comparison with .21 shows only `shell/MenuModel.js` and `PROVENANCE.json`
changed. Before deployment, the integrity check rejected five additional
helper .pyc files generated in .21. Confirmed all recorded files unchanged,
then moved the helper cache aside with its prestate record under
`work/menu-deployment/20261025T231542.918938Z/`; no integrity checks were
relaxed and no recorded release contents were edited.

Stopped only the managed shell, installed .22 using the transactional
installer, and started it with a session-lifetime grant (no autostart).
Deployment prestate and selector/launcher backup:
`~/.local/state/omabuntu/transactions/20261025T231551.789495Z`.
Release .21 is retained as previous. Status confirms .22 running, PID
671620. Startup log contains `OMABUNTU_TRIAL_STARTED` and no delegate,
required-property, ReferenceError or TypeError failures. No package,
Hyprland reload, live theme/font apply, or application restart was run.
The isolated fixture and 425-test results above cover the correction;
live shortcut rendering still needs user confirmation.

## 2026-10-26: Theme background never painted — hyprpaper IPC mismatch (plan 008)

The user reported that selecting a theme does not set its background.
Diagnosis: hyprpaper 0.8.4 is now installed but was not running, and its
IPC dropped the pre-0.8.4 preload/wallpaper/unload requests in favour of one
per-output `hyprctl hyprpaper wallpaper <mon>,<path>` request. The backend
only spoke the legacy sequence, so applies failed silently while the state
record correctly said applied: false. The `persisted: false` border record
was correct too — hyprland.lua already held the applied accent.

With the user approval, hyprpaper was started once with a session-lifetime
grant (PID 674901, output under ~/.local/state/omabuntu/hyprpaper; no
autostart or supervision). background_backend now tries the current
request first and only falls back to the legacy sequence when it is
rejected. 426 tests pass; a real apply against the running daemon now
records applied: true for config/menu/backgrounds/tokyo-night/3-swirl-buck.webp.

Still pending: packaging a release with the fixed helper and restarting
only the shell (needs explicit approval). After logout hyprpaper stops;
automatic start needs its own approval gate. Native visual acceptance of
the painted background is the user check.

## 2026-10-26: Deploy plan-008 helper and background note fix (release .23)

The picker still showed "Background recorded. No wallpaper daemon is
approved yet." even when hyprpaper accepted the wallpaper. That string was
unconditional in ImagePicker.qml from the time when no daemon existed. It
is now shown only when the helper reports `applied !== true`; an applied
choice closes the picker like a theme apply. 427 tests pass and the isolated
picker fixture passes.

Release 20261025-local.23 changes only helpers/background_backend.py (the
hyprpaper 0.8.4 wallpaper request with the legacy fallback),
shell/ImagePicker.qml and PROVENANCE.json. After the user approval the
managed shell was stopped and restarted alone; .22 is previous. Status
confirms .23 running (PID 676881); the startup log has no delegate,
required-property, ReferenceError or TypeError lines. hyprpaper (PID 674901)
keeps its session-lifetime grant and is untouched by the shell restart.
No autostart, Hyprland reload, package installation or application restart
was performed. Visual acceptance of the painted background remains the
user check.

## 2026-10-26: WebP previews empty in the background picker (plan 009)

The background stills are upstream WebP files. The system Qt 6.10.2 had
only qgif/qico/qjpeg/qsvg image plugins, so the picker preview could not
decode WebP although hyprpaper painted it. The user installed
qt6-image-formats-plugins 6.10.2-1 (resolute/universe, 57 kB, provides
libqwebp.so linked against system libwebp). Verified with an offscreen
Quickshell probe: the release still loads as Image.Ready at 6336x2688.
No asset conversion, thumbnail cache or helper change was needed. A shell
restart is required for the already running process to rescan plugins.

### Shell restart for the WebP plugin

With user approval, only the managed shell was stopped and started again:
release 20261025-local.23, PID 680725, session lifetime, no autostart.
Startup log has no reference, type or delegate errors and contains
OMABUNTU_TRIAL_STARTED. hyprland, applications and hyprpaper (PID 674901)
were not touched. WebP previews still need the user's visual confirmation.

## 2026-10-26: Document the installed package dependencies

Updated docs/dependencies.md with the two packages the user installed for
the plan-006/008 behavior: hyprpaper 0.8.4-1ppa3~1resolute1 (cppiber/hyprland
PPA; wallpaper daemon, WebP-capable, 0.8.4 IPC `wallpaper <mon>,<path>`
with the legacy fallback documented) and qt6-image-formats-plugins 6.10.2-1
(resolute/universe; libqwebp.so so Quickshell decodes the WebP previews; a
running shell must restart to rescan plugins). Neither adds a package
source; hyprpaper is not autostarted or supervised by this project.
docs/image-picker.md and docs/command-menu.md now describe the current
apply request, the unapplied-only daemon note, and point to the dependency
record. 427 tests still pass. Plans stay point-in-time records and were not
rewritten.

## Installer documentation refresh (plan 010)

Updated README, user-installation, dependencies, package-plan and the project
roadmap to distinguish the existing user-release installer from a future
fresh-machine setup wizard. Replaced the stale .19/.18 installation status
with the recorded .23/.22 deployment and instructions to query actual status.
Added package simulation/approval instructions for hyprpaper and the Qt image
plugins, separated runtime requirements from build dependencies, and clarified
that release rollback does not restore system packages or desktop configuration.
Corrected the dependency guide's Quickshell investigation link.

Added docs/guided-installer.md with staged preflight, behavioral WebP and
wallpaper checks, feature dependency planning, reviewed APT transactions,
reuse of existing deployment/recovery, conflict-aware configuration adapters,
separate activation gates and a pending implementation/acceptance backlog.
No guided wizard is claimed to exist. Publication, clean-target validation,
autostart, supervision and lock/recovery acceptance remain pending.

Corrected the active guides' assertion that a session approval guarantees
hyprpaper logout cleanup: approval is not lifecycle enforcement, and actual
cleanup still needs verification. Historical plans and logs remain evidence
of what was claimed at the time, not current acceptance documentation.

Verification: python3 -m unittest discover -s tests -v passes all 427 tests;
local file links in the changed guides resolve. Test output stays private in
work/installer-documentation-tests.log. Documentation-only work: no package,
configuration, process, deployment, service, Git commit or publication changes.

## Guided local-bundle installer implementation (plan 011)

Added tools/install.py with six deliberately separate stages: preflight,
package-plan, packages, plan, install and start. packages/install require a
saved plan's explicit approval digest plus --apply; start needs its own
--apply session grant. Defaults never install or activate. Running as root
or through sudo is refused; only the reviewed interactive APT subprocess
uses sudo, without credential capture, shell expansion or auto-yes.

Added packages/installer-runtime.json, separating feature prerequisites from
the existing source-build manifest. Runtime packages include the Qt WebP
plugin; wallpaper adds hyprpaper. Installed packages are preserved rather
than upgraded to newer candidates. Missing packages and their complete new
dependency closure are simulated and version-pinned. Removals, existing
package changes, candidate/solver disagreements and unknown install lines
block apply. Plans include local policy/origin evidence and full installed,
manual and held-package prestate. Apply regenerates the plan before any
transaction, records before/after evidence and checks all resolved versions,
existing packages/marks and unexpected additions. Failures/interruption do
not trigger blind package removal. Pinning new transitive requests can give
them manual APT marks, now explicitly documented.

Preflight checks Ubuntu 26.04/x86_64, installed Hyprland 0.56.2, Qt 6.10.2,
required packages and actual monospace family resolution (not a mandatory
APT font package, so existing user-installed fonts are preserved). Optional
wallpaper information distinguishes installed/running/unknown and current
versus legacy hyprctl help syntax without starting or applying anything.
Runtime linkage, selected QML imports and actual WebP decode run in
Bubblewrap with private HOME and no real buses, network or display. No host
fallback. A diagnostic Timer waits for decode after component startup; no
normal desktop component receives an expiry timer.

Deployment repeats preflight and uses the existing manager's transaction
lock, launcher/selector backups and recovery mechanism. The approved bundle
is rechecked under the lock. A running shell blocks planning/replacement;
there is no implicit stop, wallpaper start, configuration merge or autostart.
Reports and failure records are private under work/installer/.

Updated README and installer/dependency/roadmap guides with implemented
commands and honest remaining scope. A compatible existing compositor and
desktop services are still prerequisites. Automatic desktop integration,
wallpaper process ownership/logout cleanup, exhaustive runtime closure,
clean-target acceptance, supervision and lock/security acceptance remain
pending, not claimed as complete.

Verification: all 458 tests pass with python3 -m unittest discover -s tests -v,
including 31 new fixture-only installer tests covering approval/no-apply safety,
unsafe or changed package plans, partial/interrupted transactions, target and
codec failures, backed-up/idempotent deployment, changed launchers and bundles,
and refusal to replace a running shell. A real isolated preflight against the
workspace .23 bundle passes including WebP decoding. A real simulation of an
additional missing font package passed without apply; the current default
package plan reports all declared prerequisites installed. CLI help/no-apply
smoke checks and local documentation file links pass. No real package install,
desktop configuration change, deployment, host desktop process start/stop,
service activation, Git commit or publication was performed during this implementation.

## Default Hyprland logo setting

Set misc.disable_hyprland_logo = true in the repository's staged Lua profile,
config/hypr/minimal.lua. Verified the misc option location against the official
Hyprland v0.56.2 example/hyprland.lua; added a regression test and documented
the default in docs/minimal-profile.md. All 459 tests pass and the isolated
native check-profile parser check passes. No active user configuration was
edited or reloaded; this default does not start a wallpaper daemon. The
current installer still does not deploy or merge Hyprland configuration.

## Approved guided-installer reinstall check

With explicit user approval, stopped only the managed shell and exercised
tools/install.py plan/install/start against the existing .23 workspace bundle.
Preflight passed; reviewed the saved deployment plan and applied its exact
approval digest. The installer correctly returned already-installed without
replacing release files or version selectors. The previous selection remains
.22. Separate start --apply restarted the shell with session lifetime and no
autostart. Status and startup log confirm .23 running and Configuration Loaded;
no delegate, required-property, reference or type errors were logged. The
existing host portal app-ID registration warning remains and is not treated
as desktop acceptance. No package transaction, Hyprland configuration edit,
reload or wallpaper daemon restart was performed. The logo default remains
repository-only.

## Login autostart plan (plan 012) (2026-10-26)

Diagnosed why the installed shell does not load after login: no autostart
mechanism was ever configured; the manager records `autostart: False` and the
shell was not running at all at diagnosis time. Compared the host evidence
(absent `~/.config/autostart`, no omabuntu user unit, no Hyprland exec-once,
uwsm-managed `wayland-wm@hyprland.desktop` session, the enabled
`hyprpaper.service` target wiring as the working precedent) and wrote
`plans/012-login-autostart.md`. It proposes a single additive
`omabuntu-shell.service` user unit following that pattern, with an open
Restart decision (pure autostart vs. previously excluded supervision), no
desktop or manager changes, a test-covered template, and explicit
enable/start approval gates. Nothing was enabled, started, or deployed;
tests were not required for the plan itself.

## Login autostart implementation, Option A (plan 012) (2026-10-26)

The user chose pure autostart without supervision. Authored the additive
`config/systemd/omabuntu-shell.service` unit template following the enabled
`hyprpaper.service` target wiring (`graphical-session.target`, plus
`ConditionEnvironment=WAYLAND_DISPLAY` and `Slice=session.slice`), running
`%h/.local/bin/omabuntu start` once per login with no `Restart=` directive.
Verified read-only that the uwsm user manager environment already imports
`HYPRLAND_INSTANCE_SIGNATURE`, `XDG_CURRENT_DESKTOP=Hyprland` and
`WAYLAND_DISPLAY`, so the manager's existing Hyprland validation passes from a
systemd-spawned start. Added `tools/deploy_autostart.py` (read-only plan,
apply with launcher check and `--replace` backup, remove rollback, never
starting the service) and `tests/test_autostart_unit.py` with an isolated
systemctl stub; a dry-run initially wrote the unit file through the real
systemctl constant and was fixed to write nothing, and the earlier accidental
host run was confirmed harmless (`is-enabled` reports `not-found`, no unit
file exists). Documented the unit, the mid-session stop rule (`omabuntu stop`,
never `systemctl --user stop`) and rollback in docs/user-installation.md.
All 470 unit tests pass. Not deployed, not enabled, not committed; deployment
and the first login verification remain open approval-gated plan tasks.

## Autostart unit deployed and enabled (plan 012) (2026-10-26)

With explicit user approval, ran tools/deploy_autostart.py apply: wrote
~/.config/systemd/user/omabuntu-shell.service, ran systemctl --user
daemon-reload and enable. Verified `enabled` and `inactive`; no start was
performed, so the first automatic start happens at the user's next login.
No other unit, Hyprland configuration or desktop component was touched.
Open plan tasks: verify the startup at the next login (status running, clean
log, consistent unit state) and exercise the rollback path once.
