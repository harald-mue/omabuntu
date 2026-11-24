# Audio completion: admitted contracts (plans 153–157)

Plan 153 implements the remaining B-audio source integration in the existing
original audio/media surfaces. Its implementation request was source-only.
The separately approved [Plan 154 deployment](../plans/154-local-audio-completion-deployment.md)
now installs these contracts and restarts only the managed session-lifetime bar,
with 150 verified shell seals and no new warnings. Runtime, manager, menu,
unrelated helpers, assets, preferences and existing native receipts remain
unchanged; wallpaper restoration is disabled. Plan 152 is the retained immediate
fallback, including its owner-accepted DND/nightlight controls and tooltips.

[Plan 155](../plans/155-audio-advanced-page-and-scrollbar-gutter.md) subsequently
installs the audio-layout correction: the ordinary popup retains the original
normal controls plus one compact **Advanced audio…** action. That action opens a
separate page in the same popup, with **Back to audio**, disclosures, grants,
profile review/Apply and recovery. Navigation never grants or revokes backend
access; closing/reopening returns to the normal page and cancels old gestures.
The advanced cursor cannot act on hidden normal-page controls. The scroll policy
is unchanged, but overflowing content reserves the vertical bar width plus a
theme-scaled inner gap; nonoverflow uses the full width. Global Qt styling and
other panels are unchanged. Plan 154 is the immediate verified fallback.

[Plan 156](../plans/156-audio-panel-height-and-navigation-polish.md) corrects the
owner-rejected Plan 155 spacing/height result. The audio-only 560-unit cap is
removed: the original KeyboardPanel fits natural content to available screen
height. Nested page content now declares its actual scroll extent, so constrained
fallback scrolling reaches the last action. Overflow clearance is balanced on
both sides, and neither side reserves space when content fits. Advanced/back
navigation uses the original Button icon slot with a settings/back glyph and a
short label. Only two shell files plus provenance changed; Plan 155 is retained
as the immediate fallback. No new backend grants or native audio actions.

**Installation is not native audio acceptance.** The optional audio bridge remains
disconnected until explicit UI consent; deployment issued no optional bridge
query/subscription/setter or profile change. No package/service action, binding,
autostart, commit or publication occurred. Device/call/hotplug/pointer/OSD checks
remain a separate owner live-acceptance step.

## Application audio labels (plan 157)

Plan 157 installs the missing English **APPLICATION AUDIO** heading and narrowly
refines duplicate stream labels. Original unique application labels stay unchanged.
Repeated labels show **Stream #serial**, optionally followed by a bounded current
media.name, node description or media.role that differs from the application name.
Descriptors accept strings only, reject control/bidi formatting characters and
oversized values, and are rendered as plain text. Delegates still receive frozen
primitive rows, not native objects or property dictionaries.

These are server-local playback-stream identifiers, not participant numbers or
persistent identities. A browser can publish multiple streams; neither counts nor
labels establish which meeting participant, tab or audio function owns one. No
browser/meeting inspection or new native probe is performed. Every existing
id/name/serial control guard remains unchanged; streams are neither merged nor
linked to a new group control. Missing descriptors fall back to explicit stream
IDs rather than invented titles. This label-only update retains accepted layout,
height, navigation and spacing. Plan 156 is the immediate verified fallback.

## Original source, not a replacement audio panel

