# Match Omarchy's left bar

## Goal and evidence

Make the top bar's left side match Omarchy: the menu mark, then workspaces. The user pointed at the live bar and asked to drop the "Apps" button and the focused window title.

Pinned Omarchy `03ff1eff` default order is `left: menu, workspaces`. Neither control is a window-title readout or an app-grid button. Omabuntu adds both in `config/shell/preview/LiveStatus.qml`, mounted after `MenuButton` in `TrialPanel.qml`. The app grid stays reachable from the command menu and the floating dock.

## Gap and proposed shape

Remove the Apps button, the title text, and the `openApps` wiring that exists only for that button. Leave `LiveStatus` as the global workspace row with its width budget. Keep the menu button, the clock, and the right-side order unchanged.

## Safety and exclusions

No Hyprland edit and no package install. The user then asked to stop Quickshell and apply the change. The recorded bar was stopped, the three installed shell files were replaced from a private backup, release integrity was verified, and the bar was started again. No commit until the user asks. The app launcher, dock, and command-menu Apps row stay.

## Tasks

- [x] Remove the Apps button and window title from the left bar.
- [x] Update provenance, tests, the bar notes and the work log.
- [x] Run the unit suite (566 tests pass).
- [x] Stop the recorded bar, replace the installed shell files, and start the bar again.
