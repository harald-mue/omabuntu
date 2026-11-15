# Audit widget parity against Omarchy 4.5.0

## Goal and evidence

Audit the other staged bar/panel/dock widgets after the World Clock persistence
repair. Compare unchanged vendor sources pinned to Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`, reproducible extraction transforms,
shared Ubuntu controllers/backends, and current tests/documentation. Distinguish
missing persistence from intentionally temporary interaction state, native-service
persistence, excluded unsafe operations and features absent altogether.

## Current gaps and proposed shape

Existing capability tables contain historical process-only descriptions and
pre-stable references. A successful source derivation does not establish feature
parity. Trace each user-facing setting from upstream mutation through the staged
controller to its actual write/read path. Record actionable gaps, safety-driven
exclusions and documentation drift in an English audit report with source paths.
Do not assume every upstream setting must be copied into a local state file.

## Safety and exclusions

Read-only source analysis plus repository report/plan changes only. No desktop
mutation, installed-state inspection, network or provider requests, upstream
execution, package installation, service actions, bar restart, commit or push.
No modifications to the separate reference package. No live/pixel/security
acceptance claims. Machine-specific probe output stays under ignored work/.

## Tasks

- [x] Verify the stable source pin and reproducible staged source integrity.
- [x] Inventory mounted widgets and trace upstream/local persistence paths.
- [x] Compare retained actions and explicitly excluded features for each widget.
- [x] Write a prioritized report and identify stale documentation separately.
- [x] Run the unit suite after report changes and summarize conclusions.

## Outcome

`docs/widget-parity-audit.md` records the findings and implementation order.
All 76 upstream mappings (72 unique parents), authored seals and 120 staged files
verified against the stable pinned profile. Confirmed gaps include process-only
tray choices, dropped calendar fields/host-binding replacement, discarded busy
dock/display requests, missing cross-widget keyboard switching and Bluetooth
radio-retention semantics that differ from upstream. Existing weather, clock
label, battery percentage, dock and workspace-mode persistence was distinguished
from those defects. Native service-owned state was not mislabeled as missing
local JSON persistence.

Actual extracted JS functions reproduced calendar forwarding loss and busy
dock/display request loss with fake backends only. All 1196 unit tests passed.
Private fixtures and logs are under `work/widget-parity-audit-113/`. No runtime
repair, installed-state inspection, restart, commit or push was performed.
