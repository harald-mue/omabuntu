# Fit the audio panel to available height and polish advanced navigation

## Goal and evidence

Correct the owner's rejected Plan 155 layout using the supplied screenshot and
installed release. Compared with original Omarchy v4.5.0 audio Panel.qml pinned to
ac2690cd7be4f47e4a255f5e2e78d904d436b068, our explicit gutter exposes the original
560-unit cap: normal device content overflows and the advanced entry is clipped.
The nested normal-page content also needs an explicit scroll extent rather than
relying on inferred ScrollView sizing. An invisible/faded scrollbar is not proof
that content fits. Preserve original device controls and advanced grant semantics.

## Proposed shape and safety

Let the existing original KeyboardPanel fit the entire content to the available
screen height without the extra audio-only cap. Explicitly bind the ScrollView
content height and reserve balanced inner clearance only if content genuinely
overflows; never introduce a permanent one-sided gutter. Retain functional
scrolling for small screens and long advanced pages. Use the original Button icon
slot for compact advanced/back navigation, not a replacement panel or theme.

Back up all affected paths with existence/hash/mode, preserve original vendor
parents and synchronize narrow derivation/seals. Test populated original device
rows, full-height fitting, centered nonoverflow, small-viewport last-entry scroll
reachability, navigation and unchanged consent. Deploy only reviewed UI/provenance
changes with existing lock/drift guards and managed-bar-only session-lifetime
restart; disable wallpaper in normal and recovery starts. Retain Plan 155 fallback.
No audio grants/queries/setters/profile changes, package/service, GNOME/compositor,
bindings/autostart, security, commit/publication. Owner visual acceptance remains
separate from contained checks. This request authorizes the described correction.

## Tasks

- [x] Diagnose and back up source and installed state.
- [x] Correct height/scroll extents/centering and icon navigation.
- [x] Verify populated fitting and constrained scrolling with original components.
- [x] Pass seals, units, audio/frame/tooltip/clean-source and runtime preflight.
- [x] Deploy the narrow backed-up correction and verify state, health and fallback.
- [x] Document the outcome and request owner visual confirmation.

## Outcome

Removed the additional audio-only 560-unit height cap while retaining the original
KeyboardPanel available-screen fitting. Explicit contentHeight/contentWidth now
bind nested pages to the real Flickable extent. Left/right padding are equal and
zero when content fits; only genuinely overflowing content reserves symmetric
clearance. The ordinary advanced entry and Back use the original Button icon
slot with settings/back glyphs, short labels and explanatory hover tooltips.
Original vendor parents, controller/backend, grants and native actions are unchanged.
The narrow derived audio transform is audio-native-input-frontend-v8.

Passed 1,588 units, 43 contained audio cases, 39 frame cases, eight tooltip cases,
clean-source and runtime preflight. The actual offscreen-window layout case now
uses twelve device rows (more than the reported setup), proves fitting beyond
the old cap, fully visible icon navigation without scrolling, zero nonoverflow
reservation and equal overflow clearance. At a deliberately constrained viewport
it scrolls to and measures the entire last action, not merely scrollbar presence.
Existing separate-page/no-grant/stale-action and device/recovery cases remain green.
This does not replace owner native pixel/pointer/audio acceptance.

Installed as updated-and-started with exactly three manifested changes: two sealed
shell files and provenance. All 150 installed seals match source. Only the owned
managed bar was restarted with session lifetime, no wallpaper restoration, zero
new warnings and no open manager/update journals. Settings and native/audio
receipts are preserved; helpers/runtime/manager/menu/assets are unchanged. Plan
155 is the verified immediate fallback, with Plan 154 also retained. No native
audio grants/queries/setters/profiles, package/service, bindings/autostart, security,
commit or publication changes.

## Subsequent owner visual acceptance

The owner explicitly confirmed that the corrected audio view is okay. Record the
Plan 156 audio-view layout as owner-reported visually accepted, closing its visual
confirmation item. This does not establish the separate functional live matrix
for profiles/recovery, virtual inputs, DSP, calls, hotplug or OSD coexistence, nor
security/recovery acceptance. No desktop change or new native grant accompanies
this documentation update.

Private source/deployment hash/mode/absence backups, exact delta and digest-bound
plan, test/preflight reports, preserved-state checks and process/log health remain
under ignored work/audio-layout-156/. No raw machine-specific evidence is published.
