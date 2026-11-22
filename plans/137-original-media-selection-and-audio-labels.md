# Restore original media selection and audio-stream presentation

## Goal and evidence

Continue B with original active-player ownership and stream label/highlight
behavior, not a replacement media panel. Compare Omarchy v4.5.0 commit
ac2690cd7be4f47e4a255f5e2e78d904d436b068, the unchanged audio parent, and
Quickshell MPRIS headers at 2b4501a282689792b62e94f3fb30d8f512324fe6.

The pinned Git tree identifies MediaModel.js as blob
cab271e29f9b73907b3051f1e36b01e8775d0e58 (6877 bytes, SHA-256
566cc2c88196fedfd7b20a28e867c68efe519a65e250e4efb9946e77134654e6)
and Service.qml as blob 86c5cca36474527fb68a644a39296988434fb653
(16505 bytes, SHA-256
203fa954e84d356ed057abbd60c58aae238ce2d46014b5f3f1642e5869f9d16a).
The complete original MIT notice matches the already preserved vendor and stable
notices. Fetches remain private research until this license/tree/blob review;
only these two unchanged parents are admitted, with recorded origin and hashes.
The original BarWidget was reviewed privately, not imported: its transport,
source switching, album-art loading and popup ownership require later work.

## Current gap and proposed shape

Playback-stream snapshots currently pass an empty MPRIS list to the original
AudioModel and the derived row disables active-player highlighting. Restore a
read-only extraction of the original media service's selection functions and
reactive playing-order ownership. Keep its oldest-playing, playback-stream,
proxy, preferred and idle fallback rules. Import the unchanged pure MediaModel,
not the whole service's commands/startup/IPC graph.

Use a single shared Commons selection owner across outputs, following the
original shell's one-service ownership instead of separate per-output histories.
It owns a tracker for strictly admitted playback candidates before property
reads; existing output-local providers retain their own presentation trackers.
Never expose native nodes/players to visual delegates. Project a frozen whitelist
of primitive player metadata and active identity.
Use original AudioModel streamLabel/streamRepresentsPlayer against that projection
and retain original StreamRow geometry/visuals. Update extraction version, exact
mirrors, source admission and provenance. No transport API is added by a read-only
selection slice, and no native volume/mute/selection writes occur during discovery.

## Safety and exclusions

Back up each affected path with prior existence, SHA-256 and mode under ignored
work/. Preserve all existing Plan 133–136 work. No installed-release changes,
restart, services, packages/sources, agents, radio/trust changes, desktop config,
keybindings, recording/playback, privilege, security-policy changes, lock/idle/
suspend, commit or publication. No album-art URL loading, IPC, automatic source
transfer, media/volume commands, remote endpoints, OSD or whole-shell startup.
Fixtures replace the native MPRIS singleton, use fake players/streams, never host
DBus/PipeWire, and are not native visual/focus/input/media acceptance.
Profiles, virtual routing, remaining media transport/OSD and A/C/D/E stay open.

## Tasks

- [x] Review original selection/model/widget and official pinned native API contracts.
- [x] Back up affected paths; import the two unchanged, licensed and verified parents.
- [x] Derive the original read-only selection owner and frozen primitive presentation.
- [x] Restore original MPRIS-aware stream labels and active-row presentation.
- [x] Test playing order, proxy/idle/preferred rules, churn, generic labels and no mutations.
- [x] Synchronize source seals/docs and pass complete unit and contained regressions.
- [x] Verify the installed release and current owned session bar without restarting; record boundaries.

## Outcome and verification

The two unchanged MIT parents are admitted with pinned tree/blob/hash provenance.
The derived shared Commons singleton preserves all twelve selected original
function bodies and reactive observers. It owns playback-node binding separately
from output-local presentation providers. A primitive-only frozen projection now
restores the original MPRIS label/ambiguity and active-row behavior without new
panels, transport actions or album-art loading.

All 1,398 unit tests, twenty isolated audio cases, twenty-four isolated frame
cases, the isolated desktop fixture and tray/network/tooltip/clock regressions
passed. Four media cases cover reactive play order, stream/proxy/preferred/idle
rules, generic ambiguity, original row wiring and metadata/player/stream churn.
Two actual provider instances observe the same shared owner with only native
services substituted. Missing/duplicate extraction witnesses, mirror drift and
unsafe metadata exposure have negative controls. Clean-source export, 131 sealed
sources, twenty private prestate/backup records, existing vendor-parent integrity
and whitespace checks passed.

Read-only verification confirms the installed Plan 135 release still verifies
and remains selected; the current owned bar has session lifetime. Its PID differs
from the historical deployment receipt, so no cross-session PID continuity is
claimed. No restart, installation, package/service/agent activation, media/audio
write, native input injection, desktop configuration change, commit or publication
was performed. Native MPRIS/media, focus, visual and input acceptance remain open.
Private research, fixture diagnostics, reports and verification stay under work/.
Remaining B profiles/virtual routing/transport/OSD and A/C/D/E are not completed.
