# Network widget parity analysis

## Result and scope

The user's observation is supported by the source: the mounted Network widget is
**not the complete original Network panel**. It retains original sections, but
removes the entire connection-details grid, changes the hero's data contract and
replaces the separate QR/speed-test destinations with small authored inline
sections. Additional always-mounted Ethernet/VPN blocks change the hierarchy.
This is substantially more than an Ubuntu backend adaptation.

Baseline: Omarchy v4.5.0 stable,
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`, compared with the repository after
commit `7cbb684`. `verified_sources()` passes all 76 upstream mappings and 120
staged files, including the unchanged Network parent/model and reproducible
`network-control-frontend-v1` mirror. That verifies extraction integrity, **not**
visual completeness.

This is repository/source analysis, not a screenshot comparison with the user's
running installation. No installed files, live network state, credentials,
provider requests or desktop settings were accessed. No implementation,
deployment, restart, commit or push is part of this request. Plan 114 is still
source-only and did not restore Network visual parity.

## Follow-up

Plan 116 subsequently restores the original grid/hero/phrase presentation,
source-derived standalone QR/speed layouts, secondary profile expansion and a
request-bound queue **in source only**. See [implementation and remaining gates](network-original-surface.md).
The findings below remain the plan-115 baseline, not the repaired source status.

## 1. The missing connection-details block is deliberately excluded

The original `vendor/omarchy/shell/plugins/panels/network/Panel.qml:1386–1436`
contains a four-column grid, with two label/value pairs per row:

| Original detail | Port |
| --- | --- |
| Ping | Removed |
| Packet loss | Removed |
| Receiving rate | Removed |
| Sending rate | Removed |
| Downloaded total | Removed |
| Uploaded total | Removed |
| IP address, clickable to copy | Removed |
| Gateway, clickable to copy | Removed |

These are not hidden by unavailable values or an unusual connection state.
`tools/network_frontend.py:40–86` selects the hero and portal, then resumes at
band/DNS/Wi-Fi; it never includes the intervening details grid. It also excludes
the trailing `DetailValue`, `InfoLabel` and `InfoValue` components
(original lines 2104–2140), including their clipboard targets/tooltips.
All eight detail-label keys occur in the original and none occur in the staged
`NetworkControlView.qml`.

The original keeps ping/loss positions mounted with `--` while readings are
unavailable. Removing the controls entirely is therefore a layout deviation,
not the original unavailable-data behavior.

There is also no supplying data path: local `NetworkPanelController.qml:83–92`
constructs only `type`, `ssid`, `iface` and `ip`. `tools/network_nm.py:384–390`
returns DNS, bands and saved profiles, not gateway, transfer counters, link speed,
ping or packet-loss history. An unchanged `NetworkModel.js` still contains the
pure formatting/throughput/ping helpers, but the local controller does not use
them to populate an original details section. Restoring QML alone would not
restore functional data.

## 2. The retained hero uses different, partly incorrect data

### Wrong hardware-address projection

The port maps `device.address` to `info.ip` and returns that field from
`headerDetail()` (`NetworkPanelController.qml:90,187`). At the pinned Quickshell
commit `2b4501a282689792b62e94f3fb30d8f512324fe6` in
`upstream/source-lock.json`, `src/network/device.hpp` documents `address` as the
**hardware/MAC address**, and `src/network/nm/device.cpp` binds it to
`hwAddress()`. This was checked in the cached workspace build source, not by
querying any device.

Consequently, the hero can show a MAC address in parentheses as if it were the
link detail. It is not an IP-address readout. The original model's
`headerDetail()` shows negotiated Ethernet speed (for example `2.5gbit`) and
intentionally returns no such parenthesized detail for Wi-Fi; its IP address
belongs in the details grid. The port changes both semantics and title length,
which can also elide more of the SSID.

### Connection status reduced to one fixed string

The original keeps seven connection phrases and fades between them every
2800 ms (`Panel.qml:59–68,1027–1048`). The local controller uses the fixed
`network.connectedPhrase` string (`NetworkPanelController.qml:106`); it has
neither the phrase list nor the swap animation. The retained original hero QML
cannot reproduce the original behavior with that reduced controller.

## 3. The section order and space allocation differ

| Stage | Original main panel | Port |
| --- | --- | --- |
| 1 | Hero/actions | Retained original hero/actions, different data |
| 2 | Captive portal when needed | Retained; Ubuntu endpoint |
| 3 | Connection details | **Missing** |
| 4 | Wi-Fi band when applicable | Retained with local backend |
| 5 | DNS choices | Retained with local backend |
| 6 | Wi-Fi section and network list | Custom DNS editor; Ethernet profiles; VPN profiles; inline QR; inline speed result; service note; then Wi-Fi list |

`tools/network_sections.py:74–129` generates the Ethernet/VPN profile blocks.
Their outer columns have no visibility condition: even empty profile arrays
produce an `ETHERNET`/`VPN` header and an empty-state message. This consumes space
where Omarchy goes straight from DNS to the nearby-network list. Populated
profile arrays use uncapped Repeaters, further shifting that list downward.
These are authored additions, not missing original Network sections.

The main width remains `Style.space(380)` and column spacing remains
`Style.space(12)`. The original Wi-Fi ListView and its `Style.space(240)` height
cap are retained. Thus a different nominal popup width or replacement Wi-Fi row
is not the primary source-supported explanation. The overall column has no
whole-panel scroll container; extra profile/inline content creates an additional
height/overflow risk on small outputs. Actual rendered overflow was not tested.

## 4. QR and speed test are not their original destinations

The original routes QR to `bar.shell.summon("omarchy.wifiqr", ...)`, closes the
Network panel and passes its interface/SSID when known (`Panel.qml:559–573`).
Speed test similarly closes the panel and summons `omarchy.speedtest` with a
connection context (`Panel.qml:753–764`).

The port instead keeps Network open and inserts:

- **QR:** a fixed four-pixel module Grid inside the column, using foreground
  modules over a transparent background. There is no explicit quiet-zone or
  dedicated QR card in this local section (`NetworkControlView.qml:623–644`).
  The helper redetects connected Wi-Fi rather than accepting the displayed
  interface as an argument. This is a destination/context/layout replacement;
  actual QR readability has not been established here.
- **Speed:** a small inline title plus `DOWN`/`UP` text
  (`NetworkControlView.qml:645–668`). The helper returns numeric Mbps, but these
  text rows append no units. `speedRunning` exists in the controller but is not
  rendered as progress in this section; the display uses `--` while empty.
  The local helper performs bounded Cloudflare requests only on explicit action.

The original QR/speed plugin implementations are not among the vendored mapped
sources. This analysis establishes the changed routing and local replacement
shape; it does **not** invent their exact original visual content or claim to
have verified their original provider implementations. Any faithful restoration
needs those version-matched sources and license/provenance review before import.
QR data itself encodes credentials; analysis used no real QR or secret.

## 5. Some absent controls are explicit backend/safety boundaries

- Unknown enterprise/802.1X Wi-Fi: the original identity/passphrase flow is
  replaced with refusal. The copied identity field cannot be reached through the
  normal unknown-enterprise row action. Existing saved enterprise profiles can
  still activate. This must not be repaired by inventing certificate/EAP policy.
- DNS: the local helper changes the active NetworkManager profile, not an
  original shell/global DNS service. The Custom choice uses an authored inline
  editor, whereas the original panel delegates to its helper.
- Captive portal: the original surface is present, but opens Ubuntu's known
  connectivity endpoint rather than the original model's
  `http://ping.omacom.io/nm-check.txt`. Older project prose about an Arch endpoint
  is not the stable source's current contract.
