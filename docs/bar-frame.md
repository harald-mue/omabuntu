# Source-derived horizontal bar sections

This is a geometry port from the pinned original Bar.qml, **not full original
bar/theme/registry acceptance**. It replaces the authored full-width overlays
with a left section, independently centered group and right section. It keeps
original centerBegin/centerEnd positioning for future admitted components.

## Source and boundaries

Source parent: vendor/omarchy/shell/plugins/bar/Bar.qml, public Omarchy commit
03ff1eff3812933f7088484533784d2f63eaf19a. This unchanged MIT parent was already
reviewed for tooltip extraction. tools/bar_frame.py stages BarFrame.qml through
fixed-horizontal-sections-v1; source/derived hashes are enforced by the closed
profile. Extraction witnesses fail closed on source changes.

Retained original geometry:

- Horizontal left/right anchors with 8px outer insets and vertical centering.
- Original CenterSections and CenterBox position formulas: center stays centered
  as one group, with begin/end sections hanging off its two edges.
- Centering does not depend on title length or asymmetric side widths.

Explicit adaptations/exclusions:

- Fixed trusted Component slots replace WidgetPool/registry/module URLs. There
  is no command module, custom QML discovery, theme IO, layout persistence or
  automatic whole-shell startup.
- Only top/horizontal is admitted. Notch calibration and beside-right policy,
  vertical bars, original center gestures, drag/drop/ghosts/outlines and center
  registration are excluded rather than activated as hidden dependencies.
- Side slots clip only when their content would overlap the center group. Both
  sides keep an 8px separation from the center group, including begin/end slots.
  Very narrow displays may truncate side controls rather than overlay the clock.
  This responsive admission is an explicit addition, not unchanged upstream code.
- TrialPanel loads the clock directly at 26px through its existing read-only
  derivation, instead of placing the sealed PreviewContent frame behind a second
  full-width LiveStatus overlay. PreviewContent remains unchanged for historical
  sealed rendering/regression tests.
- LiveStatus is now a content-sized row of existing global workspace slots,
  Apps and a plain-text elided title, with a live width budget and 280px title
  cap. Fixed x offsets 224/268 and the ad-hoc half-screen subtraction are gone.
  Apps and the title remain authored adapters. Workspace slots now use the
  derived Omarchy glyph switcher; see [workspace modes](workspace-modes.md).
  Monitor-block policy remains unported.
- Colors and passive theme tokens are not the full original theme service.

## Evidence

206 unit contracts pass. Seven actual offscreen Qt frame fixtures check logical
widths 1280, 3440 and 1920, a narrow 320px frame, a long literal-markup title,
center begin/end positioning, and deliberate assertion exit 42. They instantiate
the real source-derived frame and authored left row. Only the fixture copy's
Hyprland import is synthetic, with startup dispatch as a tripwire; there is no
host compositor command or pointer injection. Tests check centering, 8px edge
insets, side non-overlap, title budget and 26px height. This is not pixel/theme
or native pointer acceptance.

All final reports passed with runtime artifact bytes unchanged:

- work/frame-port/20261024T170522.474405Z/report.json
- work/tooltip-port/20261024T170529.441160Z/report.json
- work/audio-port/20261024T170537.590297Z/report.json
- work/network-port/20261024T170545.420617Z/report.json
- work/tray-port/20261024T170552.123831Z/report.json
- work/clock-preview/20261024T170556.755465Z/report.json
- work/bar-frame-unit-tests.log

## Activation and rollback

User authorized tooltip activation and continued work. Tooltip-only activation
was work/bar-session/20261024T165402.318224Z, PID 409597. Continued section work
replaced only that verified bar process; the tooltip fix remains included.
Current run: work/bar-session/20261024T170636.340422Z, PID 414781.

Configuration Loaded/no-expiry observed; three 26px surfaces, application global
shortcut and reserved [0,26,0,0] on each output; configerrors empty. The only
observed startup warning is the known org.quickshell portal app-ID warning.
No Hyprland file edit/reload, logout, audio/network setting change, package,
autostart, service-unit enablement, authentication/lock/idle/suspend change.
Hyprland Lua mtime remains October 22. No commit/publication.

Previous sealed stages retain the prior source state. Stop only the bar through
tools/bar_session.py stop, never uwsm stop. Restarting the bar does not reset
intentional audio choices or stop applications. No installed path was edited.
The current run remains session-long with no expiry, not login persistence.
Actual hover placement, shared hit testing and visual parity need user acceptance.
