# Expand original-shell fidelity across areas A through E

## Goal and evidence

Implement the owner's requested expansion of the original-shell feature areas:
A shared frame/theme/layout ownership, B audio completeness, C Bluetooth,
D durable display configuration and E optional integrations. Preserve original
components with narrow reviewed Ubuntu adapters, not replacement panels.
Compare against Omarchy v4.5.0 commit
ac2690cd7be4f47e4a255f5e2e78d904d436b068 and the project's sealed component
parents. Quickshell is pinned to 2b4501a282689792b62e94f3fb30d8f512324fe6;
configuration remains targeted at Hyprland 0.57.0 and Qt 6.10.2.

## Current gaps and proposed sequence

These areas are multiple substantial integrations, not one appearance switch.
The selected host already has working original component surfaces. Start with
a contained source-only slice: restore the original audio per-application stream
section and row, add immutable provider projections and identity-checked native
PipeWire actions, and extend original cursor/drag behavior with fake-node tests.
The first slice uses existing licensed vendor parents without fetching or
modifying upstream inputs. A subsequent shared-layout slice imports the pure
BarModel.js only after complete source/license review, matching the pinned Git
tree blob and recording provenance; original parents remain unchanged.

Keep the other requested areas explicit rather than pretending a stream section
completes A–E. Shared layout ownership requires a source-based registry/theme
review. Bluetooth pairing-agent ownership and persistent radio/audio policy need
an Ubuntu-specific design. Durable display configuration needs version-reviewed,
conflict-aware plan/backup/apply/recovery. Optional input methods, agents,
dictation, live wallpaper and energy policy each have independent dependencies,
licenses and ownership; they cannot be enabled by loading the entire source shell.
Later slices of this same request remain tracked here, not in duplicate plans.

## Shared layout slice: reviewed design

Continue A by replacing the frame's five opaque grouped Component loaders with
original keyed WidgetPool/WidgetHost borrowing semantics and original section
geometry. Use the unchanged pure BarModel.js at the stable pin (Git blob
8d3c9d6eaadc9c75f4f76d0a4a6f5faca46823a7, SHA-256
9394b2ca8256518bbe04a8b11f4b740e20c2d9c0859372eda475dc33200471b8).
Its MIT notice matches vendor/omarchy/LICENSE. It has no native/service imports
or command execution. Admission stays closed to the existing trusted widget
Components; custom URLs, command modules and arbitrary plugin loading are not
exposed through its otherwise broader pure-model helpers.

Store a validated five-section widget order in the existing Appearance
transaction store, retaining unrelated preferences and exact rollback. Share
confirmed/pending layout state across outputs; use original layout-order panel
navigation instead of a hardcoded panel-group order. Keep existing widget state
and instances while moving between sections. Preserve current top-horizontal
geometry and defaults. Pointer drag/ghost/removal UI, vertical/notch policies and
complete original theme/service ownership remain later work, not implied by a
registry/persistence foundation. Test move identity, independent output pools,
load failure, rollback and empty/hidden sections without a live desktop.

## Conditional layout-edit slice: reviewed design

Before admitting the original pointer/ghost/removal surfaces, close the existing
asynchronous write gap. Original Bar.qml landBarDrag/writeLayout checks the
captured keyed layout; BarModel.moveEntry/removeEntry also checks source region,
index and widget ID. A blind asynchronous full-layout write cannot preserve that
contract when another writer changes state before the helper takes its lock.

Expose the unchanged original model operations through the existing frame with
an optional shared Appearance editor. Submit detached expected/new five-section
layouts through a closed conditional-edit key. Recheck semantic layout equality
inside the existing preference lock, preserve unrelated settings and retain
exact transactional rollback. Reject stale/no-op edits without creating a state
file; this is cooperating-writer conflict protection, not a claim to prevent an
uncooperative external write racing after the locked check or an ABA revision.

The shared adapter must project only matching conditional edits, drop dependent
edits after failure, refresh unknown results read-only, retain unrelated queued
clock/tray changes, and surface conflicts. Verify original model identity/no-op
rules, deferred/helper conflicts, concurrent writers, failed receipts, queue
recovery and output-local instance preservation in contained tests. Pointer hit
routing, native ghost surfaces, poof feedback and live drag/removal activation
remain explicitly outside this prerequisite slice.