- Band and station sections are conditional in the original too. A single-band
  AP with Automatic selected, no Wi-Fi device, or no shareable connection can
  legitimately hide controls. Do not classify every absent band/QR control as
  another extraction omission.

No Tailscale section exists in this pinned original Network panel. A reference
image from another version or plugin set may contain additional differences;
that needs the matching version/image rather than inference from unrelated code.

## 6. Additional confirmed state/interaction defects

The Network helper adapter was not repaired by plan 114's dock/display queues.
It still has just one `queuedKind`/`queuedArgs` slot
(`NetworkPanelController.qml:273–286`), and completion updates use mutable global
pending values (`288–339`). Source-function reproductions with a fake process
confirmed:

1. During an in-flight status read, choose a band and then DNS. DNS replaces the
   queued band command. The band command is never dispatched, while
   `pendingBand` remains set: the panel can remain busy/show a choice never
   applied and suppress subsequent band-status updates.
2. Start DNS choice A, then choose B while A is running. A's successful response
   promotes the current pending B to `dnsProvider` before B has succeeded.
   The saved/confirmed display is not tied to the request being acknowledged.

These are independent of the omitted details grid, but reinforce that retaining
original controls is not sufficient behavioral parity.

QR/speed inline content and the Custom DNS field are also absent from the fixed
section cursor model: `network_sections.navigation()` adds only Ethernet/VPN
navigation. The global `PanelKeyCatcher` is blocked only for the Wi-Fi password
prompt, not custom DNS. Keyboard/editor behavior therefore needs targeted
verification; native focus interference was **not** reproduced in this analysis.

