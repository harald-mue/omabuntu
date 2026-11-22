# Audio output port and source fidelity

The first authored output popup was rejected as below Omarchy quality. Reusing
individual buttons and a slider was not sufficient. The current output frontend
is now **derived directly from original audio/Panel.qml**, not independently
laid out. This still is **not the complete original audio panel or shell**.

## Current local installation (plan 144)

Plan 144 deploys completed Plans 136–139 and 141–143 with verified startup,
release integrity, recovery actions and unchanged preferences. The original hero
switch/right-click now controls **both output and microphone**, unlike Plan 135.
Recognized loudness routes, microphone ownership and shared media selection are
installed; the optional media widget remains absent from the default layout.
Plan 140's manual pactl/profile backend is deliberately not shipped or invoked.
Only the owned session-lifetime bar restarted, without wallpaper restoration.
No audio/media/Bluetooth functional action was exercised, and native interactive/
hardware/policy/input/pixel/security acceptance remains open. Per-plan source-only
statements below describe the historical implementation requests, not the current
deployment; the backend in Plan 140 remains source-only.

## Source and rendering boundary

The original import used 03ff1eff3812933f7088484533784d2f63eaf19a; the current
sealed audio parent is Omarchy v4.5.0 at
ac2690cd7be4f47e4a255f5e2e78d904d436b068. The original
Model.js, PanelSlider.qml, Panel.qml, KeyboardPanel.qml, PanelKeyCatcher.qml,
CursorSurface.qml, ToggleSwitch.qml, PanelToolTip.qml, PanelSeparator.qml and
PanelSectionHeader.qml were fetched individually from the public repository,
matched against the pinned tree/reference bytes and reviewed before import.
Full MIT notices and per-file Git blobs/hashes remain enforced by
upstream/clock-preview.json. Vendor parents are unchanged.

The deterministic extraction in tools/audio_frontend.py requires unique exact
witnesses and an enforced derived-content hash. The generated frontend mirror
at config/shell/preview/AudioOutputView.qml must match the extraction exactly.
It is not a second editable layout. Tests check these source relationships:

- The complete original hero markup is byte-identical: speaker glyph, title,
  mood/status label, switch, tooltip, original typography and anchors.
- Output section markup/spacing is preserved, adding only drag-target identity
  capture. Device-row markup adds a name check alongside the original ID check.
- Original CursorSurface, ToggleSwitch, section header/separator, slider,
  tooltip and PanelKeyCatcher execute, rather than replacement controls.
- The original adaptive 380px keyboard panel, lazy content and scroll container
  are used. No panel subtree is instantiated until requested/opened.
- Passive style tokens now use upstream defaults for popup padding (14), control
  gap (8), control height (28), row spacing (10), title/display sizes (14/24),
  normal fill (0.04) and selected fill (0.18). This also corrects the shared
  controls. The whole original theme/frame is NOT yet integrated.

The retained source parent also includes helpers, IPC, file watching, OSD and
media-service wiring. Those execution paths are **not staged into the frontend**,
not merely hidden. Original microphone and playback-stream sections are now
staged through the narrow controller/provider boundary. Plan 137 separately
restores a shared, initially read-only extraction of original media selection and
primitive MPRIS labels/active marks. Plan 138 extends that owner with explicit,
generation-guarded transport for the optional original media widget, not the
audio panel. Album-art loading remains excluded.
Original Panel/PanelController startup and full registry remain excluded.

## Interaction and explicit deviations

- Left click opens the original audio layout. Plan 144 installs Plan 136's
  original **output and microphone** master mute for right-click and the hero
  switch; see its explicit scope below. Historical Plan 135 was output-only.
- Wheel adjusts 5 percentage points/notch with accumulated partial deltas.
- Device slider and keyboard adjustments are bounded to 0..100 percent; original
  stream sliders permit 0..150 percent. Neither silently unmutes. Existing
  amplified values are displayed honestly.