## Original pointer/ghost slice: reviewed design

Restore original ModuleSlot pointer routing, open-panel marks, center/room/drop
outlines, keyed drag spacers, capture/settle/poof visuals and their original
thresholds/timings from the unchanged stable Bar.qml. Reuse its pure model and
route its layout write seam through the existing expected-layout transaction
adapter. Capture detached source layouts at gesture start; reject drift rather
than retargeting a later order. Keep per-output identity and closed admission.
Add an explicit Appearance/Menu Bar restore-default-layout action through the
existing transaction backend so removed widgets remain recoverable from the
independent command-menu shortcut; preserve all unrelated preferences. This is
an Ubuntu recovery seam, not a new replacement settings panel.
The tray's nested section, bar edge-moving gestures, arbitrary plugins and full
theme-service startup remain excluded, not substituted with replacement panels.

Use the original full-screen transparent surface/input-strip policy: reserve
only 26 logical pixels with an explicit exclusive zone, pass input outside the
strip while idle, and retain input during a drag. Park the entire surface when
hidden. Ghost feedback is an original visual-only overlay with an empty input
mask and no keyboard focus. Review against the pinned Quickshell official
PanelWindow/window-mask API documentation in its source headers; no Hyprland
configuration edit is needed. This source change is not live activation.

Contained fixtures must substitute only layer ownership, never connect host
services, inject host pointer events or execute a preference helper. Exercise
the actual original pointer-handler bodies through named testable functions,
including click/held feedback, threshold, cancellation, empty regions, drift,
removal distance, settle and per-output isolation. Native compositor grab,
focus, fractional-scale/pixel and hotplug acceptance still require separate
approved deployment/testing. Do not claim remaining A–E complete.

## Safety and exclusions

This request authorizes repository implementation, not package installation,
new sources, privileged operations, live desktop edits, reloads, service/session
activation, radio/trust changes, lock/idle/suspend activation or publication.
Preserve GNOME, login, VPN, certificates, keyring and corporate agents. No boot,
kernel, PAM, sudo, firewall, security-policy or management changes. Never invoke
Arch helpers or expose the source bin directory. Do not request credentials.
Back up each affected repository path with prior existence, hash and mode under
ignored work/. Preserve the uncommitted plan-133 documentation changes.

No automatic stream volume/mute writes, playback, recording or native PipeWire
connection in tests. Capture streams and the shell's own streams are excluded
from the playback-stream controls. Re-resolve type and stable identity before
each mutation; reject removed, unready and reused nodes. Native visual/audio
acceptance and deployment require separate approval. Do not claim all A–E done
when only a bounded slice has been implemented. No commit without approval.

## Tasks

- [ ] Inventory existing original-source seams and native API contracts for A–E.
- [x] Back up and implement the original per-application audio stream slice.
- [x] Verify source fidelity, identity/drag/churn guards and isolated UI behavior.
- [ ] Implement the remaining B audio functions after their native API review.
- [ ] Implement A shared source-based frame/theme/layout ownership.
  - [x] Review/license/verify and import unchanged pure BarModel.js.
  - [x] Restore original keyed pool/slot ownership behind a closed Component map.
  - [x] Add shared transactional five-section layout state and per-output owners.
  - [x] Verify stable moves, removal, layout-order navigation and output-local pools.
  - [x] Add conditional layout edits and original model move/remove entry points.
  - [x] Verify stale-write rejection and shared pending-edit failure recovery.
  - [x] Restore reviewed original widget pointer/ghost/removal source and recovery action.
  - [ ] Restore remaining theme/service owners and separately review unported layout variants.
- [x] Implement C reviewed Bluetooth ownership/error (Plan 158 source complete;
  optional trust/radio/routing/profile policies explicitly excluded, deployment
  and native authentication acceptance remain separate unperformed gates).
- [x] Implement D reversible persistent display configuration (Plan 160 source
  complete; Plan 161 locally installed with automation off and layout unchanged;
  native display/login/hotplug/recovery acceptance remains separate and pending).
