# Original bar port: implementation and remaining work

Normal approved bar runs now use [session lifetime without expiry](bar-session.md).
The timed launches and process/deployment observations recorded below are
historical, not an assertion of the current autostart/session state. For the
owner's accepted everyday and VM tests and remaining source differences, see
[current project status](project-status.md).

The complete Omarchy bar is **not finished**. A complete bar means usable
panels and their real backend semantics, not decorative status symbols. The
current experimental entry is still TrialShell, not the original shell.qml.
Workspace slots cycle tiling, scrolling and floating with the original glyphs.
See [workspace modes](workspace-modes.md) and the optional
[monitor-local policy](monitor-local-workspaces.md), published in
[v0.2.4](releases.md#v024-release-scope).

Current [v0.2.5](releases.md#v025-release-scope) adds the original compositor
activation-focus default and a separately confirmed installer/update rollout.
The owner confirmed the local Chrome app-grid interaction after enabling that
policy; the grid's desktop launch chain is unchanged. This is not complete shell
or per-application activation acceptance; see [focus-policy boundaries](browser-launch-focus-parity.md).

## Fidelity correction after user feedback

The user rejected the overall quality of the authored partial panels. Original
primitives alone are not a faithful port. Further work must use the original
layout/components, adapting only reviewed Ubuntu backend and safety boundaries,
not add more unrelated replacements. [Original horizontal section geometry](bar-frame.md)
is integrated. Plan 134 adds source-only original keyed WidgetPool ownership,
a closed individual Component registry, shared five-section layout persistence
and layout-order navigation. The existing widgets share one per-output bar API.
Conditional original-model move/remove operations now reject stale writes and
recover shared pending state. The original widget pointer/ghost/poof and
open-panel surfaces now use that guarded write seam in source, together with
original stable full-screen/idle-input-strip ownership. Full plugin/theme
services and new native input/visual acceptance remain unresolved;
successful unit tests do not establish visual quality or native acceptance.

The first correction is the [source-derived audio output frontend](audio-output-port.md):
original hero/output/device markup, cursor surfaces, switch, typography, lazy
keyboard panel and scroll behavior replace the authored output popup. This is
not complete audio or shell parity; typed input was subsequently added. That initial Network
status-only checkpoint was superseded by the original-source Network adaptation
in plans 116–117, included in v0.2.4; the owner reports the existing everyday
network interaction working under plan 133.

## Original tray, now integrated

Tray.qml (920 lines) and TrayModel.js from Omarchy commit
03ff1eff3812933f7088484533784d2f63eaf19a are staged unchanged. The drawer,
pinned icons, symbolic icon tinting, popup menus, nested submenus and
pin/hide management are original code. PopupCard, BarIconButton,
BarIconContent, IconContentBounds, Button, BorderSurface, BorderOverlay,
Border and BorderGeometry are also unchanged upstream files.

All eleven additions were fetched individually from the pinned public source,
matched against the pinned Git tree and reference bytes, and reviewed before
import. No private configuration or assets were copied. Their exact origins,
lengths, Git blobs and SHA-256 hashes are in upstream/clock-preview.json;
vendor/omarchy/LICENSE retains the full upstream MIT notice.

PortTrayHost is a deliberately restricted wrapper, not a replacement tray.
Its standalone owner retains the following boundaries. In plan-134 source, the
real registry supplies the common bar API instead; the original tray still has
no arbitrary command/module loader or automatic application startup:

- Supplies geometry, palette, popup coordination and tooltips.
- Originally stored pin/hide choices in memory only. Plans 114/117 added the
  shared transactional preference adapter; persistence is owner-accepted in
  plan 133.
- Does not offer a command runner or configuration file writer.
- Does not change application registration or start applications automatically.
- Uses Quickshell's StatusNotifier host/watcher and live application menus.
  Selecting an application's menu action belongs to that application; these
  actions can change application state and are not a read-only security boundary.

Unpinned icons live in the original expanding drawer. Hover over the chevron
to reveal them; right-click it for pin/hide management. Left/middle/right click
and wheel events follow the original application's StatusNotifier API.
Cloudflare has an active item titled warp-taskbar on this session's watcher.
No VPN connection or corporate settings were changed.

## Validation

- The initial tray checkpoint had 216 Python contracts; current validation is
  tracked in [project status](project-status.md).
- The [app launcher first-open fix](app-launcher.md) reacts to queued catalog
  publication; seven actual Qt cases include a private native DesktopEntries
  catalog. No host application or shortcut is executed by those tests.
- The [source-derived tooltip correction](tooltip-port.md) is activated. Original
  independent popup anchoring replaces the authored bare Controls ToolTip;
  seven isolated cases do not prove native hover acceptance.
- The [horizontal section layout](bar-frame.md) is source-derived; plan 134's
  twenty-four isolated Qt cases cover geometry, original pointer-handler bodies,
  ghost/settle/poof, stable/guarded widget moves, real Appearance conflict
  recovery, empty/missing admissions, removal, output-
  local pools/navigation, real registry compilation with synthetic ownership,
  and an intentional failure. No native layer/session is started.
- The [audio output port](audio-output-port.md) now uses source-derived original
  layout/control markup, native output actions and twelve isolated fake-node Qt
  fixtures after plan 134's source-only playback stream slice. Offscreen fixtures replace native surface ownership, not controls.
- The [network control port](network-control.md) replaces the live status popup
  with the original connection hero, list and row. Wi-Fi connect, passphrase,
  disconnect, forget and radio toggle use Quickshell's NetworkManager API.
  DNS, band, QR, a capped speed test, the Ubuntu captive-portal URL, and saved
  Ethernet and VPN profiles are included. New 802.1X profiles stay out. The older
  [status slice](network-status-port.md) remains a regression fixture.
- tools/check_tray_port.py is plan-only unless --run and --build-dir are given.
- Five isolated fixtures cover empty, active and passive items, pin/hide/restore,
  and an intentional assertion failure (exit 42).
- The fixture replaces only the tray import with a synthetic service in its
  private staged copy. Production vendor/staged bytes remain unchanged.
- The existing sealed clock-preview suite still passes all five cases.
- Native run work/clock-trial/20261024T133145.096302Z is one Quickshell process,
  pid 334744, with three 26px top layers and a 3600-second grant. All three
  outputs retain reserved [0, 26, 0, 0]. Super+Alt+Space remains registered.
- The live native host/watcher belongs to that process. The portal still warns
  that org.quickshell has no registered app info; this is not hidden or fixed.
- Live application menus and pixel fidelity need interactive acceptance;
  fixture success alone is not that acceptance.

Rollback: stop only this verified TrialShell process. The prior staged profile
at work/clock-trial/20261024T131041.186886Z remains unchanged. Stopping removes
the tray host and all trial surfaces; application processes remain running.
No installed config file, login, default session, autostart, package or service
unit was edited. ~/.config/hypr/hyprland.lua retains its October 22 timestamp.

## Completion backlog

| Area | Current state | Required before claiming completion |
| --- | --- | --- |
| Tray | Original code integrated; shared transactional pin/hide preferences implemented in source (plan 114; locally deployed by plan 117) | Existing everyday interaction/persistence accepted by owner (plan 133); not every third-party tray action |
| Bar frame/theme | Original horizontal/center geometry, watched palette with 250 ms OutCubic behaviors, background looks/bar-off flag; plan 134 adds source-only keyed pools, closed individual registry, shared layout persistence/API and layout-order routing | Original widget pointer/ghost/poof source is restored but not deployed or natively accepted; arbitrary plugin/full theme ownership, bar-edge relocation, nested tray and notch/vertical/blur policies remain out |
| Workspaces | Original monitor-local blocks/slots, widget and bindings are implemented, opt-in and locally deployed under plan 120; user reports tried navigation/cross-monitor operations working | Owner reports docking/hotplug and fresh-login tests working (plan 133); legacy global mode still requires explicit opt-in/migration |
| Workspace modes | Saved modes, startup restoration and floating membership/ownership are implemented | Continue native regression acceptance; not complete original helper parity |
| Floating mode/titlebars | Native integration and floating dock are implemented separately from the widget surfaces | Preserve existing reviewed plugin/profile management; plan 114 makes no native/plugin changes |
| Network | Original grid/hero/phrase transitions and standalone QR/speed layouts restored (plan 116), locally deployed (plan 117) and published in v0.2.4; bounded Ubuntu details/actions, queued requests and secondary profile expansion | Existing everyday interaction accepted by owner (plan 133); ping/loss probes, plaintext password reveal, enterprise creation and original helper execution remain excluded; see [implementation](network-original-surface.md) |
| Audio | Source-derived original output/input layout, cursor controls, peak meter and native volume/mute/preferred-device actions | Existing output/input controls accepted by owner (plan 133); original per-app streams added in source only under plan 134, not installed; untyped-source fallback, profiles, physical-sink resolver and original helper/OSD parity remain incomplete |
| Bluetooth/monitor/power | Original derived surfaces mounted with Ubuntu-native controllers | Existing Bluetooth/brightness/runtime-scale interaction accepted by owner (plan 133); Bluetooth radio-retention, AC/battery policy and persistent monitor configuration remain separate gates |
| Keyboard layout | Original widget vendored byte-identically (single reviewed visibility deviation), mounted between tray and Bluetooth; xkb cycling through the allowlisted run | xkbcli 1.13.1 is installed in the documented development setup; input-method (fcitx) indicator deliberately not ported |
| Clock/calendar | Derived original calendar; shared transactional calendar fields and binding repair implemented in source (plan 114; locally deployed by plan 117); sealed label stays read-only | Existing interaction/persistence accepted by owner (plan 133). No timezone helper, shell.json writes, IPC, or calendar hotkey |
| Indicators/menu | Menu button at the left edge: original BarIconButton with the extracted U+E900 mark, left click opens the command menu's root route, right click opens a terminal | Native click acceptance; no Arch package or system-management routes
| Elsewhen | Original panel derived to the right of the clock; Cities and preferences persist in shared, backed-up Omabuntu state (plans 111–112; locally deployed with clean startup) | Existing interaction/persistence accepted by owner (plan 133). No weather fetch, GitHub profiles, notifications, or system timezone change |
| Weather | Original panel after Elsewhen, Celsius/km/h, 15-minute refresh; original city editor, wttr.in/IP location and Open-Meteo city search/forecast | Location-parity version deployed with clean startup; native editor acceptance pending. Notification actions and IPC remain out |
| Agents | Not implemented | Dependency, notices and asset decisions |
| Updates | Ubuntu application-update review/menu is implemented; Arch management routes are excluded | Future rollout retains explicit approval and rollback; never pacman or Omarchy migrations |

Plan 114 also implements dock/display request queues, visible failure handling
and fixed-registry keyboard panel switching in source. See the
[repair status and remaining deviations](widget-preference-repairs.md).
Plan 117 subsequently deployed those repairs and the Network source changes,
with backups and a verified bar-only restart. The owner subsequently confirmed
the everyday interaction/persistence tests in plan 133; separate policy gates
remain unchanged; see [deployment status](network-original-surface.md#approved-local-deployment-plan-117).

### World Clock preference storage (plan 111)

The source implementation saves Elsewhen cities, their order and people labels,
home selection and display preferences in
`$OMABUNTU_STATE_HOME/settings/elsewhen.json` (default
`~/.local/state/omabuntu/settings/elsewhen.json`). All outputs share one adapter;
loading completes before default cities can be seeded. An explicitly empty city
list stays empty after restart. Globe-only jump destinations remain temporary,
as upstream intended.

The fixed Python helper validates bounded settings and rejects symlinked paths.
Writes replace the file atomically with mode 0600, retain the previous bytes under
`backups/<stamp>/elsewhen.json`, and record prior existence in `operations.jsonl`.
It does not write upstream shell.json or change the machine timezone. Malformed
existing state is not overwritten. Load/save errors are logged and shown in the
World Clock button tooltip; recovery from a backup is explicit, never automatic.
Rapid edits are serialized, with the newest pending snapshot retained. Separate
bar processes do not live-sync state; deployment should maintain one bar owner.

Plan 112 deployed a narrow private derivative of the installed release with a
bar-only restart, unchanged native runtime and no wallpaper reapplication.
Bundle integrity, clean startup and creation of valid private settings state
were verified. The owner subsequently reported the everyday World Clock
interaction/persistence and next-login tests working in plan 133.
Existing process-only cities cannot be automatically migrated from an already
running old bar by this change.

The completion request is not treated as permission to change login, install
packages/plugins, edit active Hyprland Lua, weaken authentication, disconnect
the VPN, or activate lock/idle/suspend. Those remain explicit approval gates.
