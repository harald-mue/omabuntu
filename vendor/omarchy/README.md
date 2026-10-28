# Selected Omarchy source

Selected unchanged files from commit 03ff1eff3812933f7088484533784d2f63eaf19a:

- shell/plugins/panels/clock/Model.js: pure date/format math.
- shell/plugins/panels/clock/BarWidget.qml: original clock parent, provenance only.
- shell/Ui/BarWidget.qml: original bar-widget base.
- shell/Ui/WidgetButton.qml and shell/Ui/OpticalGlyph.qml: original presentation.
- shell/plugins/bar/widgets/Spacer.qml: original geometry leaf.
- shell/plugins/bar/widgets/Workspaces.qml: original workspace widget. The
  staged switcher keeps its glyphs and click-to-cycle rule. The Omarchy layout
  scripts are not staged.
- bin/omarchy-hyprland-workspace-layout-toggle: reference for the cycle order
  only. It is not executable from the bar and is not staged.
- shell/plugins/bar/widgets/Tray.qml and TrayModel.js: complete original tray.
- shell/plugins/panels/network/Model.js: unchanged network presentation model;
  its dormant command strings and portal URL are not used by this port.
- shell/plugins/panels/network/Panel.qml: unchanged parent for the generated
  connection frontend. DNS, band, helpers, QR, speed tests and new 802.1X
  profile creation are not staged.
- shell/Ui/PanelActionButton.qml and shell/Ui/TextField.qml: original row
  action and passphrase field used by that frontend.
- shell/Ui/PopupCard.qml, BarIconButton.qml, BarIconContent.qml,
  IconContentBounds.qml, Button.qml, BorderSurface.qml and BorderOverlay.qml:
  original tray presentation dependencies.
- shell/Commons/Border.qml and BorderGeometry.js: original visual border logic.
- shell/plugins/panels/audio/Model.js and shell/Ui/PanelSlider.qml: original
  audio label/glyph model and slider, used by the output-only port slice.
- shell/plugins/bar/Bar.qml: unchanged source parent for narrow tooltip
  extractions (host lifecycle and original PopupWindow) and horizontal section
  geometry with fixed trusted slots; full bar/registry/drag startup is not staged.
- shell/plugins/panels/audio/Panel.qml: unchanged source parent for the generated
  output frontend, not the full panel/backend startup.
- shell/Ui/KeyboardPanel.qml: unchanged parent; staging removes Exclusive focus,
  unmaps on close and delegates hit testing to the restricted owner.
- shell/Ui/{PanelKeyCatcher,CursorSurface,ToggleSwitch,PanelToolTip,
  PanelSeparator,PanelSectionHeader}.qml: unchanged original interaction/chrome.

- shell/plugins/panels/{bluetooth,monitor,power}/{Panel.qml,Model.js}: unchanged
  parents and pure models for the Ubuntu desktop panels.
- shell/plugins/dock/{DockWindow.qml,DockModel.js}: unchanged dock window parent
  and pure grouping/order model; the unsafe dock service is not imported.

Elsewhen (`shell/plugins/panels/elsewhen/`, Jason Fried, MIT) is vendored for
the world-clock panel. The staged copy is derived by tools/elsewhen_frontend.py:
cities stay in the process, and weather fetch, GitHub profiles, notifications
and system timezone changes are removed. Offsets use tools/elsewhen_probe.py.

The deterministic derivations are recorded in upstream/clock-preview.json and
implemented in tools/audio_frontend.py, tools/network_frontend.py,
tools/desktop_frontends.py, tools/workspace_modes.py and tools/elsewhen_frontend.py. See
[desktop panel boundaries](../../docs/desktop-panels.md) for backend adaptations
and excluded features. A generated mirror is not an independently
authored layout. See docs/audio-output-port.md for exact retained markup,
excluded functions, fixture surface substitution and native acceptance limits.

Each was fetched from pinned public source, verified and reviewed before import;
no private user data was copied. The complete upstream [MIT license](LICENSE)
and copyright are preserved. Canonical URLs, hashes, scope and unchanged status
are recorded in [clock/model provenance](../../upstream/widget-candidates.json),
the [sealed spacer profile](../../upstream/spacer-candidate.json), and the
[clock preview profile](../../upstream/clock-preview.json).

The original clock parent is not staged as a runnable component. The sealed
preview derives a read-only label from it and removes calendar, IPC, persistence,
and pointer actions before preparation. The live trial stages a second derivation
of that parent and of `shell/plugins/panels/clock/Panel.qml` as the calendar
popup. This directory is not the original bar or
full shell. The tray and its visual dependencies are staged unchanged with a
restricted owner and passive Style/Color/I18n adapters. The original Border
singleton is included; original Style/Color/I18n, plugin registry, helpers,
fonts, images, data catalogs and binaries are not. See the
[bar port status](../../docs/bar-port.md).

See [widget dependencies](../../docs/widget-candidates.md), the
[passive spacer contract](../../docs/passive-spacer.md), and the
[clock preview](../../docs/clock-preview.md). Do not expand this directory
without per-file source, license, and dependency review. This project claims
no affiliation with or endorsement by Omarchy.