- Original keyboard signal handling reveals a shared cursor, navigates between
  hero/slider/device rows, adjusts the slider with Left/Right or h/l, activates
  with Enter/Space, mutes with m, and closes with Escape. Device-row horizontal
  movement does not unexpectedly alter global volume.
- Plan 114 subsequently added fixed-registry cross-panel Tab/Shift+Tab switching;
  the owner reports the existing panel navigation working under plan 133.
- Device clicks request preferredDefaultAudioSink; display uses actual default,
  not an optimistic selection. The server may reject unavailable devices.
- Graph presence is not jack availability. External availability helpers and
  comprehensive virtual-to-physical sink resolution remain narrower. Historical
  Plan 135 targeted the server default directly; Plan 139, installed by Plan 144, resolves
  recognized DSP routes as described below without changing routing policy.
- Typed input devices are now staged (plan 001): the upstream input section
  markup (separator, `audio.input` header, input slider, peak meter,
  SourceRow) is extracted with unique witnesses; source selection uses the
  native `Pipewire.preferredDefaultAudioSource`; input volume/mute go through
  `source.audio`; the peak meter is the native `PwNodePeakMonitor`, enabled
  only while the panel is open, exactly like upstream's opened gate. Keyboard
  cursor navigation covers the input section per the upstream section model.
- Untyped (virtual) sources remain excluded: upstream routes them through its
  process wrapper and a default-helper; neither is admitted. All capture
  devices on this machine are typed ALSA nodes (work/audio-input-diagnosis).
