# Repair menu font-role regression

## Goal and evidence

Restore visible rows in Super+Space and Super+Escape after plan 006.
The authored menu derives from Omarchy commit
`03ff1eff3812933f7088484533784d2f63eaf19a`. The regression is in the
Omabuntu font-preview adaptation, not a changed upstream layout.
`CommandMenu.qml` requires a string font role in every delegate, but
`MenuModel.js` displayRow drops the provider's font field and supplies no
fallback for ordinary rows. The previous offscreen log contains
`Cannot create delegate` and `Required property font was not initialized`
while its report incorrectly says passed.

## Shape, constraints and exclusions

Forward the font role with an empty-string fallback for ordinary rows.
Reject delegate creation failures in the offscreen checker. Preserve the
original menu layout, routing and action gates. No installs, configuration
edits, live deployment, restart, commits or session transitions are approved
by this plan. Live replacement requires explicit user approval. Other theme,
fontconfig and wallpaper changes are excluded.

## Tasks

- [x] Add regression contracts and demonstrate failure before the fix.
- [x] Forward the font role and reject delegate errors in the checker.
- [x] Refresh the authored source integrity record and run unit tests plus
      the isolated menu fixture (425 tests pass; stricter fixture passes).
- [x] Update WORKLOG with evidence and pending deployment approval.
- [x] After explicit user approval, package and install release
      `20261025-local.22`, restart only the shell, and verify startup.
      Native shortcut and visual acceptance remain with the user.