- [ ] Implement the agreed E optional integrations after dependency/license review.
- [x] Update provenance/docs and run complete unit and clean-source checks.

## First source-only slice outcome

The original audio per-application section and StreamRow are now derived from
the existing unchanged MIT parent via audio-streams-frontend-v2. Playback streams
have a separate tracker and frozen primitive state; actions and drags require
matching ID, name and bound object serial. Per-stream volume/mute and cursor
navigation are present, with the original explicit 0..150% stream gain range.
Device gain remains limited to 100% and no microphone master-mute change was made.

All twelve isolated audio cases passed, including four stream cases and the
negative control. The new disappearance case also exposed a stale visible-section
cursor dependency; clamping now observes section-list changes. All 1,338 unit
tests, clean-source export and the isolated desktop regression passed. Source
seals, generated mirror, unchanged vendor parents and private backup hashes were
verified. Native PipeWire, pointer/focus, sound and deployment acceptance are not
claimed. Failed diagnostic attempts are retained alongside the passing report.

The inventory/review across all A–E is still in progress. A shared host ownership,
C Bluetooth agent/policy integration, D persistent monitor configuration, E
optional services and the rest of B are not implemented by this slice. In
particular, device profiles, virtual-source helpers, physical-sink mapping,
active-player/media transport, OSD and two-channel master mute remain absent.
The original Bar.qml expects injected shell/plugin/layout ownership, the current
Bluetooth adapter delegates pairing to an existing agent, and the display backend
is deliberately runtime-only. Those contracts need their own source/API review
before extension; the full upstream startup must not be used as a shortcut.

The running desktop, private configuration and selected immutable release are
unchanged. No package/service operation, reload, restart, recording/playback,
commit or publication was performed. Prior plan-133 documentation edits remain
preserved and uncommitted. The whole A–E request is not complete.

## Second source-only slice: shared bar/layout foundation

The unchanged stable BarModel.js was read, checked against the pinned Git tree/
blob and MIT license, then imported with complete origin/hash records. The
frame derivation now retains original keyed WidgetPool ownership and bounded
WidgetHost/ModuleSlot borrowing. Only twelve trusted prebound Components are
admitted. No custom module URL, command component, arbitrary discovery or whole-
shell startup is enabled.

TrialPanel now gives the existing widgets one per-output bar API, including the
tray. Shared layout state is validated as exactly five section arrays of unique
known string IDs; inline settings/clones/paths/commands are rejected. Existing
Appearance transactions preserve unrelated state, exact prior bytes/mode or
absence, and refuse rollback after external drift. Shared pending projections
keep all outputs coherent; their original widget pools remain independent and
retain widget instances/state on moves. Panel navigation and popout handoff use
actual layout regions rather than fixed authored groups.

Fourteen isolated frame cases cover original widths/spacing, stable moves,
removal, empty layouts, missing Component admission, layout-order navigation,
separate output pools, real registry wiring
compilation with synthetic layer ownership, and the deliberate negative control.
Python/JS contracts cover validation, persistence, concurrent independent edits,
exact rollback, failed receipts, source seals and pending-response ordering.
Synthetic surface substitution is recorded in each fixture report; this is not
native layer, pointer, device-service, pixel or session acceptance.

Final validation passed: 1,354 unit tests, all fourteen frame and twelve audio
cases, tray/network/tooltip/clock and isolated desktop regressions, clean-source
export, source seals and private backup hash/mode verification. The new model is
the only added vendor file; existing vendor parents are unchanged. Failed
diagnostic attempts remain under ignored work/ and are not acceptance evidence.

The source foundation does not yet expose original pointer-drag/removal editing;
full theme/plugin service ownership and other A–E work remain outstanding. No
live layout, selected release, desktop file, package, service or session was
changed. No commit or publication was made.

## Third source-only slice: conditional layout editing

The unchanged original BarModel moveEntry/removeEntry operations are connected
through frame entry points to an optional shared editor. The new closed
bar-layout-edit payload carries expected/replacement five-section layouts;
semantic equality is checked again under the existing preference lock. Stale
and no-op preflight requests allocate no preference state, and unrelated field
edits are preserved. Exact rollback, failed receipt recovery and session gates
remain enforced. Two concurrent cooperating writers with the same expected
layout cannot both commit.

