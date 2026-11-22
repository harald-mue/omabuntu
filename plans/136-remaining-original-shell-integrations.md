# Continue the remaining original-shell integrations

## Goal and evidence

Continue the owner's request for the remaining A–E implementation, without
mistaking the locally installed Plan 134 slices for full completion. Compare
against Omarchy v4.5.0 commit ac2690cd7be4f47e4a255f5e2e78d904d436b068,
the unchanged licensed vendor parents and official Quickshell API headers at
2b4501a282689792b62e94f3fb30d8f512324fe6. Preserve all existing dirty-tree work.

## Gaps and proposed shape

A still lacks original theme/service ownership and reviewed layout variants.
B lacks profiles, untyped-source fallback, physical-sink resolution, active-player
integration, media/OSD and two-channel master mute. C lacks complete pending/error
ownership and an owned agent. D lacks durable output/topology/text-size storage
and recovery. E has no individually agreed optional integration set or dependency
and ownership review. These are separate native contracts, not a single switch.

Start with B's original two-channel hero semantics and C's bounded device-action
ownership, using existing original UI rather than replacement panels. Master mute
must resolve both captured typed devices before any write and reject stale object
serials, missing devices and malformed keys. It must not touch streams, volume,
selection or untyped inputs. The explicit hero action controls both output and
microphone; section actions stay channel-local. Opening/readback never mutates.
Retain original any-audible semantics with an explicit scope tooltip. Native
setters are not a cross-channel atomic transaction; do not claim otherwise.

Review C against the pinned BluetoothDevice API: asynchronous invocations expose
state but no structured QML operation-error signal. Track requested actions until
observed completion, disappearance, owner/adapter loss or a bounded operation
deadline; never claim that issuing an invocation proves success. Never register
an agent or modify radio/trust/audio policy implicitly. Review the remaining A,
D and E dependency/ownership contracts before admitting their implementations;
unsupported/security-sensitive integrations remain visibly open, not fake stubs.

## Safety and exclusions

This is repository implementation only. The installed Plan 135 release and
running desktop remain unchanged. Back up affected repository files with prior
existence, SHA-256 and mode under ignored work/. No package/source installation,
privilege, service/agent activation, desktop reload, configuration apply,
radio/trust change, recording/playback, security-policy change, lock/idle/suspend,
commit or publication. Preserve GNOME, keyring, certificates, VPN and corporate
agents. Optional authorization/security agents are not approved by this request.
Do not import further upstream assets/code without provenance and license review.
Fixtures use fake nodes/devices and isolated surfaces, never host services.

## Tasks

- [x] Diagnose the installed/source boundaries and review original master-mute and pinned native APIs.
- [x] Back up affected source paths and implement guarded two-channel master mute.
- [x] Verify mixed/single/no-channel, serial reuse, stale/default changes and channel-local controls.
- [x] Restore bounded Bluetooth action status/ownership and test failure/churn paths.
- [ ] Review and implement remaining A theme/service ownership.
- [ ] Review and implement remaining B profile/virtual/media/OSD contracts.
- [ ] Review and implement C agent and separately approved optional policies.
- [ ] Review and implement D durable display plan/apply/recovery.
- [ ] Agree and review E integrations individually before implementation/activation.
- [x] Synchronize source seals, current documentation and pass full/isolated checks.

## Implemented source slices and remaining boundaries

The original hero/right-click action now applies one desired mute state to output
and microphone, while section/stream actions remain local. Both default devices
and bound object serials are checked before any write. Missing/reused/malformed
identity rejects preflight without a partial write. A native setter exception can
still leave a partial result: uncertainty is reported without retry or unsafe
compensating unmute. The tooltip names output and microphone. Four new isolated
audio cases exercise mixed, single/no-channel, stale/default/serial guards and
setter exceptions, alongside pure-JS execution of the actual action code.

Bluetooth action records now retain primitives only: address, DBus path, adapter,
phase and deadline. Original connecting/disconnecting/forgetting row states remain
pending until observed completion. Duplicate requests fail; pairing acceptance
issues at most one follow-up connect. Device/adapter loss, disabled radio,
invocation exceptions and deadlines stop tracking without replay or automatic
radio/trust/audio policy changes. Actual QML actions run in the contained desktop
fixture and pure-JS tests. The native API has no structured operation-error signal;
these guards are not full BlueZ error acceptance, an owned agent, or a guarantee
against every same-path disappearance/reappearance between observations.

The installed release is unchanged. These are two further source slices, not
completion of the owner's remaining A–E request. A theme/service ownership, B
profiles/virtual mapping/media/OSD, C owned agent/policies, D durable displays and
E individually agreed integrations remain unchecked above. In particular, do
not substitute a dependency catalog or a success stub for a working integration,
and do not activate the whole original service graph to bypass its review.

## Verification checkpoint

All 1,390 unit tests, sixteen isolated audio cases, twenty-four isolated frame
cases, the isolated desktop/action-ownership fixture and tray/network/tooltip/
clock regressions passed. Clean-source export, 128 sealed preview sources,
fourteen private prestate/backup records and whitespace checks passed. The
installed Plan 135 immutable release still verifies and its identity-checked
session bar PID is unchanged. No new packages, services, agents, native input,
audio playback/capture, radio/trust state, desktop configuration, restart,
installation, commit or publication occurred. Contained tests do not establish
native visual, input, audio or authentication acceptance.