The baseline is Omarchy v4.5.0
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`, with unchanged MIT Panel/Model,
media Service/BarWidget, OSD/OsdModel and SizedImage parents. The new parents were
verified against their pinned tree/blob hashes and MIT notice before import.
`upstream/clock-preview.json` retains exact origin/blob/content/derived hashes;
generated mirrors must match deterministic extraction. The original measured OSD
card, progress/readout geometry, icons, transient hide behavior and bounded image
slot remain. A nonvisual shared owner replaces only OSD IPC/activation plumbing.

The audio hero, sliders, stream rows, scroll/popup and cursor are still original
components. Added profile/recovery capabilities use their original Button,
PanelSectionHeader and separator inside that panel, not a replacement panel.
On the advanced page they join its existing arrow/j/k cursor and Enter/Space
activation, with navigation restricted to the visible page. Horizontal
adjustment is a no-op there; m does not accidentally mute an unrelated output.
Changing approval/model membership revokes a positional profile cursor. Tab keeps
its existing cross-panel meaning. Existing typed 0–100% device controls and
0–150% playback-stream controls retain their established contracts.

## Optional local bridge and session lifetime

`audio_controls.py` is one bounded JSON RPC bridge. `audio_pactl.py` retains the
reviewed PulseAudio 17 contract at
`1f020889c9aa44ea0f63d7222e8c2b62c3f45f68`; no PulseAudio implementation is
imported. Quickshell stays pinned to
`2b4501a282689792b62e94f3fb30d8f512324fe6`.

Queries are off until an explicit in-panel grant discloses that connecting to an
existing local socket can activate a stopping transport. Only the canonical,
already-proved same-user pipewire-pulse owner and trusted `/usr/bin/pactl` are
admitted. Missing executable/owner/schema/helper configuration is reported; no
package installation, daemon start, alternate server or wpctl fallback occurs.
Every RPC is scope-bound, size-limited and watchdog-bounded. A timeout or malformed
response revokes knowledge, never manufactures successful native state.

A fixed `pactl subscribe` worker supplies invalidation, not authoritative values.
It has bounded framing/rate, context checks and cleanup; there is no reconnect
loop, setter or forced component expiry. Ready means process/context admission,
not functional acceptance. Subscription loss fences optional writes until an
explicit reconnect and fresh observation. Superseded-scope replies/events cannot
readmit an old owner. Normal ownership is session-long while the audio component
is selected/visible; timers are individual RPC/coalescing/OSD deadlines only.

One nonvisual provider/bridge/feedback owner is shared across outputs. Peak
monitoring has explicit per-panel owners: closing one panel cannot stop another.
The native peak monitor runs only for typed default inputs while a panel is open.
No recording is added for virtual inputs; their original hidden-meter behavior
is preserved.

## Profile review, apply and recovery

Only available, non-off ALSA profiles advertising an input or output are offered.
Selection produces a review, **not a setter**. Review binds the displayed card
index/serial, observed audio owner/state and UI scope to the native before-state
and approval digest. Apply is a separate action with an interruption warning.
Opening, querying, subscription events and refresh never apply a profile.

The existing [profile engine](audio-profile-backend.md) still prepares/fsyncs
before/outcome receipts, revalidates drift and issues one symbolic setter before
readback. Recovery restores only the prior profile name under the original
identity; it does not restore topology, defaults, volumes, streams or policy.
Prepared/restore-prepared evidence blocks writes. Acknowledgement is explicit and
is not restoration. Profile writes/restores, including the manual CLI, check
control uncertainty under the shared profile-operation lock. Controls acquire
that same lock before their own private journal lock, preventing cooperating
profile/control writers from passing each other's preparation window.

## Virtual input and DSP contracts

Untyped inputs require both current native object-generation authority and a
matching pulse name/object serial. Delegates receive frozen primitive rows,
never process/native handles. Gain/mute additionally require the actual default,
a current full-observation key and unchanged server/endpoint/default proofs.
Gain is capped at 100%, preserves channel balance and never implicitly unmutes.
For pulse-backed inputs the original slider previews moves locally and issues
one captured final value on release; typed inputs keep continuous native moves.
Closing, loss or replacement cancels the gesture without transferring it to a
new source. Fresh wheel/keyboard actions remain discrete. Local action readback
retains last-observed rows behind a separate write fence, never optimistic gain.
A fresh native no-op produces neither a setter nor another receipt.
Prepared private receipts precede issuance; matching identity/channel/readback is
required for confirmation. Failure/timeout/partial master outcome retains the
receipt, blocks further optional writes and never retries or compensates.
Control acknowledgement does not restore gain/mute. Private receipt storage is
bounded, rejects corruption/links/mode drift and does not auto-prune evidence.
Storage and wire limits are distinct: an oversized history reply refuses rather
than truncating recovery evidence, potentially before the journal entry ceiling.
There is no automatic retention/rotation or capacity-reset action; preserving
and archiving such evidence requires a separate reviewed recovery operation.

The existing route resolver now also admits exact node.link-group/node.group
associations backed by current native graph links. Potential processing streams
are tracked before reading their bound metadata. Association participates in the
captured route proof. Multiple targets, disappearance, changed metadata, cycles
and missing authority refuse; there is no hardware-gain guess or graph rewrite.
Existing recognized EasyEffects/tuning routes remain supported.

Combined bridge master mute is admitted only when the selected default equals the
proved direct loudness target. A mixed untyped-input/DSP-output asynchronous bridge
cannot prove intervening graph ownership and is refused before either setter;
individual proved controls remain available. This is an explicit unsupported
combination, not a silent fallback. Identity checks/advisory locks are not atomic
server CAS, a guarantee against external writers or an ABA/security boundary.

## Original OSD and admitted artwork

Shared OSD feedback follows observed default-device gain/mute changes, not the
first observation or a replacement default. It never claims that request issuance
proves playback/call acceptance. The original media dispatch icons are retained;
optional media feedback explicitly says requested. The original widget continues
to suppress redundant transport OSD inside its own controls. Existing hardware
volume changes can be observed without installing new key bindings. No old OSD
owner is stopped/replaced by this source request; coexistence needs deployment
review. Boosted observations retain a truthful percentage readout with the
original bounded progress bar; normal setters do not introduce gain boost.

Only owned, non-symlink, stable PNG/JPEG files already under the user's cache are
admitted. Encoded input is at most 4 MiB, dimensions at most 2048 per side; SVG,
remote/data URLs, arbitrary home/tmp files, URL authorities/query/fragments and
parent traversal refuse. Accepted bytes are copied once to private content-hash
objects under `omabuntu/audio-art`, bounded to 64 entries/32 MiB with no automatic
eviction or overwrite. Player/track generations bind RPC completion; only the
exact cache-prefix/hash URL reaches the unchanged original SizedImage. Unknown or
rejected art keeps the original music fallback. This is bounded admission, not an
image-decoder sandbox or security/pixel acceptance.

## Source verification

Plan 153 checks passed 1,586 unit tests and 42 contained audio cases, plus 39 frame,
8 tooltip, 5 tray and 7 network cases, clock/desktop checks and clean-source
checks. All 150 shell sources are sealed. The private source-check bundle passes
manifest, shell/helper-byte checks and sandboxed helper CLI/import checks; it has
not itself been installed or started. Plan 154 instead installs a narrow verified
derivative of Plan 152, carrying the same sealed shell sources and six exact
audio-helper files while retaining the installed runtime and unrelated assets.

Plan 155 additionally passes 1,587 unit tests and 43 isolated audio cases, plus
frame/tooltip/clean-source and runtime preflight. Its actual offscreen-window
fixture measures an inner content-to-scrollbar gap, full-width nonoverflow,
explicit page/Back/reopen behavior, stale-action rejection and no navigation
grant. This is not owner native visual/pointer acceptance.

Plan 156 passes 1,588 units and the same 43 isolated audio cases with strengthened
layout checks: twelve original device rows, fitting beyond the old cap, visible
icon navigation, zero nonoverflow side reservation, balanced overflow clearance,
explicit flickable extent and complete last-action reachability at a constrained
viewport. Frame/tooltip/clean-source and runtime preflight also pass. Owner native
visual acceptance was subsequently explicitly given for the corrected audio view.
This closes the Plan 156 layout confirmation only; profile/recovery, virtual-input,
DSP, call/hotplug and OSD-coexistence functional live acceptance remains separate.

Plan 157 passes 1,590 units, 43 contained audio cases, 39 frame cases, eight tooltip
cases, clean-source and runtime preflight. The strengthened original stream case
renders five same-name browser streams, verifies the translated heading and
supplied descriptors, and proves that gain changes only one independently
addressed stream. JS checks cover reorder-stable IDs, unchanged unique labels,
missing/non-string/oversized/control/bidi metadata, bounded descriptors, unbound
nodes, serial replacement and frozen primitive projection. These synthetic
fixtures do not establish live Teams participant ownership or call acceptance.

Original-slider signal-path fixtures cover one final asynchronous write,
retained observation/readback fencing, cancellation and late-release refusal.
These are not physical pointer or live microphone acceptance.

## Explicit exclusions and remaining gates

- Remote artwork downloads and covers outside the admitted cache; no substitute
  remote fetcher, player launch or credential access.
- Bluetooth/network profile policy, pairing agents, radio changes, unavailable/
  off profiles, jack availability probes and arbitrary DSP configuration inference.
- The mixed bridge-master combination above, input DSP graph creation/rewiring,
  automatic routing/stream moves, full topology rollback and automatic replay.
- New volume bindings, installer/package changes, daemon activation, crash
  supervision/autostart, security/recording policy and native desktop changes.

Plan 154 includes all optional bridge/profile/event/artwork/recovery modules in
the backed-up, separately approved local release. Inclusion is not query consent;
new native actions still require their individual UI grants. Existing everyday audio
acceptance does not establish this new profile/untyped/DSP/OSD/artwork matrix.
Contained protocol/process/original-QML tests cover stale generations, loss,
malformed capabilities, partial writes, timeout and recovery. Hardware, calls,
physical hotplug, native input/popup/pixel/OSD coexistence and security acceptance
remain explicitly unverified.
