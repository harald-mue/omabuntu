# Toolkit-wide window controls: feasibility and boundaries

## Superseding scope decision (plan 131)

The user subsequently approved a user-wide button-layout switch, explicitly
including GNOME, to make the original working mechanism configurable. That
implementation is described in [Window Controls](window-controls.md). It does
not claim session isolation or guaranteed coverage of custom controls. The
Hyprland-only assessment below is historical and explains why those stronger
requirements were not met. The unfinished plan-130 launch integration was
archived without deployment; no special-launcher requirement remains in the new
implementation. Live activation is a separate step.

## Historical decision

A central Setup menu is feasible as a user interface, but a universally effective
Hyprland-only min/max/close toggle is **not established**. Do not ship a menu
switch that silently changes GNOME or claims unsupported applications are covered.
This assessment implements no window-control policy and changes no runtime state.

**Historical follow-up (plans 128–129):** the user accepted partial coverage and
that wrapper-only implementation was deployed locally. It did not meet normal
application-launch expectations and did not cover GNOME Files' GTK4 headerbar.
Plan 131 replaces it with the explicitly approved user-wide setting. That scope
change does not disprove the session-isolation/universal-support limits below.

The requested policy is independent of application identity:

- Hyprland tiling and scrolling: no application-drawn min/max/close controls.
- Floating workspaces: hyprbars supplies the controls.
- GNOME: normal controls remain available.
- One central Super+Space > Setup entry, not a Chrome-specific replacement.

Distinguish application families from window roles. Even a supported toolkit can
have ordinary windows, modal dialogs, tool windows, custom headers, popups,
fullscreen windows and other special surfaces. Blanket removal is not an
accepted policy for every role without testing its close/recovery path.

## Evidence scope

Compare plans 074 and 080–089, `config/hypr/titlebars.lua.in`,
`config/shell/omabuntu-menu.jsonc` and `tools/menu_model.py` with the official
sources below. The upstream behavior baseline is Omarchy v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Plan 086 records source evidence
for floating-workspace titlebars, not universal application-control suppression.

Qt source was reviewed at **v6.10.2**, matching the project baseline. GTK3 docs
identify library 3.24; GTK4 docs currently identify 4.24.1. Libadwaita main,
Electron latest (the example identifies 45.4.1), and the Wayland protocol main
branch are moving documentation, not pins for installed applications. Their
retrieval hashes are recorded privately; these sources establish API boundaries,
not installed-version compatibility. No new host inventory or native tests were
performed. Earlier Chrome evidence is specific to 156.0.8078.79.

Raw downloaded material, retrieval URLs, timestamps, SHA-256 hashes and failed
requests are private under `work/research/window-controls-127/`. Initial Qt
source URLs in qtwayland returned 404; successful v6.10.2 source URLs are in
qtbase. Failed URLs are not evidence that a mechanism is absent. No upstream
implementation or assets were imported into product code.

## Support matrix

“Candidate” means source-level mechanism, not implemented or live-accepted support.

| Family / owner | Available mechanism | Hyprland-only scope and gaps | Assessment |
| --- | --- | --- | --- |
| Compositor decorations / current hyprbars | Existing rules hide the bar generally and show it for `omabuntu-floating-workspace` members | Already scoped to Hyprland; membership is not equivalent to each individual `floating=true` window. Does not remove CSD. | Existing mechanism; preserve it rather than confusing it with app controls. |
| GTK3 default titlebars | `GTK_CSD=0` disables default CSD for windows without a custom titlebar widget | Child-process environment can be scoped, but launch inheritance, D-Bus activation, existing processes and actual Wayland behavior require tests. Custom titlebars explicitly keep CSD. | Partial candidate only. Not a general GTK3 button toggle. |
| GTK3 custom headerbars | `gtk-decoration-layout` is a GtkSettings property; apps can override properties locally | Shared GNOME key/settings files are not session-local. Historical GTK3 module was rolled back; Chrome blocked its loading. No approved external general setter exists here. | Blocked for a general external policy. |
| GTK4 headerbars | `show-title-buttons`; `decoration-layout`, falling back to GtkSettings when unset | These are application widget APIs, not commands to control another process. An explicit widget layout can differ from the global setting. Wayland settings normally come from the settings portal. | Application cooperation exists; universal external control not established. |
| libadwaita headerbars | `show-start-title-buttons`, `show-end-title-buttons`, `decoration-layout` | Same application-owned boundary; removing the whole headerbar could remove navigation and application actions. | No supported external universal toggle established. |
| Qt 6.10.2 standard Wayland decorations | `QT_WAYLAND_DISABLE_WINDOWDECORATION=1` causes `supportsWindowDecoration()` to return false; `createDecoration()` checks that result | A scoped environment is a candidate for newly started matching Qt Wayland processes. Does not remove custom QML/widget controls, affect xcb clients, or reconfigure already running apps. The value is cached in the process. | Concrete partial candidate, not deployed or visually accepted. |
| Chromium / ordinary Chrome | Supported system-titlebar preference where the platform advertises the decoration protocol | Earlier user-confirmed Chrome outcome only. Preference belongs to the browser profile; GNOME fallback needs native acceptance. PWA/PiP exceptions remain. | Existing narrow evidence, not the requested general solution. |
| Edge | No equivalent tested setting established | Shared Chromium ancestry is insufficient evidence. | Unresolved. |
| Electron | `frame: false` is a BrowserWindow constructor option; custom controls can be application UI | Developer API, not a universal end-user flag. An application can draw buttons in web content even without an OS frame. Chrome's profile UI is not an Electron contract. | Requires app cooperation/settings; no general external toggle established. |
| XWayland / X11 applications | Compositor/server frames and application-owned controls are separate | Qt Wayland variables and xdg-decoration do not govern the xcb/X11 backend. No X11-specific runtime/source acceptance was performed in this assessment. | Separate research; no blanket support claim. |
| Java, Wine, SDL, proprietary/custom toolkits | May have their own frames and controls | Not individually source-reviewed here; custom rendering alone defeats a guarantee based on GTK/Qt settings. | Unknown; explicitly outside demonstrated coverage. |

