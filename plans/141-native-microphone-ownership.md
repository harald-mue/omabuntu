# Native microphone ownership and stale-action fences

## Goal and evidence

Continue B with the existing original microphone surface, not another standalone
helper or replacement panel. Close typed-input identity/default/readiness gaps
before admitting any untyped-input backend. Keep this request source-only.

Baseline: Omarchy v4.5.0 ac2690cd7be4f47e4a255f5e2e78d904d436b068,
unchanged licensed audio Panel.qml/Model.js and privately verified
Commons/UntypedInput.qml. Original input markup, device rows and local mute/gain
semantics are retained. Original untyped capture requires wpctl and a subscription;
those remain excluded. No new upstream code/assets are imported.

Official pinned Quickshell 2b4501a282689792b62e94f3fb30d8f512324fe6
qml.hpp/qml.cpp/node.hpp document tracker-bound properties, constant node identity,
ready state, typed audio setters and preferredDefaultAudioSource as a hint rather
than actual-default assignment. Existing AudioRouting.createAuthority supplies
provider-scoped native-object generations without changing the pinned backend.

## Gaps and proposed shape

Current local input gain/mute resolves only ID/name and has no current-default,
server-ready, serial or native-object generation fence; input selection also
lacks server readiness/exception handling. A held drag can reach a replacement
microphone, and controller nodeFor can silently resolve an old row to a reused
input ID/name. Output and media already have stronger source-only ownership.

Add a pure native-input adapter with immutable row/control records, strict unique
membership, serial/generation/provider ownership, and explicit default-present
metadata. Use it only at the actual provider boundary. Local gain/mute requires
the same actual default; input selection accepts a current eligible nondefault
row but only requests server preference. Preflight the microphone proof before
either master setter. Catch synchronous uncertainty without retry/compensation.
Disable the original slider and display its existing unknown percentage when
control identity is unavailable; explain unavailable microphone master scope.
Retain legacy pure projection for existing isolated simple-backend tests, never
as a production authority bypass. Do not offer untyped nodes as writable inputs
or silently treat a present unsupported default as an absent master channel.

## Safety and exclusions

Back up every affected path with existence/hash/mode under ignored work/ before
editing; preserve the existing dirty tree. Execute fake-service/pure-JS/offscreen
checks only, not host audio commands/queries or installed-path/PID probes.
No deployment/reload/restart, packages, privilege, service/agent/radio/trust,
security/session/desktop changes, commits or publication. No normal-component
expiry, new recording/peak activation policy, autostart or supervision.

No untyped gain/mute/subscription, profile UI/backend wiring, input DSP routing,
new input rows/panels, OSD or A/C/D/E completion. Native asynchronous acceptance,
object changes after validation, unobserved ABA, focus/input/grab/pixel/hotplug,
corporate policy and authentication/security acceptance remain separate gates.

## Tasks

- [x] Diagnose original/native API and current input ownership gaps.
- [x] Back up affected paths and preserve existing modifications.
- [x] Implement immutable native-input projection and fresh target validation.
- [x] Bind guarded gain/mute/selection/master and original surface availability.
- [x] Add pure-JS and actual-provider/original-UI fake-service regression cases.
- [x] Synchronize extraction mirrors, seals, provenance, tests and status docs.
- [x] Pass complete units, contained regressions, clean-source and backup checks.
- [x] Record source-only completion and remaining native/untyped boundaries.

## Completed source checkpoint

Added AudioInput.js with provider-scoped frozen microphone proofs and strict
fresh target resolution. The actual provider uses this adapter, not the legacy
simple-backend projection. Gain/mute binds the actual default; selection is only
a preference hint; master preflights the input proof before either setter.
The controller no longer resolves captured input rows through ID/name alone.
Original input geometry/rows remain; the availability splice advances extraction
to audio-native-input-frontend-v5. Disabled input sliders are skipped by keyboard
navigation. Unsupported present defaults have an explicit unavailable master hint.
There are no untyped setters, new trackers or new peak/recording activation rules.

Final units: 1,478 passed, including ten new pure-JS/integration contracts;
work/plan-141-units-final.log. Four additional actual-provider/original-surface
fake-service cases bring audio to 32; frame 24, tray 5, network 7, tooltip 8,
clock 5 and desktop compile also passed. Final contained reports are dated
20261122T121805; clean-source passed at
work/clean-source/20261122T121805.236259Z/report.json. All 135 runtime source
seals verified, with existing authored seal changes confined to the reviewed
provider/controller and the new input adapter; unrelated records/maps/notices
remain unchanged. Generated audio mirror and whitespace checks passed.

Fourteen prestate records verified under
work/backups/plan-141-20261122T120401010269Z/; existing changes were preserved.
Private summary: work/native-microphone-141/verification.json.

No host audio command/query/mutation, installed-path/PID probe, deployment,
restart, package/source/service/agent/radio/trust/security operation, desktop or
session transition, commit or publication occurred. Plan 135 remains the last
verified installation; Plans 136–141 are source-only. Native asynchronous,
identity-race/ABA, hotplug/input/focus/grab/pixel/security acceptance is not implied.
Untyped control/subscription, profile UI/wiring, comprehensive routing, OSD and
remaining A/C/D/E work stay open.
