# Analyze Network widget visual and behavioral parity

## Goal and evidence

Explain the user's observed Network widget differences by comparing the current
port with the unchanged Omarchy v4.5.0 stable Network panel, pinned at
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Trace the derivation, shared frame,
controller properties, backend and tests, not just imported source counts.
Distinguish removed original UI, replacement layouts, conditional visibility,
backend limitations and changes not yet deployed.

## Current gaps and proposed shape

The network extraction deliberately retains only selected original sections and
adds authored Ubuntu sections. The previous broad audit did not exhaustively
compare the Network panel's visual hierarchy or every action/detail. Produce a
focused source-backed report with an original-to-port matrix and prioritized
corrections. Do not mistake a missing widget section for an unavailable backend,
or reproducible extraction for visual parity.

## Safety and exclusions

Repository-only analysis and documentation. No installed-state reads, screenshots,
network scans/provider requests, NetworkManager commands, credentials, desktop
changes, service actions, configuration writes, deployment, restart, commit or
push. Preserve VPN, certificates and existing enterprise policy. Do not modify
the separate reference package. No implementation or live/pixel acceptance.

## Tasks

- [x] Verify the source pin and current reproducible mappings.
- [x] Compare original and derived sections, states, layout and interactions.
- [x] Trace controller/backend visibility and identify test/documentation gaps.
- [x] Record concrete missing/replaced elements and a safe repair order.
- [x] Run the unit suite after documentation changes and report limitations.

## Outcome

`docs/network-widget-parity-analysis.md` records the comparison and repair order;
`docs/network-control.md` links to it without replacing its historical record.
All 76 source mappings and 120 staged files verified. Confirmed the eight-field
connection grid and clipboard controls are excluded, the hero maps the native
hardware address as IP/link detail, connection phrases are static, and original
QR/speed destinations are replaced by authored inline content. Unconditional
Ethernet/VPN profile blocks alter the original hierarchy.

Actual extracted JS with fake processes reproduced overwritten queued band
requests, incorrect DNS response attribution and hardware-address projection.
The native address contract was checked in the workspace's cached source for the
locked Quickshell commit, not through device queries. Private fixtures/results
are under `work/network-widget-parity-115/`. All 1215 unit tests pass.

No functional source, installed state, desktop, network or service was changed.
No screenshot/native acceptance, deployment, restart, commit or push was performed.
