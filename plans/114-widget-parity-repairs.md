# Repair widget parity gaps

## Goal and evidence

Implement the actionable gaps from plan 113 against Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Compare the unchanged vendor clock/tray
surfaces with their staged adapters, the Appearance transaction registry, and
existing persistence/queue tests. Keep original layouts and narrow Ubuntu backend
adaptations; source fidelity is not native functional acceptance.

## Gaps and proposed shape

First implementation slice: persist calendar preferences and tray pin/hide state
through the existing single Appearance owner and transactional current/bar.json
store. Use field patches, preserve clock/host bindings, share state across
outputs, and serialize requests without stale response overwrites. Keep legacy
bar files readable, exact prestate/rollback and startup failures non-destructive.
Add regressions for each field, restart, clear/reset, multiple consumers,
concurrent queued edits and failed writes. Do not duplicate the clock format in
a competing file or import the original unrestricted shell registry.

The implementation also covers dock/display request queues and error handling,
fixed-registry cross-widget keyboard navigation, and capability-document
reconciliation. Native-service parity (Bluetooth radio retention, AC/battery
profile policy, persistent monitor settings and other omitted features) needs
separate concrete designs and explicit live-change gates, not blind activation.

## Safety and exclusions

Repository implementation/testing only. No deployment, active preference reads,
bar restart, compositor reload, service/rfkill/power-policy changes, package
installation, session transition, commit or push. Preserve GNOME, VPN, keyring
and corporate policy. Tests use workspace-local fixtures or isolated fake
backends. No new upstream code/assets or reference-package changes. Existing
upstream system timezone, network endpoint and full-shell exclusions remain.

## Tasks

- [x] Extend validated transactional Appearance state for calendar and tray.
- [x] Wire shared QML patch handling without replacing declarative bindings.
- [x] Add persistence, rollback, startup, shared-state and queue regressions.
- [x] Refresh derivation mirrors/profile seals and document this slice honestly.
- [x] Run the full unit suite and isolated QML checks where available.
- [x] Repair dock/display busy-action queues and surface failures.
- [x] Implement fixed-registry keyboard switching and navigation regressions.
- [x] Reconcile stale capability documentation and plan remaining native deviations.

## Verification and remaining scope

All 1215 unit tests pass, including 19 new persistence/queue/navigation regressions.
Verified source derivations, hashes and unchanged vendor parents. Isolated QML
checks exercised the actual Appearance adapter/backend, shared calendar bindings,
tray clear/reset and fresh-process readback; actual dock queue/failure/restart
behavior also passed, and the display controller compiled. The existing five
tray fixtures and desktop-surface suite pass after the repairs.

A direct full TrialPanel compilation attempt in the standalone offscreen fixture
hit the expected missing native PanelWindow backend. It was not accepted as a
native bar test; supported synthetic surface/controller checks were used instead.
Fixed-registry switching is covered by actual-function tests, not native keyboard
focus acceptance. Private scripts/reports are under
`work/widget-parity-repairs-114/`.

`docs/widget-preference-repairs.md` records the source-only implementation and
remaining work. Bluetooth radio-retention, AC/battery policy, persistent monitor
settings and other explicitly omitted full-parity features remain open; these
checkboxes do not claim they are implemented. No installed state was read or
changed; no deployment, restart, package/service/policy action, commit or push.
