# Separate advanced audio controls and reserve a scrollbar gutter

## Goal and evidence

Implement the owner's approved recommendation: return the ordinary audio popup
to its original hierarchy, move profile/query/recovery disclosures behind an
explicit advanced-page action, and prevent the vertical scrollbar overlapping
content. Compare both supplied screenshots, installed Plan 154 and the original
Omarchy v4.5.0 audio Panel.qml pinned to
ac2690cd7be4f47e4a255f5e2e78d904d436b068. The original already scrolls as needed
and disables horizontal scrolling, but has no appended technical profile block.
Our added block makes overflow occur sooner; the screenshot also shows the
vertical bar touching/covering right-aligned content despite exterior clearance.

## Shape, boundaries and safety

Preserve original normal controls/layout within the same original panel. A compact
Advanced audio action opens a separate page in that panel; Back returns to normal.
Keep grants, disclosures, separate review/Apply and recovery on the advanced page.
Page navigation issues no query/setter/revoke; closing resets page/navigation and
cancels gestures, not pending native transactions. Restrict cursor navigation to
visible page sections. Reserve scrollbar width plus a theme-scaled inner gap only
when content overflows; retain original scroll policies and scrollbar appearance.
Do not claim an unverified Qt-style mismatch or change global toolkit styling.

Back up each source/deployment path with existence/hash/mode. Synchronize strict
derivation/seals and test actual original QML, page/cursor/stale-action/readback and
measured overflow/nonoverflow geometry. Apply only a reviewed narrow derivative
of installed Plan 154, using existing manager locking/drift checks and explicit
session lifetime; all normal/failure-recovery starts disable wallpaper restoration.
Retain Plan 154 as immediate fallback. This request approves the described UI
correction and managed-bar restart, not native audio grants/tests/setters/profiles,
packages/services, compositor/GNOME, bindings/autostart, security, commit/publication.
Existing Plan 152 indicator acceptance remains preserved; audio live acceptance
remains owner-pending.

## Tasks

- [x] Back up source files and compare original/source/installed behavior.
- [x] Implement explicit advanced page, visible-page cursor and scrollbar gutter.
- [x] Add contained page/gesture/cursor and measured gutter regression checks.
- [x] Regenerate seals and pass units/audio/frame/tooltip/clean-source checks.
- [x] Diagnose/back up installation and deploy only the reviewed UI correction.
- [x] Verify owned-bar health, exact installed bytes, preserved state and fallback.
- [x] Document outcome and remaining owner visual/audio acceptance.

## Outcome

The ordinary popup now has one compact Advanced audio action instead of the
expanded technical block. A separate page in the same original panel provides
Back, disclosures, explicit consent, profile review/Apply and recovery. Opening/
returning does not grant or revoke audio access. Closing resets the page and
cancels captured gestures; hidden normal controls cannot receive advanced-page
cursor actions. The original vendor parent remains unchanged; the derived audio
transform is audio-native-input-frontend-v7. The only scrollbar adaptation is
explicit right padding equal to its width plus Style.space(10) when overflowing.
Existing exterior margins, scrollbar appearance and policies remain unchanged.

Passed 1,587 units, 43 isolated audio cases, 39 frame cases, eight tooltip cases,
clean-source and runtime preflight. The new contained case uses an actual
offscreen Window so Qt positioning and scrollbar geometry are exercised, measuring
the inner gap and full-width nonoverflow. It also covers separate page/Back,
closed-page stale capabilities, visible-page cursor, reopen reset and no implicit
grant. Prior gesture, profile, recovery and timeout cases remain green. These are
not native pointer/pixel/hardware/call acceptance.

Installed as updated-and-started with exactly four manifested changes: three
sealed shell files and provenance. All 150 installed sources match reviewed seals.
Only the verified managed session bar was restarted, with session lifetime and
wallpaper restoration disabled in normal and recovery starts. Helpers/runtime/
manager/menu/assets, backed-up preferences and native/profile/control receipts
remain unchanged. No new warnings or unresolved manager/update journals. The
immutable Plan 154 is the immediate verified fallback; Plan 152 is also retained.
No optional native grants/queries/setters/profile changes, packages/services,
bindings/autostart, security change, commit or publication occurred.

Private source/deployment backups and hash/mode/absence inventories, exact delta,
digest-bound plan, reports, startup/process continuity and preservation checks
remain under ignored work/audio-layout-155/. The fixture-count test pre-edit bytes
were reconstructed by reversing its sole recorded 42-to-43 replacement, explicitly
labelled as reconstruction rather than a contemporaneous pre-edit backup.
Owner confirmation of the corrected live layout and the broader audio acceptance
matrix remain separate.