## Why Wayland decoration negotiation is not a universal solution

`xdg-decoration` lets participating clients negotiate client-side or server-side
decoration. The compositor may enforce a different mode and participating
clients must obey the configured mode. This is stronger than a mere visual hint,
but the client must first create the decoration object. It does not give an
external helper access to arbitrary widgets or web content, nor compel every
application to implement this optional protocol. It is not a min/max/close
property registry for all windows.

A compositor-side preference for server decorations is therefore worth testing
only for participating clients. It is not proof that custom application buttons
will disappear. No Hyprland rule or protocol implementation was changed here.

## Rejected shortcuts

- Do not bring back the shared GNOME `button-layout` write. It reproduced the
  original regression and never proved universal application coverage.
- Do not change that value on login and restore it on logout. Overlapping
  sessions, crashes and live settings notifications break the isolation model.
- Do not export toolkit variables through the shared systemd user manager or
  D-Bus activation environment and call them session-local.
- Do not alter shared GTK CSS/settings files, redirect the whole XDG config or
  GSettings backend, or change browser profiles without an explicit scope.
- Do not retry the rejected GTK module through injection/preload or bypass
  browser filtering. GTK3 module research does not establish GTK4 support.
- Do not crop the top of windows. That removes tabs/header actions or hit targets,
  not a semantic button group. Hiding a headerbar is not hiding its buttons.
- Do not force all applications to XWayland or patch corporate applications to
  make a universal menu claim appear true.
- Do not infer that a new launcher environment updates existing processes.
  Single-instance forwarding and application activation need separate evidence.

## Central menu boundary

At assessment time Setup contained Defaults only. Dotted entries in
`config/shell/omabuntu-menu.jsonc` can add a Window Controls submenu without a new
panel. Its actions must be explicitly registered in `tools/menu_model.py` and
backed by a bounded helper; arbitrary shell commands are not accepted.

However, **the requested universal toggle remains blocked**, so the assessment
added no menu entry or no-op preference. The later partial “supported applications
only” mode was explicitly agreed by the user and is documented separately; it
must not be confused with universal support.
Even showing an enabled preference must distinguish requested policy from actual
application support and from verified visual results.

## Smallest useful follow-up, requiring separate approval

If partial toolkit coverage is accepted, prepare disposable native GTK3 and
Qt 6.10.2 test applications with standard and custom headers. Compare default
and child-process-only environment variants in the existing Hyprland session,
without changing real application launchers or restarting user applications.
Check rendering, close/maximize/minimize/restore, dialog usability, floating
membership and fullscreen. Report expected failures for custom headers.
A process-local test does not establish D-Bus/single-instance launch coverage.

Only after those results should launch integration be designed: explicit
session-lifetime opt-in, backed-up launch/configuration paths, no global manager
environment, clear restart requirements, safe rollback and detection of drift.
Fresh GNOME login, reverse/overlapping sessions, sandboxed packages, window roles
and ordinary floating dialogs remain separate acceptance gates. Do not create a
universal guarantee from a representative sample.

If coverage of every application/window type without exceptions is mandatory,
this assessment's result is a blocker, not authorization for a workaround.

## Official sources

- [GTK3 settings](https://docs.gtk.org/gtk3/class.Settings.html)
- [GTK3 environment, including GTK_CSD](https://docs.gtk.org/gtk3/running.html)
- [GTK4 title buttons](https://docs.gtk.org/gtk4/property.HeaderBar.show-title-buttons.html)
- [GTK4 per-widget decoration layout](https://docs.gtk.org/gtk4/property.HeaderBar.decoration-layout.html)
- [GTK4 settings and portal](https://docs.gtk.org/gtk4/class.Settings.html)
- [Libadwaita HeaderBar](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.HeaderBar.html)
- [Qt v6.10.2 decoration support](https://github.com/qt/qtbase/blob/v6.10.2/src/plugins/platforms/wayland/qwaylanddisplay.cpp#L916-L930)
- [Qt v6.10.2 decoration creation](https://github.com/qt/qtbase/blob/v6.10.2/src/plugins/platforms/wayland/qwaylandwindow.cpp#L1092-L1174)
- [Qt 6.10 Wayland architecture](https://doc.qt.io/qt-6.10/wayland-and-qt.html)
- [Electron custom window styles](https://www.electronjs.org/docs/latest/tutorial/custom-window-styles)
- [Wayland xdg-decoration protocol](https://github.com/wayland-mirror/wayland-protocols/blob/main/unstable/xdg-decoration/xdg-decoration-unstable-v1.xml)
- [Previous browser-specific findings](chrome-edge-decoration-research.md)
- [Original GNOME regression and rejected mechanisms](window-buttons-session-isolation.md)

## Verification

Documentation-only assessment. No native functional, GNOME-session or security
acceptance is claimed. Unit-suite results are recorded in plan 127 after running.
