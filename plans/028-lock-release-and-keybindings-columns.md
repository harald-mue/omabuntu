# Lock release and keybindings columns

## Goal

Stop the manual lock chord from handing held modifiers to Hyprlock, and make
the Super+K list two readable columns that appear in one pass.

## Evidence compared

- On 2026-10-27 two locks ran. The first (`20261027T105951Z`) unlocked and
  exited 0. Its log records `Invalid key down event (stray release event?)`
  twice, then authentication. The chord is `SUPER+CTRL+L` on key press, so
  Hyprlock can see the still-held keys.
- The second (`20261027T110030Z`) reached `onLockLocked` and the password
  prompt, then wrote nothing else and left no `result.json`. The Hyprland
  process was replaced at 13:05, and the machine was power-cycled. No kernel
  GPU hang is recorded. This is not a new lock test.
- Hyprland 0.56.2 `HL.BindOptions` has `release`. That is the documented
  key-up bind for this compositor version.
- Super+K's helper returns 43 rows in about 0.1 seconds. The card paints each
  row as one padded string. The live UI font is Adwaita Sans, which is
  proportional, so the 35-space chord field does not line up. Each
  `ListModel` append lays the row out again.

## Current project gaps

- The lock bind fires while Super and Ctrl are still down.
- The menu has no separate chord and action fields, and the card has no two-column row.

## Safety constraints

- Do not start Hyprlock from the agent. A bind reload is not a lock test.
- Back up `hyprland.lua` before the one-line bind change.
- No idle, lid, suspend, PAM, or screenshot change.
- The menu change is source only until a later, approved shell update. The
  installed release keeps serving the old card until then.

## Proposed shape

1. Set `release = true` on the existing `SUPER+CTRL+L` bind and reload the
   compositor config.
2. Add `chord` and `action` next to the existing label. Draw them as two
   columns. Keep the previous rows on screen and replace the whole list at
   once when the helper answers.

## Exclusions

- Another live lock or unlock attempt.
- Installing or restarting the shell in this change.
- Disabling Hyprlock's screen copy without evidence that the copy failed.
  The second log finished the copy before the prompt.

## Tasks

- [x] Back up and switch the lock bind to key-up, then reload.
- [x] Publish chord and action on each menu row and render two columns.
- [x] Record the stuck lock and the font-column cause.
- [x] Run the unit suite.
