# Restore original optional media controls with guarded transport

## Goal and evidence

Continue B from the shared Plan 137 selection owner to explicit media transport
and the original media bar widget/popup, not a replacement panel. Compare Omarchy
v4.5.0 commit ac2690cd7be4f47e4a255f5e2e78d904d436b068 and official Quickshell
MPRIS player/watcher APIs at 2b4501a282689792b62e94f3fb30d8f512324fe6.

The original BarWidget.qml is blob b4c9a7d38690628eb47a9b5856a6ab23ce350a21,
12247 bytes, SHA-256
ce306a3b6d2308c948b0acf08fcf7fa651d69a6d8d5b672b3e004d1c165748a2.
Its complete source was reviewed privately in Plan 137; the pinned MIT notice
matches the already preserved stable/vendor notices. Verify tree/blob/hash and
license again before importing this unchanged parent. Existing parents remain
unchanged. The original native transport dispatch branches come from the already
admitted Service.qml, with narrow capability/identity/error guards.

## Gaps and proposed shape

The selection owner is read-only and no media control widget is admitted. Add
session-local generation tokens for current native player objects. Project only
frozen primitive metadata, capabilities and opaque target keys. Every explicit
transport request requires a current matching key, canControl, a known action
and current action capabilities. Never fall back to another player on stale,
missing or unsupported targets. Catch synchronous exceptions without replay;
issuing a native asynchronous call is not observed playback acceptance. The
pinned watcher recreates players on unregister/register. Tokens guard observed
object replacement, not unobserved DBus owner races after validation or unique
server-owner compare-and-swap.

Derive the original widget, metadata, source list, scrolling label, popup and
transport buttons. Replace only the service lookup/native delegate exposure,
mandatory target keys, excluded artwork loader and visible error seam. Preserve
original mouse action meanings and native dispatch branches. Source selection
changes the in-memory preference only and never transfers playback. No OSD.
Register media as the thirteenth trusted optional Component; retain the existing
twelve-widget default order. Add explicit Appearance/Menu Bar Show/Hide Media
Controls through existing exact-backup transactional preferences. Showing adds
one centerBegin entry if absent; hiding removes that ID wherever moved. Reads
and installation do not enable it. Restore Default Layout keeps its existing
meaning and excludes the optional widget.

## Safety and exclusions

Repository implementation only. Back up every affected path with existence,
SHA-256 and mode under ignored work/, preserving all dirty-tree work. No live
installation, restart, package/source changes, service/agent activation, native
media/audio commands, recording/playback, radio/trust changes, desktop settings,
keybindings, privilege, security-policy changes, lock/idle/suspend, commit or
publication. No album-art URL loading, external endpoints, arbitrary commands,
player launching/raising/quitting, volume/seek, source transfer, OSD, new shortcut
or whole-shell startup. Normal components retain session lifetime, not expiry.
Fixtures use fake native players/services and substitute only popup ownership;
original widget content executes. Native pointer/focus/grab/pixel/media-server
acceptance remains separate. Remaining A/C/D/E and B profiles/routing/OSD stay open.

## Tasks

- [x] Review original widget/dispatch, pinned watcher identity and capability contracts.
- [x] Back up affected paths and import the verified unchanged widget parent.
- [x] Add generation-bound targets and guarded original transport dispatch/source selection.
- [x] Restore the original widget/popup with primitive rows and no artwork loader.
- [x] Add optional closed-registry admission and reversible Show/Hide preference actions.
- [x] Test capability changes, target churn, stale/no-target rejection, errors, UI and rollback.
- [x] Synchronize mirrors/provenance/docs; pass units and contained regressions.
- [x] Record remaining native acceptance and verify no deployment was performed.

## Completed source checkpoint

The original widget and native dispatch branches are now derived under sealed
transforms original-media-widget-v1 and guarded-media-owner-v2. The unchanged
parent is imported only after tree/blob/hash/license verification. The twelve
original selection function bodies/reactive observers remain intact. Shared
selection/transport uses one owner across independent per-output widgets. All
native targets stay inside that owner; metadata, admitted capabilities and frozen
primitive target records cross into visual delegates. No-target, stale/recycled,
ambiguous and unsupported requests refuse without fallback. Native exceptions
report uncertainty without replay; asynchronous server acceptance and DBus
unique-owner races remain outside the contract.

The original bar/popup layouts and pointer meanings are restored, with only the
reviewed service/identity/capability, excluded-artwork and error/lifecycle seams.
The optional widget can be shown/hidden through transactional Appearance actions,
including empty layouts and relocation; defaults remain the existing twelve
widgets. Read/no-op behavior, writer recheck, exact rollback and drift refusal
are covered with private temporary preferences.

Verification passed: 1,412 unit tests, 24 contained audio cases, 24 frame cases,
desktop, tray/network/tooltip/clock and clean-source regressions, 133 sealed
sources, 24 implementation/documentation prestate backup records, existing
vendor-parent integrity and whitespace checks. Private evidence is in
work/plan-138-tests-final.log, work/plan-138-*-final.log and
work/original-media-138/verification.json. Initial test failures were confined to
fixture popup API substitution, incorrect wheel/glyph witnesses and the isolated
source-copy list; the fixture now substitutes only the media popup owner, not
shared tray PopupCard content. Original wheel direction was preserved.

This request performed no installation, restart, host media command, package,
service/agent activation, native configuration change, commit or publication.
Installed paths/process identity were not probed; prior Plan 135 deployment
verification is historical, not a new runtime/PID-continuity check. Plans
136–138 remain source-only. Native popup/input/focus/grab/pixel/server behavior,
complete asynchronous media errors, device profiles/virtual routing/OSD and the
remaining A/C/D/E integrations remain open under their existing approval gates.