The actual shared QML adapter now projects only matching conditional chains,
drops dependent edits after a failed request, retains independent clock/tray
requests and refreshes unknown outcomes read-only without replaying writes.
Conflict notices survive subsequent unrelated success. Native offscreen tests
instantiate this adapter without starting its helper Process, and verify
original-model move/removal through a contained fake editor. Optimistic removal
can reconstruct widget state after a rejected write; file rollback does not
promise transient widget-state restoration. The guard is semantic and does not
claim ABA or uncooperative external-writer race prevention.

All 1,371 unit tests, sixteen isolated frame cases, twelve audio cases and the
tray/clock/desktop regressions passed, along with clean-source export. Source
seals, existing vendor parents and private prestate backups remain verified.
The expected conflict warning has a narrowly tested allowlist; other warnings
still fail the frame suite. No new vendor code was imported.

This remains a prerequisite, not the original mouse pointer/ghost/poof UI or
native drag/removal acceptance. Those surfaces, full theme ownership and the
rest of A–E remained outstanding at this checkpoint. No desktop/deployment/
service/session change, commit or publication was performed.

## Fourth source-only slice: original widget gestures and recovery

The v4 derivation now retains original ModuleSlot pointer handler bodies and
held/click routing, open-panel indicators, center/room/drop outlines, keyed
spacers, capture, landing and ghost/poof visuals. Original thresholds/timings are
unchanged. Wrapper/API, namespace, top-horizontal geometry and named handler
entry points are narrow documented adaptations. No custom module, nested tray
or bar-edge relocation path is admitted. Existing vendor parents are unchanged.

The original stable full-screen transparent surface policy now reserves only
26 logical pixels and passes idle input outside the strip. Active gestures keep
the full surface input region; hidden bars park the whole surface and cancel
active drag state. Official API documentation in the pinned Quickshell source
headers was checked for exclusion zones, anchors and input masks. Ghost overlays
are visual-only, focusless and input-empty. Animation timers do not expire any
normal desktop component. Nothing was applied to the running desktop.

Gesture start captures a detached source layout and a local slot. Landing and
removal retain original keyed identity checks and the expected-layout transaction
adapter. QML can expose distinct interfaces for one window, so the original
screen-identity equivalence is required rather than pointer identity alone.
An explicit Appearance/Menu Bar Restore Default Layout action recovers removed
widgets even from an empty layout through the independent command-menu shortcut.
It preserves unrelated preferences and exact transaction rollback/session gates.

All 1,382 unit tests and twenty-four isolated frame cases passed, including eight
original-handler gesture cases: click/threshold/held feedback, move/settle, empty
section, removal/poof, cancel, drift, rejected write and output isolation. Twelve
audio cases and tray/network/tooltip/clock/desktop regressions and clean-source
export passed. Private backup hashes/modes and source seals were verified.
Contained fixtures replace layer ownership, call actual original handler bodies
with synthetic data and never start a preference helper or inject host input.
They are not native input dispatch, compositor-grab, GPU/pixel, focus, scaling,
hotplug or session acceptance. Diagnostic failures remain private evidence, not
acceptance claims.

Full theme/service ownership, original fullscreen/peek and vertical/notch policy,
bar-edge relocation, nested tray layouts, remaining B audio, C Bluetooth, D
durable displays and E optional integrations are still outstanding. The whole
A–E request is not complete. No deployment, restart, package/service operation,
commit or publication was performed at this source checkpoint.

## Subsequent approved local installation

The separate user installation request is implemented in
[plan 135](135-local-original-shell-installation.md). It deploys the four completed
source slices and restarts only the owned session-lifetime bar. The source-only
outcomes above remain historical checkpoint records. Local release integrity,
startup, unchanged preferences and the independent recovery route were verified;
no new native interactive acceptance or completion of remaining A–E work is
claimed. No packages, services, autostart, wallpaper, GNOME settings or compositor
configuration were changed by that installation.
