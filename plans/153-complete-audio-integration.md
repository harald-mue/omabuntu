# Complete the remaining audio implementation

## Goal and compared evidence

Implement the owner's B-audio request without further design questions. Preserve
working original controls and narrow Ubuntu seams, not replacement panels. Compare
Omarchy v4.5.0 ac2690cd7be4f47e4a255f5e2e78d904d436b068 audio Panel/Model,
media Service/BarWidget, UntypedInput and original OSD parents; retain unchanged
MIT parents after tree/blob/license verification. Native APIs remain pinned to
Quickshell 2b4501a282689792b62e94f3fb30d8f512324fe6 and the already reviewed
PulseAudio 17 pactl contract, 1f020889c9aa44ea0f63d7222e8c2b62c3f45f68.

## Current gaps and shape

Existing typed controls, media transport, serial/generation route proofs and
manual reversible ALSA profile backend work, but profile surface/package wiring,
untyped input controls and observed subscriptions, metadata-backed custom DSP
routes, original OSD and safely admitted artwork remain incomplete.

Use one bounded standard-library RPC bridge for the original audio surface,
reusing profile review/digest/before/prepared/readback/recovery rather than a new
profile policy. Profile changes require explicit review/Apply in the UI, disclose
shared-user/call interruption and transport activation risk, and never apply on
selection/open/refresh. Add strict endpoint projection and current-default proof
for untyped gain/mute; preserve uncertain receipts, no retries/compensation.
Queries must be explicit opt-in and report unavailable dependencies/providers,
not install them or silently fall back to an alternate daemon. Subscription
lifetime follows the selected/visible component, with bounded event framing and
invalidation; individual requests keep deadlines, not component expiry.

Extend the existing original rows/controller for profiles and recovery. Keep
native objects behind providers, frozen primitive targets in delegates and
captured drag/action identity. Generalize routing only when native graph metadata
unambiguously associates processing endpoints; cycles, absent/ambiguous topology
stay unknown rather than guessing hardware gain. Preserve the original OSD
layout/model and media art slot, with closed local artwork admission, bounded
image dimensions/file sizes, no remote fetch or arbitrary file URL traversal.
Feedback must distinguish requests issued from observed native acceptance.

## Safety and exclusions

Back up every affected source with existence/hash/mode under ignored work/;
preserve the committed baseline and original vendor parents. Source and contained
synthetic protocol/UI/process tests are authorized by this implementation request.
No host native probes/setters, package/source installation, service activation,
privilege, installed-path mutation, bar restart, session/binding/autostart,
GNOME/security/recording/corporate-agent change, credentials, commit or publication.
Those safety gates are not bypassed by the request to avoid further questions.
Native hardware/call/hotplug/pixel/Wayland acceptance cannot be manufactured from
synthetic tests. Exclude remote artwork retrieval, arbitrary helpers/config/argv,
Bluetooth radio/agent policy, audio recording and full topology rollback.

## Tasks

- [x] Back up source paths and verify original OSD/untyped/artwork/API contracts.
- [x] Integrate transactional profile review/apply/recovery into the existing surface.
- [x] Implement proof-bound untyped input observation/control and event invalidation.
- [x] Extend unambiguous custom DSP routing without unsafe gain fallback.
- [x] Restore original OSD and safely admitted original artwork slot.
- [x] Wire shared owners, dependency reporting and release packaging.
- [x] Exercise disappearance, stale proof, uncertainty/recovery and actual original UI.
- [x] Synchronize mirrors/provenance, pass units/contained/clean-source/whitespace.
- [x] Document implemented contracts and all remaining acceptance/approval gates.

## Completed source checkpoint

The owner paused work before final slider validation and subsequently requested
continuation. Final pulse-backed pointer gestures preview within the original
slider and submit one captured value on release. Close/loss/replacement cancels
the old gesture without adopting a new source; typed controls remain continuous.
Readback retains last-observed presentation behind an independent write fence,
not optimistic values. Fresh native no-ops do not accumulate receipts.

All 1,586 unit tests, 42 isolated audio cases, 39 frame cases, 8 tooltip cases,
5 tray cases, 7 network cases, clock/desktop checks and clean-source checks pass.
All 150 shell sources are sealed. A private source-check bundle passes manifest,
shell/helper-byte checks and sandboxed helper CLI/import checks; it was not
installed or started. Existing tracked files have verified exact baseline
backups. Detailed reports and generated fixtures remain under ignored work/.

See [audio completion](../docs/audio-completion.md) for the admitted contracts,
explicit exclusions and remaining gates. In particular, remote art and unproved
mixed untyped-input/DSP combined master remain excluded. These checks do not
establish native device/call/hotplug/pointer/pixel/security acceptance. The current
installed Plan 152 was not changed; deployment, native actions, package/service
changes, bindings/autostart, commits and publication remain separate approvals.
