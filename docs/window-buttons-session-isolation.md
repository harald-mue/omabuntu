# Application window buttons and session isolation

> **Historical state after plan 085:** all window-control experiments were rolled
> back at the user's request. The original hyprbars rule again includes browsers
> on floating workspaces; GNOME settings remain unchanged. The option comparison
> below is historical analysis. For the subsequently user-confirmed Chrome setting
> and the unresolved Edge limitation, see
> [current installation guidance](installer.md#browser-window-controls).

## Result

The reported buttons come from two independent decoration owners:

1. Chrome/Edge and other CSD applications draw controls inside their own window.
2. Hyprbars draws an additional compositor-side titlebar for windows carrying
   the `omabuntu-floating-workspace` membership tag.

A tiled browser can therefore have its own controls without any hyprbars bar;
a browser on a floating workspace can show both sets. Removing repeated
hyprbars registrations (plan 075) does not remove application-drawn controls.
Conversely, hiding hyprbars does not hide the browser's controls in tiling.
Individual floating state and floating-workspace membership are distinct here:
the current titlebar rule matches membership, not every `floating=true` window.

This analysis changes no desktop settings. Normal GNOME buttons must remain
intact, including after switching sessions or running them concurrently.

## Evidence

Read-only probes on 2026-11-05 found:

- The shared user setting `org.gnome.desktop.wm.preferences button-layout` is
  `appmenu:minimize,maximize,close`, as restored by plan 074.
- The GNOME XSettings overrides dictionary is empty. This does not prove that
  no other toolkit/app-specific override exists.
- The observed Chrome and Edge application windows are native Wayland clients,
  not XWayland. No floating client was present in that snapshot; the actual
  two-row appearance is the user's observation, not a new visual test.
- Installed Chrome is 156.0.8078.79; Edge is 156.0.4314.58. Edge-specific source
  and the exact active browser UI preference were not independently inspected.
- `config/hypr/titlebars.lua.in` hides hyprbars generally and enables it for
  tagged floating-workspace members. Its per-Lua-state guard prevents repeated
  registrations in that state. No live plugin reload/evaluation was performed.

Chromium's official source at tag **156.0.8078.79** subscribes to
`notify::gtk-decoration-layout` and passes that layout into its window button
ordering. GTK **3.24.52**, matching the installed GTK3 upstream version, maps
`org.gnome.desktop.wm.preferences/button-layout` to `gtk-decoration-layout` in
its Wayland backend and supports a settings-portal path with GSettings fallback.
These establish the relevant mechanism, not that every app/backend follows it.

Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068` was checked for the browser rules and
Chromium flags. The reviewed browser rules tag/tile browser classes; those
rules do not suppress application titlebar buttons. The reviewed flags select
Wayland but contain no button-layout isolation mechanism. These two files are
not an audit of every upstream startup/theme helper.

Raw public review files remain private in `work/research/window-buttons-080/`.
No browser profiles, history, cookies, credentials or corporate policies were read.

## Why the previous global fix must not return

Plan 074 records the actual regression: setting the shared user button layout
to `appmenu` removed controls in GNOME too. Restoring
`appmenu:minimize,maximize,close` deliberately restored CSD controls in Hyprland.
The setting is user-level, not private to the terminal/session running gsettings.

Do not set it on Hyprland login and restore it on logout. Crashes, overlapping
sessions and settings-change notifications make that unsafe. A user-manager
`import-environment` is not per-application isolation either. Persistent
browser appearance preferences can also follow the same profile into GNOME.

## Options and tradeoffs

| Option | Hyprland tiling | Hyprland floating workspace | GNOME | Assessment |
| --- | --- | --- | --- | --- |
| Keep current behavior | App buttons | Hyprbars plus app buttons | Normal | Current, no change |
| Exclude selected CSD apps from hyprbars | App buttons | App buttons only | Unchanged | Lowest-risk way to remove duplicate rows, but not the desired button-free tiling look |
| Suppress app buttons only in Hyprland application processes | No app buttons if the app honors it | Hyprbars only | Normal if truly isolated | Preferred architecture for that visual goal; mechanism still needs app/backend-specific proof |
| Change the shared GNOME key | Buttons can disappear | Hyprbars only | Buttons also disappear | Rejected |

A CSD exception must cover actual browser/PWA identities without matching
unrelated applications. It must preserve the existing hide/show rule ordering
and floating membership handling; it is not enough to add a generic floating
rule. At analysis time no exception had been applied. The subsequent approved
variant-1 implementation/deployment is recorded in plan 081 and
[the subsequent rollback](hyprbars.md#window-control-experiments-rolled-back-plan-085).

A process/session-scoped application solution needs a narrowly bounded source
of decoration settings, not a write to the shared GNOME key. The read-only
review does **not** establish a deployable universal switch:

- GTK documents `GTK_CSD=0` as disabling default CSD only for windows without a
  custom titlebar widget. It is not a general Chromium/headerbar button remover.
- A shared `~/.config/gtk-3.0/settings.ini`, GTK4 file or CSS edit also reaches
  GNOME. Settings-file precedence must not be assumed to override Wayland's
  active settings provider; Chromium's own drawing is not GTK widget CSS.
- An XSettings-only solution does not cover these native Wayland browsers.
- Changing `XDG_CONFIG_HOME`, the whole GSettings backend or the browser profile
  to separate one decoration property risks unrelated preferences and state.
- A browser's system-titlebar preference is not presumed session-local or
  equivalent to removing its buttons on the installed Wayland version.
- A Hyprland no-border/no-bar rule cannot delete controls painted inside a
  client buffer. Cropping/masking would also damage application UI/hit testing.

## Recommendation and acceptance gates

First decide whether the requirement is **one row of buttons** or the stronger
**no app buttons in tiling, hyprbars controls in floating workspaces**.

For the former, a reviewed Hyprland-only hyprbars exception is the simplest
candidate and leaves application/GNOME settings entirely alone. For the latter,
retain hyprbars and investigate a genuinely process-scoped decoration-setting
mechanism; do not deploy a global workaround disguised as session isolation.

Any approved follow-up must test normal Chrome, Edge/PWA and at least one GTK
headerbar app in tiled and floating-workspace states, including a browser already
running before launch (single-instance forwarding may bypass a launch wrapper).
Verify GNOME after a fresh login, reverse session order and, where supported,
overlapping sessions; include failure recovery and rollback. Fullscreen and
ordinary floating dialogs must not gain broken decorations. Native visual and
interaction acceptance remains pending. No app restart, config edit, reload,
service change, deployment or commit was authorized by this analysis request.

## Official sources

- [Chromium 156 GTK settings provider](https://github.com/chromium/chromium/blob/156.0.8078.79/ui/gtk/settings_provider_gtk.cc)
- [GTK 3.24.52 Wayland settings mapping](https://github.com/GNOME/gtk/blob/3.24.52/gdk/wayland/gdkscreen-wayland.c)
- [GTK3 decoration layout](https://docs.gtk.org/gtk3/property.Settings.gtk-decoration-layout.html)
- [GTK3 settings and configuration precedence](https://docs.gtk.org/gtk3/class.Settings.html)
- [GTK3 environment variables, including GTK_CSD](https://docs.gtk.org/gtk3/running.html)
- [GTK4 headerbar title buttons](https://docs.gtk.org/gtk4/property.HeaderBar.show-title-buttons.html)
- [Hyprbars v0.57.0 settings and window rules](https://github.com/hyprwm/hyprland-plugins/blob/v0.57.0/hyprbars/README.md)
- [Stable Omarchy browser rules](https://github.com/omacom/omarchy/blob/ac2690cd7be4f47e4a255f5e2e78d904d436b068/default/hypr/apps/browser.lua)
- [Stable Omarchy Chromium flags](https://github.com/omacom/omarchy/blob/ac2690cd7be4f47e4a255f5e2e78d904d436b068/config/chromium-flags.conf)
