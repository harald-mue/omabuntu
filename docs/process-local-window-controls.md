# Process-local window controls: GTK3 research, blocked for Chrome 156

> **Rolled back by plan 085.** No module was installed or persisted. The research
> source, builder and dedicated tests were archived under ignored
> `work/rollback-window-controls-085/archived-code/`, not retained as active code.
> The browser hyprbars exception was also removed; the sections below are
> historical findings, not current activation instructions.

## Confirmed browser blocker

The explicitly approved real Chrome restart in plan 084 **failed the module-load
check**. Chrome was closed and relaunched through its standard launcher with
GTK_MODULES scoped to that child and the existing profile. The fresh browser
returned to its recorded workspace but did not map the module.

Official Chromium source at the exact installed Chrome tag **156.0.8078.79**,
`ui/gtk/gtk_ui.cc`, explains why: before GTK initialization it installs a GTK
settings interceptor to sanitize module settings and explicitly calls
`env->UnSetVar("GTK_MODULES")`. The earlier review of a mutable main-branch file
and the pinned settings-provider file did not establish this version-specific
initialization behavior. Generic GTK probes did not cover that restriction.

**Do not install, persist or advertise this module as a Chrome/Edge fix.**
Do not bypass browser module filtering or use preload/interposition to force
loading. Edge's exact initialization behavior has not been separately verified;
a shared Chromium family is not proof of identical vendor behavior.

Chrome is running again without the module. GNOME settings are unchanged,
Edge was not restarted, and the existing variant-1 hyprbars exception remains.
No persistent integration or sealed release was changed. The code below remains
bounded GTK3 research, not a deployable browser solution. Requested variant-2
behavior is still blocked pending a separately supported mechanism.

## Original candidate goal and status

The requested target is no application window-control buttons in Hyprland tiling,
only hyprbars controls on floating workspaces, and normal buttons in GNOME.
Plan 083 prepared an authored **GTK3-only candidate** for that target. It was not
installed or integrated into startup. The controlled restart in plan 084
established a browser-specific blocker rather than accepting a replacement.

This is deliberately not a shared GNOME setting, a different browser profile,
LD_PRELOAD interception, a replacement panel or a compositor/plugin patch.
Chrome and Edge processes were observed loading GTK3/GObject libraries; Chromium
156's source reads GtkSettings' decoration layout. That supports this candidate,
not a guarantee about every browser/backend or GTK headerbar application.

## Implementation

`native/gtk3_window_controls.c` implements GTK3's documented module initialization
entry points. In an unambiguous Hyprland/Wayland process with a compositor
signature and display environment, it sets the process's GtkSettings property
`gtk-decoration-layout` to `:` (neither left nor right window buttons). A guarded
notification callback maintains that local property if a provider/app changes it.
Repeated initialization does not add duplicate callbacks.

The module refuses GNOME/Ubuntu, mixed GNOME/Hyprland desktop identifiers,
non-Wayland session types and missing session/display grants. The environment is
an operational scope guard, not a cryptographic proof of compositor identity.
It makes no D-Bus/settings-backend calls, filesystem writes, subprocess launches
or compositor requests. The GObject property setter changes this process only.

Python cannot change a different application's GtkSettings at initialization;
a small native GTK3 module is justified for this boundary. Only the installed
public GTK3/GObject ABI is referenced. No third-party implementation is copied.
The source is MIT like the project. It compiles against the existing runtime
libraries and existing GLib headers, without a GTK development-package install.

`tools/build_gtk3_window_controls.py` is plan-only by default. Explicit
`--build` produces a distinct private artifact/report under
`work/gtk3-window-controls/`, with source and binary hashes, compiler arguments
and build log. It neither installs nor launches an application. The linker
requires resolved symbols and enables RELRO/immediate binding. No browser
sandbox or other security policy is changed.

## Verification performed

- A pure GObject mock harness executes the actual module source without loading
  GTK, opening displays, contacting a settings service or modifying host state.
  It covers Hyprland enablement, GNOME/mixed-desktop refusal, missing grants,
  repeated initialization, display initialization and notification updates.
