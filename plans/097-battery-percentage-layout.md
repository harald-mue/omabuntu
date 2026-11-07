# Restore battery percentage layout width

## Goal and evidence

Fix the crowded/overlapping battery percentage shown in the user-provided
screenshot. Compare the original Omarchy v4.5.0 power Panel and BarIconButton,
pinned to commit `ac2690cd7be4f47e4a255f5e2e78d904d436b068`, with the adapted
PowerControlView, DesktopPanelController and the right-side bar row.

The original power button reserves two icon slots when showing percentages.
The Ubuntu adapter inherits a fixed 26 px implicit width from
DesktopPanelController; TrialPanel's Row allocates that width to PowerControlView
regardless of the button's larger implicit width. Its anchors force the button
back into the narrow parent, allowing its centered label/icon group to overlap
adjacent content. Existing fixtures construct panels at wide fixed dimensions
and do not exercise the production implicit-width allocation.

## Shape and constraints

Back up affected repository files. Preserve original power-button label, icon,
slot sizing and interactions; adapt only the power view's implicit dimensions to
its original button, reserving at least the measured label/icon group width
so three-digit labels do not overflow the original minimum slot. Extend
contained QML coverage to use actual Row/implicit
geometry, toggle percentages, and check neighbor placement at representative
battery levels including 100%. Update derived source provenance/hash and tests.
No upstream vendor modification, replacement component, UPower/profile action,
real preference mutation, compositor setting, package/service action, commit or
publication. The user subsequently explicitly approved local deployment and a
bar-only restart. Prepare a verified private derivative replacing only the power
view and provenance, back up the current deployment/preferences, and use the
reviewed application update with wallpaper restoration disabled and automatic
selection recovery on startup failure. No compositor reload or timed component
lifetime wrapper.

## Exclusions and verification limits

No changes to power profiles, charging policy, battery readings or shared icon
primitives without evidence. Synthetic geometry checks are not native visual
acceptance. The user must confirm the corrected battery appearance after a
separately approved deployment.

## Tasks

- [x] Back up sources and fix the power view's implicit dimensions.
- [x] Add regression coverage for real row allocation and percentage toggling.
- [x] Update source hash/documentation and run the unit/contained checks.
- [x] Deploy after separate approval and verify startup/preferences/profile.
- [x] Record the user's sign-off for the deployed correction.

## Verification and remaining gate

1107 unit tests and the contained desktop fixture passed. The fixture exercises
icon-only allocation, percentage expansion at 1%, 63% and 100%, actual content
containment and adjacent Row placement, then contraction to icon-only width.
A deliberately restored old power surface was rejected at the intended battery
percentage allocation assertion. Source backups and diagnostic evidence remain
under ignored `work/battery-layout-097/`.

The repository checks did not change the live shell, preferences, devices,
energy profiles or desktop settings.

## Approved deployment

After explicit user approval, prepared a private local derivative changing only
PowerControlView and provenance. The reviewed update completed with a bar-only
restart, no state migration/native transition and wallpaper restore disabled.
The previous release remains available as the rollback selection. Startup and
manifest integrity passed, all three bar outputs and the independent menu
registration are present, and no shell error markers were detected. Relevant
preference presence/bytes/modes and the read-only queried power profile are
unchanged. Private backups, update evidence and verification are under ignored
`work/battery-layout-097/deployment/`.

No compositor reload, preference mutation, power-profile change, package/service
operation, commit or publication was performed during deployment. After the
request to check the corrected appearance, the user explicitly requested closure
of all tasks and a commit. This records user sign-off for this deployed fix;
it does not claim additional automated native visual testing or acceptance of
unrelated features, GNOME coexistence or fresh-machine behavior.