- Plan 134 adds the original per-app playback-stream section, installed locally
  through [plan 135](../plans/135-local-original-shell-installation.md);
  profiles, media transport and original OSD remain outside this slice.
  Plan 137 restores MPRIS labels/active-player marks in the source tree;
  Plan 138 adds the separate optional original media widget described below.
  No test sound is played. Plan 144 installs Plan 136's guarded two-channel
  master mute, replacing the historical output-only hero.
  Authored input errors mirror the output ones ("Input device is no longer
  available", "No audio input available").
- Title, output and mute labels use the pinned English catalog strings in the
  passive locale adapter. Mood labels use the same catalog strings. Authored
  errors are "Output device is no longer available" and "No audio output available".
- KeyboardPanel is staged with OnDemand only, **never Exclusive**, and unmaps
  immediately on logical close so a fade-out does not retain focus. Its original
  retained prime timer gates bar click forwarding only, not keyboard ownership.
  Hit testing delegates to the restricted owner, not the full Util singleton.
- The original other-output dismissal surfaces remain. The owner reports the
  existing everyday audio and multi-output focus/navigation checks working
  under plan 133; no exhaustive device/race/security acceptance is implied.

No native QObject reaches visual delegates: display rows contain frozen
primitives. Every write resolves the current graph by ID+name and requires a
ready non-stream audio sink. Removed/reused IDs with different names fail.
Dragging retains its starting target. Construction, state publication and popup
opening do not write audio state. This is not a general QML security sandbox.

## Original per-application stream slice (plan 134)

The original per-app section and StreamRow are derived from the already licensed
vendor parent initially by `audio-streams-frontend-v2`, not replaced by a new
panel. Plan 137 advances it to `audio-media-streams-frontend-v3` with original
MPRIS-aware labels and active-row visuals. Labels use the original AudioModel. Each row offers its own mute and 0..150% volume,
matching the original stream slider; device gain stays limited to 0..100%.
This stream checkpoint and historical Plan 135 left the header output-only.
Plan 144 now installs the subsequent two-channel master action from Plan 136.

The provider tracks playback audio streams separately before reading bound
properties. Capture streams, the shell's own stream and the upstream tuning
processor are excluded. Delegates get only frozen primitive snapshots. A stream
requires its PipeWire object serial in addition to ID/name; absent or changed
identity fails closed, including reuse of the same ID and application name.

Pointer dragging pins that identity and cannot transfer gain to a replacement
stream. Keyboard h/l adjusts only the selected stream, while m and Enter/Space
mute only that stream. Cursor clamping reacts to visible-section changes, so
removing the last stream returns navigation to a surviving section. Opening,
polling and closing the panel do not mutate volume or mute. No helper commands,
recording, test playback, microphone activation or persistence policy are added.

That stream checkpoint passed twelve isolated offscreen cases with fake nodes,
including four stream/identity/navigation/drag cases and the deliberate negative
control. They do not connect to host PipeWire/DBus or a compositor. The slice is
now installed locally through plan 135, with clean startup and verified release
integrity, but **native interactive acceptance remains open**. Prior owner
acceptance applies to the earlier controls, not automatically to this new slice. Broader A–E work
remains tracked in [plan 134](../plans/134-original-shell-a-to-e-expansion.md).

## Two-channel master action (plan 136, source only)

The original hero switch and right-click action now control output and microphone
together. Checked means either admitted channel is unmuted. If either is audible,
the explicit master action mutes both; only when both are muted does it unmute
both. The tooltip explicitly names output and microphone. Output/input row mute,
stream mute, wheel and volume sliders keep their existing local scope. Opening,
closing, projecting state and reading the graph never invoke master mute.

Both captured default keys include the bound PipeWire object serial. The provider
rechecks the current defaults, including absence, and resolves every requested
channel before either setter runs. A missing/unready/reused node, changed default,
missing serial or malformed key rejects the entire preflight. An untyped default
is not silently dropped from a two-channel action. Master mute does not change
selection, gain or playback-stream state. Native setters are not cross-channel
atomic: a setter exception reports uncertainty, with no automatic retry or
compensating unmute. No universal native mutation-success guarantee is claimed.

Four additional contained cases cover mixed/single/no-channel behavior, local row
actions, explicit unmute, serial reuse, malformed keys, default churn and partial
setter failure. Pure-JS tests execute the actual action implementation as well.
The new behavior is deployed by Plan 144, but not natively accepted.
Broader profiles/virtual routing/OSD remain open;
Plan 138 separately implements optional original media controls in source.

## Original media selection and stream presentation (plan 137, source only)

The unchanged MIT MediaModel.js and Service.qml parents were verified against the
same pinned Git tree/blob identities before import. A closed derivation keeps
the original selection/order functions and reactive player-set/isPlaying
observers. At that checkpoint it omitted transport, source transfer, volume keys,
IPC, OSD and command helpers; Plan 138's explicit extension is described below. Selection is one shared Commons singleton, not per-output history, with
its own tracker for strictly admitted playback nodes before property reads.

Original selection rules remain: a playing preference, oldest real playing source
with a matching stream, oldest real playing source, proxy fallback, then the
original idle/shown-track/preference rules. No automatic play/pause or preference
file write occurs. A frozen whitelist of primitive player metadata reaches the
audio provider. Native players, methods, raw metadata and art URLs do not reach
visual delegates. No artwork is downloaded or decoded.

The original AudioModel now receives that projection for streamLabel and
streamRepresentsPlayer. StreamRow retains its original active-state visuals,
with only a primitive active flag crossing the backend boundary. Generic
"audio-src" labeling retains the original ambiguity rules rather than guessing a
player. Matching is presentation-only, not a process identity or security proof.
Playback-stream mutations still require their separate ID/name/object-serial key.

That checkpoint's twenty contained audio cases include four media cases: reactive play order,
proxy/idle/preferred fallbacks, unique/ambiguous generic labels, original active
row wiring, metadata/player/stream churn, and two actual provider instances
observing the same singleton. Only native MPRIS/PipeWire services are substituted;
original selection and UI execute without host buses. Pure-JS checks enforce the
frozen primitive whitelist. Native media/visual acceptance and installation remain
separate. Profiles, virtual-source/sink mapping and OSD remain open; the following
source-only slice adds explicit transport, not native playback acceptance.

## Original optional media controls (plan 138, source only)

The original 12,247-byte MIT media BarWidget.qml is now imported unchanged after
rechecking the pinned tree/blob, SHA-256 and preserved full license. Its extraction
keeps the original glyph/scrolling title, metadata layout, 320px adaptive popup,
transport buttons and source list. Narrow adaptations bind the shared service,
project immutable data instead of native players, require target keys, remove the
artwork loader, add guarded error text and close on last-player/bar disappearance.
The music fallback glyph remains; no local/remote artwork path is loaded. The
passive icon-large style token is the original default of 18 pixels.

Original action meanings remain: left click play/pause, middle click next,
right click popup, wheel up previous/down next. Popup buttons retain original
native dispatch conditions/calls, including the advertised toggle fallback.
Targets are captured when an action is submitted, not a new pointer-press capture
contract. Every request needs a current per-object generation/name key,
canControl and current action capabilities. Missing/malformed/stale keys,
same-name observed object replacement, ambiguous names, unknown actions and
unavailable capabilities refuse without selecting a fallback target. Native
objects/methods, art URLs and raw metadata never reach the visual model. Keys
contain frozen primitive data and are valid only within this shell instance.
Invalid identities cannot advertise admitted control availability.

The pinned watcher recreates players after unregister/register; the identity
map distinguishes those observed native objects. This does not provide a DBus
unique-owner compare-and-swap or eliminate an unobserved server-owner race after
validation. A successful return means only that a native asynchronous request was
issued, not playback/server acceptance. Synchronous exceptions report uncertainty
without retry. The API does not provide a full structured asynchronous media-error
contract here. Source selection changes only the original in-memory preference;
it never starts, pauses, transfers or launches playback. No metadata observer or
startup path sends transport commands. The original popup's keyboard/focus policy
is retained; this slice adds no new keyboard transport/navigation contract.

Media is the thirteenth closed Component, **not enabled in the twelve-widget
default layout**. After a separately approved deployment, Super+Space → Appearance
→ Menu Bar → Show Media Controls adds one `omarchy.media` in centerBegin, leaving
other entries/order unchanged. Hide Media Controls removes that ID wherever moved.
Neither operation changes playback. Both use existing exact-byte/mode/absence
backups and drift-refusing rollback. A no-op hide with absent preferences creates
no state; the cooperating-writer lock rechecks membership before writing. Restore
Default Layout intentionally returns to the existing defaults without media.

Four additional contained cases exercise native-method fakes and the actual
shared owner/original widget: all admitted dispatches, capability churn,
no-target/stale/recycled/ambiguous rejection, uncertainty without replay, popup
ownership, original click/wheel/button bodies and disappearance/reappearance.
Only media popup ownership is synthetic; its original content runs. No host media
bus, native pointer/focus/grab, pixel or playback acceptance is established.
That implementation checkpoint was source-only and made no deployment or
running-process changes or installed-path/PID check. Plan 144 subsequently
deploys these sources and verifies its owned process, not native playback.
Profiles, virtual routing and OSD, together with the broader A/C/D/E work, remain
open. Installation, native testing, packages/services and commits require separate
approval.

## Native loudness routing (plan 139, source only)

The selected server output and its loudness target are now separate. The original
hero, output-device rows and slider remain; only drag identity, route enablement
and an explicit unknown percentage are adapted. A resolved DSP selection shows
and controls the downstream target's gain/mute, never its processing gain. Output
selection still requests the selected sink as a server preference and does not
optimistically rewrite the actual default. Existing stream/input row controls
remain local and independent.

The adapter was compared with pinned original audio Panel.qml and privately
reviewed/tree-verified output-sink, output-volume and sink-availability helpers.
None is executed, imported or exposed through PATH. Official pinned Quickshell
source exposes constant link-group endpoints, tracked node properties and native
volume/mute, but no QML device-profile switching interface. Profiles still need a
separately reviewed backend; no profile placeholder or replacement panel is added.

Recognized effect_input/effect_output, virtual-name-prefix, speaker-tuning and
EasyEffects 8 ee_→ALSA/Bluetooth endpoint rules are retained. Only name-matched
route source nodes are additionally tracked; properties are read only after
readiness. Link state is deliberately not read: this is an endpoint-presence
contract, not link-health or jack-availability acceptance. Duplicate channel edges
are deduplicated; same-priority multiple outputs refuse rather than picking one.
Recognized chains are bounded to eight nodes; cycles, missing endpoints/serials,
stale objects, unready nodes and unresolved routes refuse without DSP fallback.
ALSA/Bluetooth and ordinary nonvirtual typed sinks retain direct server-sink
semantics; arbitrary names/flags do not prove physical hardware or process identity.

Every captured route contains frozen ID/name/object.serial, provider scope,
native-object generation and sorted endpoint proof data. No native nodes, methods
or raw property dictionaries enter delegates. Before gain/mute or combined master
mutation the provider recomputes the current default/route and compares that proof.
A slider drag held across rerouting, observed object recreation or backend-owner
replacement cannot silently control a new target. Route proof changes also reset
partial wheel deltas. Missing proof and server-unready state refuse. Unknown routes
disable the existing gain slider, display an em dash instead of a fabricated
percentage and name the unavailable route. A combined master request refuses
before either setter when its output route or microphone key changed; local input
controls remain usable. Synchronous setter exceptions report uncertainty without
replay or compensating unmute. Native setters/server routing are not an atomic
transaction; unobserved graph/default ABA or server changes after validation are
not eliminated. Request issuance is not functional or security acceptance.

Explicit exclusions: helper application-name-only inference, first-match ambiguity
selection, idle EasyEffects configuration fallback, unrecognized/unmarked custom
DSP mappings, availability probes, profile changes, untyped-source control, route
creation/rewiring, external commands, volume keys and OSD. Resolution is reactive
and read-only; there is no polling/expiry timer, startup write, recording/playback
or new service/agent.

Tests execute the actual provider and original surface against fake graph services
for direct/DSP gain/mute, master behavior, selection hints, rerouting, stale drags,
same-ID/name/serial object replacement, unknown/ambiguous/cyclic routes, readiness
and partial setter failures without compensation. Pure-JS probes additionally
cover bounded chains, EE8 hardware-only targets, source matching priority,
channel/link-order stability, owner scopes and forbidden unbound reads. These are
not native PipeWire, hotplug, pointer/focus/grab, pixel or audio-policy acceptance.
That implementation request made no deployment/restart/native audio changes
or installed-path/process probe. Plan 144 subsequently deploys the routing source;
no native audio functional action or policy acceptance was exercised.

## Manual profile backend (plan 140, source only)

A separately reviewed optional pactl transport now provides a manual ALSA profile
review/apply/profile-only recovery CLI, not a replacement panel or installed
profile selector. See [the backend contract and limitations](audio-profile-backend.md).
It admits only a proven already-running local PipeWire-Pulse context, strict
ALSA/serial/profile metadata, digest-reviewed shared-user requests and private
before/prepared receipts. Changes reject drift; uncertain requests are not retried
or compensated. Explicit latest-first recovery and unresolved no-native-write
acknowledgement retain backups. Native topology/default/stream restoration is not
claimed. Connecting can race a stopping service/socket activation, so the CLI
requires a separate explicit connection-risk grant as well as query/write consent.

Only synthetic protocol/process/state and bounded Python-client tests ran. No host
pactl/wpctl, audio query/change, installation, restart, package/service action or
current installed-path/PID probe occurred. There is no QML/menu/installer wiring.
Plan 140 remains source-only and excluded from Plan 144; profile UI/native acceptance, untyped inputs,
comprehensive routing and OSD remain open. No prior acceptance authorizes these
new operations.

## Native microphone ownership (plan 141, source only)

The existing original input section now uses provider-scoped frozen
ID/name/object.serial/native-object-generation proofs, matching the stronger
output/media ownership. Local gain/mute rechecks the actual default, unique graph
membership and server readiness. An input row can request a different eligible
source as a server preference, but never optimistically rewrites the default.
Stale drags, recreated/recycled nodes, serial changes and foreign provider keys
refuse rather than reaching a replacement microphone. The controller also refuses
to rebind a captured input row through ID/name alone.

The master preflights the input proof before either native setter. Unsupported
present defaults are distinguished from absence: their master hint explicitly
says microphone controls are unavailable, and they never turn a two-channel
request into output-only mute/unmute. Missing input authority disables the
original slider and uses its existing unknown percentage; keyboard navigation
skips the disabled slider. Original hero/input
geometry and device rows remain; only the input availability splice advances the
frontend to audio-native-input-frontend-v5. The pure legacy input projection is
retained for simple isolated backends, not as a production action bypass.

Native input setter/selection exceptions report uncertainty without replay or
compensation. A partly completed master never unmutes the output as compensation.
There is no native CAS/structured asynchronous acceptance or protection against
unobserved changes after validation. This does not admit untyped gain/mute,
subscriptions, input DSP routing, profile UI/helper wiring or OSD. No new node
tracker, microphone peak/recording policy, timer or startup write is introduced.

Ten new pure-JS/integration contracts and four actual-provider/original-surface
fake-service cases cover these boundaries, including stale drag/default/serial/
object/provider churn, readiness, unsupported defaults, ambiguity, disabled
original controls and uncertain partial setters. These do not establish native
input/focus/grab/pixel/audio/hotplug/authentication/security acceptance. No host
audio query/change, installed-path/PID probe, deployment, restart, package/service
action or commit occurred during that implementation request. Plan 144
subsequently deploys these microphone guards, excluding Plan 140's manual backend.

## Tests and native observation

The historical initial fidelity checkpoint passed 191 Python contracts.
Source-fidelity assertions do not claim pixel parity.
Eight actual isolated Qt fixtures cover no-output, glyphs/labels, wheel/mute,
selection, invalid/clamped values, hot-unplug/ID reuse, keyboard/cursor flow,
lazy content construction and the deliberate negative exit 42. They load the
original visual content and controls using fake nodes and a synthetic surface
owner: Qt offscreen has no native PanelWindow backend. Neither a host audio bus
nor native focus/pointer behavior is tested by those fixtures.

The first attempt to instantiate native KeyboardPanel offscreen failed with
"No PanelWindow backend loaded"; the failed report is retained. The fix replaces
only surface ownership in fixture copies. Production staging retains the reviewed
native KeyboardPanel derivation. Earlier unit failures (missing generated mirror
in test copies and outdated source/control expectations) are also retained.

Final reports, all staged-runtime artifacts unchanged:

- work/audio-port/20261024T161209.038468Z/report.json (eight fixtures)
- work/network-port/20261024T161216.270570Z/report.json (seven regressions)
- work/tray-port/20261024T161222.463033Z/report.json (five regressions)
- work/clock-preview/20261024T161226.655311Z/report.json (five regressions)
- work/audio-fidelity-unit-tests-final.log (191 contracts)

Live run: work/bar-session/20261024T161308.276025Z, PID 393392. Configuration
Loaded and no-expiry markers observed, three 26px bar surfaces, configerrors
empty. Only the existing portal app-ID warning remains at startup. This is not
interactive acceptance of the opened native popup.

Private read-only baseline: work/research/audio-fidelity/baseline/. Default
output inspect and get-volume outputs were identical before/after launch.
No audio change, sound playback, service restart or configuration reload was
performed by the assistant. The active Hyprland Lua retains its October 22 mtime.

## Scope and rollback

The native PipeWire API was reviewed at the pinned Quickshell source: the
tracker binds device properties; audio.volume/audio.muted are writable;
preferredDefaultAudioSink is a session-manager hint, defaultAudioSink reports
actual state. No package, helper, daemon configuration or installed file changed.

The prior staged UI is retained at work/bar-session/20261024T154411.383363Z.
Only the verified bar process was replaced through tools/bar_session.py stop/start.
Stop the current UI with tools/bar_session.py stop, never uwsm stop. This leaves
Hyprland, applications, PipeWire and intentional user audio choices running.
The diagnostic baseline is not an automatic audio restore script.

Normal operation remains session-long without expiry; login persistence is still
separately gated. The full bar frame/theme and other panels are unfinished.
