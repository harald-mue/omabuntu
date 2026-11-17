# Restore the original Network surface with Ubuntu adapters

## Goal and evidence

Implement the corrections from plan 115 against Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Compare the original Network panel,
model and matching QR/speed destination sources with the current extraction,
Ubuntu NetworkManager helper, pinned Quickshell API and tests. Preserve original
component/layout source with narrow reviewed adapters, not replacement panels.

## Current gaps and proposed shape

Restore the original connection grid, copy targets, Ethernet-speed header and
phrase transitions. Supply bounded read-only Ubuntu IP/gateway/link/counter
readings; reuse original formatting/rate logic and placeholders for unapproved
ping/loss measurements. Replace the single pending request slot with a serialized
request-bound queue. Retain Ubuntu profile functionality behind an explicit
secondary expansion rather than always-visible empty blocks. Review matching
original QR/speed source, license and dependencies before admitting any new
upstream files; use original destination layouts with bounded local backends
where supported, and document unresolved dependencies instead of inventing UI.
Add source, backend, queue and isolated QML regressions and refresh provenance.

## Safety and exclusions

Repository implementation and isolated tests only. No installed-state reads,
real NetworkManager actions/scans, credential reads, live QR, speed measurement,
ping, package installation, service/policy changes, deployment, bar restart,
compositor reload, commit or push. Source-document retrieval is not permission
for measurement traffic. Preserve enterprise/VPN/certificate policy and existing
user preferences. No modification of the separate reference package. New source
must retain its license and recorded origin. Source fidelity is not live/pixel
acceptance; normal desktop components retain session lifetime, not timed runs.

## Tasks

- [x] Review original destination sources/license and relevant native API contracts.
- [x] Restore original details/hero/phrase presentation and secondary profiles.
- [x] Implement bounded read-only details and request-bound queue/error handling.
- [x] Adapt original QR/speed destinations or document precise blockers.
- [x] Add regression tests and refresh generated mirrors/provenance/notices.
- [x] Run full unit and available isolated QML suites; record remaining gates.

## Outcome and verification

`docs/network-original-surface.md` records the implementation and remaining gates.
The complete original connection grid/components and phrase animations are
retained. Correct IP/gateway/counter/link-speed readings replace MAC projection;
ping/loss cells stay mounted with unavailable placeholders and no probes.
Secondary profiles are collapsed, bounded, keyboard navigable and scroll with
selection. The queue preserves independent actions and request-bound results.

Four unchanged original MIT parents now supply the QR scrim and speed gauge
layouts and their shared window dependencies. Their root notice matched the
preserved notice before import. Exact origin/blob/hash/transform records are in
the profile. Explicit exclusions include plaintext password reveal, continuous
speed streaming, upstream helpers/registry, enterprise creation and unapproved
probes. OnDemand ownership and session-lifetime components are preserved.

All 1237 unit tests pass (22 new), including fake-process cancellation and helper
hard-kill tests without network. All 11 established Wi-Fi fixtures, five tray
fixtures and the desktop-panel isolated suite pass. An additional isolated QML
check verifies the actual original grid, rates, secondary-profile keyboard/scroll
behavior, QR white canvas/clearing and original speed gauges/units against a fake
Python helper. Native ownership/services are synthetic, not live acceptance.
The expanded source profile verifies 80 upstream mappings and 126 staged files.

Pinned Quickshell source confirms hardware-address semantics, monitor refresh
and window geometry APIs, and Process termination/kill behavior. Private source
retrieval, scripts and reports remain under `work/network-surface-116/`. No live
settings/device reads, credentials, scans, speed/ping requests, desktop changes,
packages, services, deployment, restart, commit or push. A backed-up deployment
and native comparison remain separate approval gates.
