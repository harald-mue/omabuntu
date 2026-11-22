# Native, identity-bound audio volume routing

## Goal and evidence

Continue B after Plan 138 without changing the installed desktop. Separate the
selected output from its actual loudness target for recognized DSP routes, using
the existing original audio surface and the pinned native PipeWire API.

Compare Omarchy v4.5.0 commit ac2690cd7be4f47e4a255f5e2e78d904d436b068:
unchanged admitted audio Panel.qml/Model.js and privately reviewed helpers
omarchy-audio-output-sink (blob 1b4146cf4730ad98c5bf6a8f0e058574543e4742,
SHA-256 ab0b3f92c546d09a24fbf300f4892a1aadac06746438f663bd85138a3492ecfd),
omarchy-audio-output-volume and omarchy-audio-sink-availability. Helpers were
verified against the pinned tree/blob/size and are research only, never executed
or imported. The existing full MIT notice is preserved. Review official
Quickshell source/docs at 2b4501a282689792b62e94f3fb30d8f512324fe6: qml.hpp,
node.cpp, link.hpp and device.hpp. Node/link endpoints have constant identity;
properties require tracked, ready nodes. Link state requires binding and is not
needed for the endpoint-presence contract below.

## Current gaps and proposed shape

The audio provider currently controls the selected typed sink directly. Original
upstream resolves DSP loudness through a helper and falls back to the virtual
sink when unresolved. Native QML exposes graph endpoints but no device-profile
selection contract; profiles and untyped inputs need separate backend review.

Add a pure native graph adapter, not a replacement panel or helper subprocess.
Preserve original effect_input/effect_output, virtual-name-prefix and EasyEffects
8 ee_ endpoint matching. Require a unique current route; do not choose an arbitrary
first output or fall back to DSP gain. Resolve bounded recognized chains and
refuse ambiguous, missing, unready, cyclic or excessive-depth routes. Track only
name-matched route sources in addition to the already tracked output sinks.
Exclude application-name-only inference and idle EasyEffects config fallback.
ALSA and ordinary nonvirtual typed sinks retain direct server-sink semantics;
that does not prove every arbitrary sink name is physical hardware.

Bind route records to ID/name/object.serial plus a session-local native-object
generation and sorted endpoint proof. Project frozen primitive records only.
Before each output gain/mute or combined master mutation, recompute the current
route/default and compare the captured proof. A rerouted slider drag must never
write a different target. Keep selected output rows/default selection separate;
no preference, graph, device/profile or stream edits during resolution. Current
physical-target volume/mute drive the existing original hero/slider. Unknown
routes disable output gain and display an explicit unknown state. Individual
microphone/stream controls remain independent. Combined master requests must
preflight the resolved output and microphone before either setter, with the
existing uncertainty/no-compensating-unmute rule.

## Safety and exclusions

Back up each implementation/documentation path with prior existence/hash/mode
under ignored work/, preserving previous dirty-tree changes. Repository and
contained fake-service tests only: no installation/restart, host audio commands,
new packages/sources, native media playback/recording, device/profile changes,
radio/trust/agent/service activation, compositor settings, privileges, security
changes, session transitions, commit or publication. No original helpers on PATH.
No timers or expiry wrappers. Endpoint observations are not a server transaction,
link-health proof, unobserved-ABA guard, atomic cross-channel mute or hardware/
security acceptance. Native hotplug/routing/input/focus/pixel behavior stays open.
Profiles, untyped-source controls, availability probes, idle configuration fallback,
OSD and remaining A/C/D/E are excluded from this bounded slice.

## Tasks

- [x] Diagnose original routing and official pinned native/profile API limits.
- [x] Back up all affected implementation/documentation paths.
- [x] Implement bounded graph resolution with frozen generation/proof records.
- [x] Connect fresh-proof output/master actions and original display/slider seams.
- [x] Test direct/DSP/EasyEffects/chains, ambiguity, cycles, readiness and target churn.
- [x] Verify actual provider and original UI with fake native graph services.
- [x] Synchronize seals/docs and pass complete unit/contained/clean-source checks.
- [x] Record native limitations and the absence of deployment/activation.

## Completed source checkpoint

AudioRouting.js implements the reviewed endpoint-name policy with tracked-ready
node identities, per-provider scope/generation, bounded chains and immutable
route proofs. The actual provider recomputes the current route before explicit
output/master mutations; stale captured drags, changed defaults/objects, missing
serials, unready servers and ambiguous/missing/cyclic routes refuse without DSP
fallback. Selected/default output and its downstream loudness target remain
separate. Output choices still request a server preference, not optimistic
selection. Local microphone/stream actions remain independent.

Original hero/rows/slider geometry is preserved. Three closed output-section
seams cover drag identity, route enablement and explicit unknown percentage;
the existing controller reports unavailable/uncertain outcomes and resets partial
wheel deltas when route proofs change. There is no additional panel, helper
process, graph edit, device-profile switch, polling/expiry timer or startup write.
The original helper's first-match ambiguity, application-name-only inference and
idle EasyEffects config fallback remain deliberately excluded. Ordinary nonvirtual
typed sinks retain direct server-volume semantics; this is not universal hardware
identity or complete virtual-routing parity. The pinned native QML API has no
profile-switching interface; a reviewed backend is still needed for profiles and
untyped sources.

Passed verification: 1,420 unit tests; 28 contained audio cases, including four
new cases executing the actual provider/original UI; 24 frame cases; desktop,
tray/network/tooltip/clock and clean-source regressions; 134 sealed sources;
15 implementation/documentation prestate records with backup hashes/modes; and
whitespace checks. Pure-JS probes cover EE8 hardware-only targets, source-name
priority, chains/cycles/depth limits, duplicate/order-independent links, stale
endpoints, source serials, scope/object replacement and forbidden unbound reads.
Actual-provider cases cover master preflight/partial failure and uncertain gain
setters without replay or compensating unmute. The initial fidelity assertion
expected only the old drag splice; it was updated to admit exactly the two new
route-state splices, without changing original geometry or vendor parents.
Evidence remains private under work/plan-139-*-final.log and
work/native-audio-routing-139/verification.json.

No installation, process control/restart, host media command, native preference
or graph edit, package/service/agent activation, session/security change, commit
or publication was performed. Installed paths/PID continuity were not probed;
Plan 135 remains the last verified deployment, not a newly verified runtime.
Plans 136–139 remain source-only. Endpoint presence is not link health, an atomic
server transaction, protection against unobserved ABA after validation, native
hotplug/audio-policy/input/pixel acceptance or security acceptance. Full profiles,
untyped inputs, availability/config fallback, OSD and remaining A/C/D/E stay open.
