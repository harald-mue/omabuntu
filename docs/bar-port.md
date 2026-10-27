# Original bar port: implementation and remaining work

Normal approved bar runs now use [session lifetime without expiry](bar-session.md).
The timed launches recorded below are historical; no autostart has been configured.

The complete Omarchy bar is **not finished**. A complete bar means usable
panels and their real backend semantics, not decorative status symbols. The
current experimental entry is still TrialShell, not the original shell.qml.
Workspace slots cycle tiling, scrolling and floating with the original glyphs.
See [workspace modes](workspace-modes.md).

## Fidelity correction after user feedback

The user rejected the overall quality of the authored partial panels. Original
primitives alone are not a faithful port. Further work must use the original
layout/components, adapting only reviewed Ubuntu backend and safety boundaries,
not add more unrelated replacements. [Original horizontal section geometry](bar-frame.md)
is now integrated, but full frame/theme/registry remains an unresolved gap;
successful unit tests do not establish visual quality.

The first correction is the [source-derived audio output frontend](audio-output-port.md):
original hero/output/device markup, cursor surfaces, switch, typography, lazy
keyboard panel and scroll behavior replace the authored output popup. This is
still output-only and not complete audio or shell parity. Network remains the
restricted authored status view until its original panel is properly ported.

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

PortTrayHost is a deliberately restricted owner, not a replacement tray:

- Supplies geometry, palette, popup coordination and tooltips.
- Stores pin/hide choices in memory only. Restart resets those preferences.
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

- 216 Python contracts pass; they do not start Qt or DBus.
- The [app launcher first-open fix](app-launcher.md) reacts to queued catalog
  publication; seven actual Qt cases include a private native DesktopEntries
  catalog. No host application or shortcut is executed by those tests.
- The [source-derived tooltip correction](tooltip-port.md) is activated. Original
  independent popup anchoring replaces the authored bare Controls ToolTip;
  seven isolated cases do not prove native hover acceptance.
- The [horizontal section layout](bar-frame.md) is source-derived; seven actual
  Qt cases cover supported widths, narrow clipping, long titles and centering.
- The [audio output port](audio-output-port.md) now uses source-derived original
  layout/control markup, native output actions and eight isolated fake-node Qt
  fixtures. Offscreen fixtures replace native surface ownership, not controls.
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
| Tray | Original code integrated | User checks drawer, Cloudflare icon and menus; persistent pin/hide storage needs its own reviewed project path |
| Bar frame/theme | Source-derived original horizontal/center section geometry; watched theme palette state with the original 420 ms OutCubic color behaviors, opaque/glassy/none background looks and the bar-off flag | Full original theme/frame/registry, native visual acceptance, reviewed notch/vertical/gesture policies; blur behind a glassy bar stays user-owned (Hyprland 0.56 has no runtime layerrule) |
| Workspaces | Global 1-6 and native focus call | Original per-monitor blocks of ten and layout glyph, with verified backend |
| Workspace modes | Not implemented | Port workspace-modes.lua, helpers/paths dependencies, per-workspace restoration, safe window-tag reversal and a separate approved config change |
| Floating mode/titlebars | Not implemented | Review original plugin requirement; do not install or reload blindly |
| Network | Native status popup with original glyph model and original UI primitives; not the original full panel | Native click acceptance. No new VPN profiles, certificates, firewall, proxy, or Arch helpers |
| Audio | Source-derived original output layout, shared cursor/keyboard controls and native volume/mute/preferred-device actions | Native pointer/focus/reopening acceptance; input, streams, profiles, physical-sink resolver and media/OSD remain unported |
| Bluetooth/monitor/power | Not implemented | Review original panels and existing Ubuntu backend ownership; no idle/suspend/lock activation |
| Keyboard layout | Original widget vendored byte-identically (single reviewed visibility deviation), mounted between tray and Bluetooth; xkb cycling through the allowlisted run | xkbcli briefs need an optional package decision (fallback label is the description's first word); input-method (fcitx) indicator deliberately not ported |
| Clock/calendar | Derived original calendar on left click; sealed label stays read-only | Native click acceptance. No timezone helper, shell.json writes, IPC, or calendar hotkey |
| Indicators/menu | Menu button at the left edge: original BarIconButton with the extracted U+E900 mark, left click opens the command menu's root route, right click opens a terminal | Native click acceptance; no Arch package or system-management routes
| Weather/Elsewhen/agents | Not implemented | Dependency, notices, network/provider and asset decisions |
| Updates | Arch route excluded | Ubuntu-native, reviewed status/actions if agreed; never pacman or Omarchy migrations |

The completion request is not treated as permission to change login, install
packages/plugins, edit active Hyprland Lua, weaken authentication, disconnect
the VPN, or activate lock/idle/suspend. Those remain explicit approval gates.