- Separate short-lived, no-window GTK3 probe processes connected to the existing
  Wayland display. The baseline read the normal min/max/close layout; the module
  changed only the Hyprland probe to `:` and held it after a local update.
- Probes with GNOME and mixed-desktop environment identifiers retained the
  baseline layout. Theme, font and icon-theme property hashes matched in all
  cases. These are guard tests on the existing compositor, **not a fresh GNOME
  login or a real browser visual test**.
- The shared GNOME button-layout setting remains untouched. No real browser,
  existing application, shell, plugin or compositor was restarted or modified.

Private official-source review, native property-probe results and artifacts
remain in ignored work/. These property checks do not prove browser rendering,
headerbar-widget overrides, per-app menu actions or all decoration behavior.

## Rejected deployment path and acceptance requirements

GTK_MODULES is read during toolkit startup. A browser which is already running
will not inherit it, and single-instance launch forwarding can silently reuse
that old process. Do not inject code into that process or kill browser windows
to make a test pass. A controlled full exit/relaunch of Chrome and Edge, including
their app/PWA windows/background process, needs explicit coordination with the
user to protect unsaved work.

These were the proposed deployment gates. Gate 1 failed for Chrome 156, so
subsequent gates must not be executed for this module:

1. Confirm the user can safely close/relaunch the browser family; test the exact
   module on a fresh real browser process without replacing its profile.
2. Verify app controls disappear in tiling while menus, tabs, input and dialogs
   remain functional. Check the actual process loaded the pinned artifact.
3. Use backed-up Hyprland-only launch environment/config integration. Preserve
   existing GTK_MODULES entries and do not export into the shared user manager
   or desktop activation environment. Hyprland 0.57's `hl.env` supports a local
   process environment update with its third D-Bus-export argument false; launch
   paths through D-Bus or old terminals still need independent testing.
4. Only then restore the original owned hyprbars browser matcher with backups
   and a receipt update. Test floating minimize, maximize/restore and dock restore
   through the compositor-side buttons. Do not append duplicate plugin effects
   or button registrations.
5. Test the normal GNOME launch path and next login before claiming session
   acceptance. Store rollback state before each deployed path is changed.

GTK4, Qt, apps overriding their own button layout, Flatpak/Snap confinement and
other browser Linux UI backends are **not supported by this GTK3 candidate**.
Do not silently replace these with global settings or disable their sandboxes.
No machine-wide launcher, startup file, browser policy or package was changed.

## Why native browser minimize was not enough

Official Hyprland v0.57.0 XDGShell/WaylandBackend source forwards a minimize
request, but `CWindow::onUpdateState` processes fullscreen/maximized requests
without consuming the minimized field. It does not call Omabuntu's special-
workspace minimize helper. That is why hiding hyprbars and relying on native
browser controls did not establish equivalent functionality. Browser maximize/
restore also passes through compositor/client-state synchronization; its exact
reported failure has not been reproduced with an interactive event trace.

## Sources

- [GTK3 module loading and environment](https://docs.gtk.org/gtk3/running.html)
- [GTK3 settings and application-local property overrides](https://docs.gtk.org/gtk3/class.Settings.html)
- [GTK 3.24.52 module loader](https://github.com/GNOME/gtk/blob/3.24.52/gtk/gtkmodules.c)
- [Chromium 156 GtkSettings provider](https://github.com/chromium/chromium/blob/156.0.8078.79/ui/gtk/settings_provider_gtk.cc)
- [Chromium 156 GTK initialization and module filtering](https://github.com/chromium/chromium/blob/156.0.8078.79/ui/gtk/gtk_ui.cc)
- [Hyprland 0.57 Wayland requests](https://github.com/hyprwm/Hyprland/blob/v0.57.0/src/desktop/view/window/WaylandBackend.cpp)
- [Hyprland 0.57 window-state request handling](https://github.com/hyprwm/Hyprland/blob/v0.57.0/src/desktop/view/window/Window.cpp)
- [Hyprland 0.57 local versus D-Bus environment export](https://github.com/hyprwm/Hyprland/blob/v0.57.0/src/config/lua/bindings/LuaBindingsConfigRules.cpp)