## 7. Shared frame and tests: what the current evidence does not prove

The port retains the original panel width, main column, hero, portal, band/DNS
pills, Wi-Fi ListView, network rows and inline PSK prompt. It is not merely the
older `NetworkStatusView`: that file is an unmounted regression fixture;
`TrialPanel.qml` mounts `NetworkControlView`.

The shared frame is derived from the original `KeyboardPanel`. Its approved
Ubuntu changes deliberately use OnDemand focus without the original Exclusive
prime and unmap on logical close, instead of preserving the original mapped
fade-out (`tools/audio_frontend.py:95–105`). Those affect focus/closing behavior,
not the missing eight-field grid. Shared Style tokens remain authored/fixed
rather than the full original configurable style service. No independent
pixel/color/font/frame acceptance is implied by the retained section source.

Existing tests verify exact extraction, retained hero bytes, selected controls,
backend commands and 11 synthetic Wi-Fi cases. They do not require the eight
metrics, correct hardware-versus-IP semantics, original QR/speed destinations,
rich profile-list height behavior or queued settings acknowledgement. In fact,
the fake device's `address` is populated with an IP-shaped fixture value, hiding
the native property's meaning. Green tests therefore do not contradict these
findings. `docs/network-control.md` documents some omissions, but its broad
original-surface description, old pin/test counts and click-only-helper wording
are not a current comprehensive parity record.

## Recommended correction order, not approval to implement/deploy

1. Restore the original details grid and its helper components at the original
   position; use explicit unavailable placeholders for unsupported readings.
   Correct the hero to the original Ethernet-speed/Wi-Fi semantics.
2. Supply validated Ubuntu data for IP/gateway/counters/link speed and reuse
   original pure formatting/rate logic. Design ping/loss probes separately with
   approved destinations, bounded operations and no silent new network traffic.
3. Stop inserting always-visible profile empty states into the original main
   flow; agree on how Ubuntu-only Ethernet/VPN access is exposed without
   replacing the original hierarchy or removing useful approved functionality.
4. Review/import the matching original QR/speed plugin surfaces, adapting only
   their Ubuntu backend boundaries instead of adding more simplified inline
   panels. Preserve credential and provider approval gates.
5. Repair the Network request queue with request-bound responses/failure state;
   restore phrase transitions and complete keyboard/editor navigation.
6. Add feature-by-feature tests plus synthetic layout/readability checks, then a
   separately approved live comparison against the same-version reference.

Private reproducible fixtures/results are under `work/network-widget-parity-115/`.
The actual-source fake-process checks pass, and all 1215 unit tests pass after
these documentation changes. No live or pixel acceptance is claimed.
