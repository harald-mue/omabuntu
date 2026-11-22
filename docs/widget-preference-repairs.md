# Widget persistence, queue and navigation repairs

## Status and source

Plan 114 implements the first five actionable findings of the
[widget parity audit](widget-parity-audit.md) in repository source. It does **not**
deploy them, restart the bar, change the desktop or claim complete Omarchy parity.
The source baseline remains Omarchy v4.5.0 stable,
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Original vendor parents are unchanged;
clock/dock derivations and authored-source seals are updated reproducibly.

Plan 117 subsequently installed these repairs alongside the Network adaptation
and restarted only the owned bar. Startup passed, prior releases/prestates are
preserved, and existing preference files remained unchanged. This is local
deployment; the owner subsequently confirmed the everyday persistence,
interaction and multi-output tests in plan 133. See
[current acceptance](project-status.md#owner-reported-acceptance) and the
[deployment record](network-original-surface.md#approved-local-deployment-plan-117).

## Implemented

### Calendar and tray: one shared transactional owner

The existing `AppearanceState` owner now handles field patches for clock and
tray through the allowlisted Appearance backend. Every output receives the same
confirmed state and pending projection. Responses to earlier requests cannot
hide newer pending edits. Failed writes remove their optimistic projection and
surface a preference error; they are not treated as successful saves.

`$OMABUNTU_STATE_HOME/current/bar.json` (default
`~/.local/state/omabuntu/current/bar.json`) gains optional fields:

- `clock_settings`: week-start day, birth year, life expectancy, alternate label
  format and vertical format variants. The authoritative horizontal label format
  remains the existing top-level `clock_format`, so Appearance and right-click
  cycling do not compete with a second clock file.
- `tray_settings`: pinned and hidden identifier arrays, including explicitly
  empty arrays and saved order.

Legacy schema-1 files without those fields remain readable. Field patches merge
under the existing cross-process lock, preserve unrelated/unknown top-level
fields and use the same mode-0600 atomic writes, exact-byte/mode prestate records
and guarded rollback transactions. Invalid existing state is not overwritten;
reads do not create preference files. Birth years and identifiers stay in private
user state and transaction receipts, never in Git or diagnostic plan contents.

The original calendar/clock functions route patches before assigning local or
host settings, preserving declarative bindings. The tray retains its original
upstream QML byte-for-byte and forwards choices through its narrow host adapter.
Its no-adapter fallback is for isolated fixtures; the live `TrialShell` supplies
the shared owner. Writes are blocked until its initial load succeeds.

### Dock and display: user requests are not discarded while busy

Dock absolute edits are queued/coalesced per verb, projected over confirmed
state and drained after the initial read or previous write. The latest pin list,
position and autohide choice remain visible while older requests finish. Backend
failures revert unconfirmed choices and appear in the dock context/settings menu
and log. Storage remains the existing config `omabuntu/dock.json`; no competing
preference store was introduced.

Display brightness/scale mutations are queued ahead of periodic status reads.
Repeated absolute values coalesce, and each scale request retains its original
output identifier. Older read responses cannot overwrite queued user choices.
Failure restores the last confirmed readings while retaining independent pending
requests and showing an error. No automatic mutation retry or configuration
reload was introduced. Runtime-only scaling remains runtime-only.

### Keyboard navigation: fixed, output-local panel groups

Each bar output has its own fixed registry of already mounted panels:

- Center: clock, World Clock, weather.
- Right: Bluetooth, network, audio, display, power.

Tab/Shift+Tab wrap in their group, skipping hidden, disabled, zero-sized,
non-panel or destroyed items. Tray and keyboard-layout indicators are not popup
navigation targets. Controllers now delegate switching instead of silently
ignoring Tab or substituting local section toggles. Existing popout ownership and
OnDemand focus policy remain responsible for dismissal and keyboard ownership.
This does not admit arbitrary widgets/plugins, IPC or new keyboard bindings.

Display section/cursor functions are derived from the pinned original monitor
panel, with the excluded text-size section removed from the visible section list.
The monitor inventory can be navigated, but output enable/disable remains inert
and visibly unavailable; this change does not bypass that existing policy gate.

## Verification

- 1215 unit tests pass, including 19 new tests for field persistence, fresh-process
  readback, empty/reset values, exact rollback, concurrency, failed receipts,
  bounded merged state, pending projections, lost-request regressions, output
  targeting, fixed-registry switching and original display cursor navigation.
- Isolated offscreen QML exercised the actual Appearance adapter and Python
  backend: calendar field patches, two bound consumers, a subsequent Appearance
  label change, tray clear/reset and fresh-process readback passed.
- Another isolated QML check exercised actual dock queue/coalescing, stored order,
  failed-write visibility/reversion and fresh-process readback, and compiled the
  display controller. No host displays, buses or network were exposed.
- The existing tray and desktop-surface isolated suites are rerun against the
  current mirrors. Their synthetic owners/backends are not native focus, pointer,
  Bluetooth, power-policy or monitor acceptance.

The complete real bar's native layer-window backend is not available in the
standalone offscreen fixture. The owner subsequently reported the multi-monitor focus/navigation,
interactive preference and next-login tests working (plan 133). This is human
acceptance for the tested setup, not a new offscreen/native measurement.

## Remaining work and explicit gates

This is not a claim that every omitted upstream feature is fixed. In particular:

- **Bluetooth radio retention:** the difference between BlueZ Powered and
  upstream's persistent rfkill off-state still needs an Ubuntu-specific design,
  ownership/recovery review and explicit approval before any live radio/service
  change. No rfkill or system policy was changed here.
- **Power profiles:** upstream AC/battery-specific profile policy is not silently
  installed over Ubuntu's existing power-profiles-daemon behavior.
- **Monitor policy:** persistent per-output settings, output enable/disable,
  text-size controls and topology changes require their own validated reversible
  design and deployment approval.
- **Other parity boundaries:** per-app audio streams/untyped-source/physical-sink
  routing, automatic Bluetooth audio selection, input-method integration,
  full shell/plugin/layout persistence and omitted services remain feature
  differences. Per-monitor workspace blocks were subsequently implemented and
  deployed in plans 119–120; see [current status](project-status.md).

Capability documentation was reconciled for the touched widget areas. Historical
native-version/acceptance records are not replaced by invented fresh acceptance.
No commit or deployment is implied by these source changes.
