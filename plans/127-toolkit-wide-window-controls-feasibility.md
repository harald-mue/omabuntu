# Assess toolkit-wide application window controls

## Goal

Assess a central Super+Space > Setup setting for application min/max/close
buttons across application families: hide client controls in Hyprland tiling
and scrolling, retain hyprbars on floating workspaces, and preserve GNOME.
The request is general, not a Chrome-only workaround.

## Evidence and gaps

Compare plans 074 and 080–089, the current menu registry and hyprbars template,
GTK3/GTK4 and libadwaita documentation, Qt Wayland decoration handling,
Electron window-frame APIs, and the Wayland decoration protocol. Omarchy
behavior is pinned to v4.5.0 commit
ac2690cd7be4f47e4a255f5e2e78d904d436b068; plan 086 records that its reviewed
floating-titlebar source does not establish universal client-button suppression.
Chrome findings are version-specific (156.0.8078.79), not proof for Electron
or Edge. No universally effective session-local mechanism is established.

## Proposed shape

Produce an evidence-linked support matrix distinguishing application APIs,
external user controls, compositor decoration negotiation and actual acceptance.
Assess central-menu feasibility without presenting partial toolkit support as a
universal toggle. Record the blockers and the next approval gate.

## Safety and exclusions

Documentation and bounded public-source research only. Keep raw downloaded
sources and retrieval metadata in ignored work/research/. No live inventory,
credentials, browser profiles, private reference reads, package installations,
application launches/restarts, settings writes, session transitions, plugin
reloads, code injection, service/environment changes or commits. No imported
upstream implementation/assets. Do not revive the rejected GTK_MODULES path.
Do not toggle shared GNOME settings at session entry/exit or alter shared GTK
configuration. A plan is not desktop/deployment approval.

## Tasks

- [x] Review existing evidence, menu boundaries and floating-workspace ownership.
- [x] Compare official toolkit/protocol documentation and record source limits.
- [x] Write the cross-toolkit support matrix and central-menu decision.
- [x] Run the unit suite and review the final diff without deployment.

## Outcome

See `docs/toolkit-wide-window-controls.md`. A universal Hyprland-only external
button toggle remains blocked. GTK3 default CSD and Qt 6.10.2 standard Wayland
decorations have partial process-environment candidates, but custom GTK/libadwaita
headers and Electron content require application cooperation. No candidate is
implemented or native-accepted by this assessment. Partial coverage requires
explicit scope agreement; no misleading menu toggle was added.

Official Qt v6.10.2 source was successfully reviewed in qtbase after attempted
qtwayland URLs returned 404. Current GTK4/libadwaita/Electron/protocol docs are
identified as moving or non-host-version evidence, not deployment guarantees.
Raw public sources, response hashes and failed requests are retained privately
under `work/research/window-controls-127/`.

Validation: all 1,297 unit tests pass (8.378 seconds); `git diff --check` passes.
Only this new plan and the new assessment document are added. No runtime code,
menu/configuration, GNOME state, application/profile, launcher, service, plugin,
package, session or commit was changed.
