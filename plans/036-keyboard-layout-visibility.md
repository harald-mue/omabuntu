# Match Omarchy keyboard-layout visibility

## Goal and evidence

Hide the top-bar keyboard-layout label on a single-layout seat, as Omarchy does. The user asked for that behavior after the label stayed visible at the right of the bar.

Pinned Omarchy `03ff1eff` shows `omarchy.keyboard-layout` only when `showIndicator` is true: more than one layout, or more than one input method. This seat has `kb_layout = "de"` and the restricted input-method stub, so upstream hides the label. Omabuntu splice `keyboard-layout-widget-v1` adds `alwaysShow` (default true) in `config/shell/preview/KeyboardLayout.qml`, and `TrialPanel.qml` passes that setting. The active local shell copies are the same splice.

## Gap and proposed shape

Make the preview widget a byte copy of the vendored parent. Record `stage_transform` `none` and the matching staged hash. Remove the `alwaysShow` setting from the trial bar. Drop the splice helper. Keep the widget mounted between the tray and Bluetooth; visibility stays the upstream rule. Update the capability note and work log.

## Safety and exclusions

No Hyprland config edit, no second `kb_layout`, no input-method daemon, no package install, no compositor reload, and no shell restart in this change. A backed-up replacement of the two installed shell files may update the release the next start reads; it does not by itself reload the running bar. No commit.

## Tasks

- [x] Remove the visibility splice and prove the preview matches the vendored parent.
- [x] Update provenance, the trial mount, tests, the capability note and the work log.
- [x] Run the unit suite (566 tests pass).
- [x] Back up and replace the two installed shell files, then verify release integrity, without restarting the bar.
