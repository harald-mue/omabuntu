# Original Network surface with Ubuntu adapters

## Status

Plan 116 repairs the source-level gaps established by the
[Network parity analysis](network-widget-parity-analysis.md). **Locally installed
and bar restarted under plan 117; startup verified, native interactive acceptance
still pending.** The implementation is included in published
[v0.2.4](releases.md#v024-release-scope); publication does not establish native
Network or credential/measurement acceptance. The comparison/source pin
remains Omarchy v4.5.0 stable,
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`.

The repair retains original layout/component source rather than composing another
simplified replacement panel. It does not import the full original shell,
registry, Arch helper directory or system-management behavior.

## Main panel

`network-control-frontend-v2` now retains the original:

- Connection hero, portal action, band/DNS sections and nearby-network ListView.
- Four-column connection grid: ping/loss, receiving/sending rates,
  downloaded/uploaded totals, IP and gateway.
- `DetailValue`, `InfoLabel` and `InfoValue` components, including copy targets.
- Seven connection phrases and the original 2800-ms/150-ms/200-ms transitions.
- Network rows, inline PSK prompt, keyboard selection and scroll behavior.

Grid/component/animation blocks are tested against their unchanged original
parent, not merely checked for matching labels. The original nominal width and
main column spacing remain intact. The hero uses the original pure model's
Ethernet-speed formatting and no parenthesized Wi-Fi detail. Native
`NetworkDevice.address` is no longer misrepresented as an IP address.

Ubuntu-only saved Ethernet/VPN access is a collapsed secondary expansion,
visible only when profiles exist. Expanded lists have 144-unit scroll viewports
and follow keyboard selection; empty-state blocks no longer crowd the default
main panel. P toggles expansion; arrows/h/j/k/l use the existing section model.
The custom DNS editor owns focus while open, blocks global panel navigation and
returns focus on submit/Escape. DNS choices remain visible while awaiting their
result, so failed writes have an inline error rather than disappearing behind a
closed popup; this is a deliberate action-feedback difference from upstream.

## Passive Ubuntu data and copy actions

The allowlisted `details <iface>` helper operation reads one validated interface:

- `ip -j -s address show dev <iface>` supplies global IP addresses and available
  link counters. Prefer IPv4, otherwise a global IPv6 address; never use MAC.
- If iproute2 omits link counters, read the bounded Linux sysfs `statistics`
  counters for that same interface. No file writes or fallback probes.
- `nmcli -g IP4.GATEWAY,IP6.GATEWAY device show <iface>` supplies the gateway.
- The read-only Linux sysfs `speed` attribute supplies negotiated Mbps when
  available. Virtual/Wi-Fi interfaces can legitimately have no such value.

Commands have five-second timeouts, JSON is bounded, fields/counters are
validated and partial results identify missing fields. Missing data remains
unavailable in the original cells; it is not replaced with invented values.
The helper reports missing commands/timeouts as explicit failures. A successful
partial collection is not functional/native acceptance.

Original pure model functions calculate rates from counter/time samples and
format bytes/rates. Interface changes, panel close and missing-counter samples
reset the rate baseline, preventing misleading spikes on the next valid sample.
Responses are checked against interface and link generation before publication.
Details polling runs only while Network is open; the existing conditional signal
fallback is unchanged. Profile/DNS/band status refreshes run at a slower cadence.

Copying IP/gateway submits a validated `copy-address` operation to `wl-copy` with
argv only, no shell interpolation. A missing clipboard tool is an error, not a
package-install request. No copy action was performed on the host during testing.

**No ping or packet-loss traffic is enabled.** Both original cells remain mounted
with `--`. Selecting a probe destination and enabling measurement require a
separate explicit decision; restoring layout did not silently admit new traffic.

## Original standalone destinations

Four unchanged MIT source parents were reviewed and imported from the same pin:

| Parent | Staged adaptation |
| --- | --- |
| `shell/plugins/panels/wifiqr/Panel.qml` | `WifiQrView.qml`: original centered scrim/title/white canvas/loading/error/help layout |
| `shell/plugins/panels/speedtest/Panel.qml` | `NetworkSpeedView.qml`: original gauge-overlay wiring |
| `shell/Ui/OverlayWindow.qml` | `Ui/OverlayWindow.qml`: original scale/output lifecycle, OnDemand focus and invoking-output preference |
| `shell/Ui/SpeedTestOverlay.qml` | `Ui/SpeedTestOverlay.qml`: original two-dial cluster, arcs/ticks/needles/readouts, Mbps units, ignition sweep, rerun/error UI; OnDemand focus and explicit output |

The complete downloaded root notice matched `vendor/omarchy/LICENSE` before
import. `upstream/clock-preview.json` records exact URLs, original Git blobs,
hashes, unchanged-source status and versioned derivations. Original English
catalog keys and their catalog URL/hash are recorded there too. Root MIT notices
remain preserved; no QR images, secrets or results enter Git.

Network closes and opens these fixed trusted destinations through lazy Loaders,
not arbitrary plugin identifiers or upstream shell IPC. Window ownership remains
OnDemand, not Exclusive. Neither surface expires on a lifetime timer.

### QR boundary

The matrix backend is pinned to the displayed Wi-Fi interface and verifies it is
still connected rather than silently choosing a different radio. Returned
interface/SSID metadata is authoritative. A four-module quiet zone and the
original white canvas/fixed dark modules preserve contrast and left-to-right
module order independent of theme and text direction. Narrow-screen scaling is
retained from the original layout.

The existing explicit QR action may read a saved PSK inside the helper, but
returns only the matrix and non-secret title/context metadata. The matrix itself
is credential-bearing: no logging, disk cache or report capture is permitted.
Close/re-summon clears it and generation checks reject late replies.
**Plaintext password reveal is deliberately excluded**, including the original
reveal label/button and password-helper dependency. Unknown enterprise Wi-Fi
creation and QR sharing for enterprise security remain excluded.

### Speed boundary

Only explicit summon/Run Again starts the existing bounded Cloudflare backend.
Each download/upload phase has an eight-second curl maximum plus subprocess
timeout; upload is a fixed 512-KiB temporary body. Normal OS/VPN routing is
preserved; the adapter does not bind around a VPN. No measurements ran here.

The original dials/units/phase highlighting and scale/sweep behavior are retained.
The adapter produces an end-of-phase reading rather than upstream's continuous
stream, so the original live-per-second feed is **not** claimed. Closing aborts
and invalidates the run. The standalone Python measurement process kills/reaps
its owned curl group on cancellation/timeout; a Linux parent-death signal also
prevents a hard-killed helper from orphaning curl. This is owned-child lifecycle,
not a system service, global security-policy change or session lifetime timeout.
Rerun starts a fresh bounded measurement; errors leave the panel open.

## Request correctness

Network now uses a bounded serialized queue instead of one overwriteable slot:

- Absolute DNS/band edits and redundant reads coalesce; independent actions do
  not overwrite each other. User mutations precede queued polling reads.
- Each in-flight request retains its own kind, arguments and link generation.
  Acknowledgement of DNS choice A cannot confirm pending choice B.
- Pending projections are computed from the in-flight/queued requests and fall
  back to confirmed values on failure; no permanently stranded `pendingBand`.
- Nonzero exits cannot publish a success payload. Failures are shown without
  logging raw responses, identifiers or credential-bearing matrices.
- Response finalization prevents reentrant polls from overtaking waiting edits.

No automatic mutation retries or service/policy changes were added. The queue is
per widget/output, not a new global NetworkManager transaction/locking service.
Existing profile-specific DNS/band rollback boundaries remain separate from
source-level request correctness and require native acceptance.

## Verification and remaining gates

All **1237 unit tests** pass, including 22 new regressions for original source
blocks, correct IP/MAC semantics, IPv4/IPv6/partial/counter data, read-only fallback,
copy validation, queued edits/acknowledgements, stale interfaces, missing samples,
QR quiet zone/context/late replies, speed phases and owned-child cancellation.
Cancellation tests use a fake local curl executable with **no network**; both
normal termination and helper hard-kill paths are exercised.

The 11 established isolated Wi-Fi fixtures pass. An additional Bubblewrap/
offscreen run exercises actual main-panel content and QML process/protocol
handling with a fake Python helper, all eight visible labels, rates/gateway, collapsed and
bounded expanded profiles with keyboard-driven scrolling, QR scrim/canvas/clear-on-close, and the original speed
gauges/units with two synthetic phase values. It substitutes native window
ownership and network services, not the original visible layout. No host display,
NetworkManager, buses, clipboard, GPU or network is exposed. Private evidence
remains under `work/network-surface-116/`.

The expanded source profile verifies 80 upstream mappings and 126 staged files.
This proves source/protocol/isolated behavior, **not** native focus, pointer,
real clipboard, real gateway/counters/permission behavior, scannable QR, actual
speed results or pixel parity. The backed-up local deployment is complete under
plan 117; interactive comparison remains pending. Shared authored Style/en-US scope,
enterprise/certificate policy, full shell IPC/plugin registry and unapproved
probe/provider behaviors remain explicit limits. No deployment, restart, commit
or push is implied by this implementation alone.

## Approved local deployment (plan 117)

The user approved installation and restart. A private derivative of the verified
running release changed exactly 20 shell files, two helpers and its provenance
record; manager, native runtime and existing fallback remained unchanged. The
standard update transaction backed up the launcher/selectors and retained the
prior immutable release. Private preference/running-record prestates were also
saved before applying. All 1237 tests passed again before deployment.

Only the owned bar restarted, with session lifetime and background restoration
disabled. Identity, loaded/session markers and clean startup were verified;
calendar/tray, World Clock and dock preference files remained byte-for-byte
unchanged. No compositor reload, packages, services, autostart, network mutation,
QR credential reads, speed/ping tests, commit or push. Private deployment and
rollback evidence is under `work/widget-network-deployment-117/`.
