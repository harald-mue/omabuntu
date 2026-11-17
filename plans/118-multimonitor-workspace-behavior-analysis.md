# Analyze multi-monitor workspace behavior

## Goal
Explain the user's uneven workspace distribution and compare the current global
workspace adapter with original Omarchy multi-monitor behavior.

## Evidence and gaps
Compare read-only Hyprland 0.57.0 IPC (monitor/workspace placement and binding
metadata), repository profiles, LiveStatus.qml, WorkspaceSwitcher.qml and
Omarchy v4.5.0 stable commit ac2690cd7be4f47e4a255f5e2e78d904d436b068.
The local adapter deliberately uses global IDs and six visible slots; upstream
uses monitor-local slots backed by blocks of ten. Existing documentation still
references the older component baseline in places. IPC binding arguments are
opaque callback handles and do not establish their captured Lua parameters.

## Shape and safety
Read sources and query state only. Explain global IDs, monitor ownership, focus,
window moves and layout modes separately. Keep machine-specific state and raw
IPC out of tracked documents. Do not read external personal configuration,
change configuration, dispatch actions, reload, restart, install or commit.
No third-party code/assets will be imported into the product.

## Exclusions
Implementation, live interaction tests, migration, fixed monitor assignments,
hotplug acceptance and claims about the exact historical sequence of creation.

## Tasks
- [x] Inspect local workspace adapter, profiles and existing documentation.
- [x] Query current monitor/workspace placement and binding metadata read-only.
- [x] Verify pinned upstream monitor allocation and keyboard semantics.
- [x] Explain the root distinction and options without applying desktop changes.

## Findings
The original stable monitor-workspaces.lua and bindings/tiling.lua confirm
monitor-local slots, persistent physical-monitor identities, blocks of ten,
local focus/window moves, explicit directional monitor moves and unplug/return
reconciliation. The upstream bar initially shows five slots and adds existing
higher slots and visiting workspaces. The local bar instead focuses global IDs
1-6 and highlights the globally focused workspace, not each output's view.
Uneven global-ID distribution is therefore compatible with the local model;
creation/move history is not recoverable from a state snapshot. The recommended
future direction is coordinated original monitor-local behavior across compositor,
keyboard, bar and saved layouts, not cosmetic renumbering alone. No deployment
or implementation is authorized by this analysis.
