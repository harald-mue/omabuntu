# Chrome and Edge decoration research

## Result and scope

No supported **process-local button-layout override** has been established for
both installed browsers. There is, however, a supported Chrome UI setting worth
a separately approved test: **Use system title bar and borders**. Its behavior
is selected by the compositor's capabilities, not simply by a shared preference.
This is a narrower candidate for ordinary browser windows, not a deployed fix,
not a session-local preference, and not verified Edge/PWA/GNOME acceptance.

Plan: [087](../plans/087-chrome-edge-supported-decoration-research.md).
Existing experiments remain rolled back under plan 085.

## Subsequent user confirmation (plan 089)

The user subsequently enabled **Use system title bar and borders** in Chrome
and reported that it resolves their Chrome appearance problem. This is local
user acceptance of the appearance, not independent verification of every button
action, PWA/PiP behavior or GNOME login. The user did not find an equivalent Edge
setting and deferred Edge work. It remains unverified, not silently supported.

The installer now provides manual [browser setup guidance](installer.md#browser-window-controls).
It does not read or edit profiles, launch browsers or change GNOME/GTK settings.
The original source findings and pre-test scope below remain historical evidence.

## Versions and unchanged state

A read-only package query, without executing either browser, returned:

- Chrome package: `156.0.8078.79-1`.
- Edge package: `156.0.4314.58-1`.
- Hyprland package: `0.57.0-1ppa2~1resolute1`.

Package versions do not prove the running process version or backend. Previous
plan-080 evidence identifies sampled Chrome/Edge clients as native Wayland;
this investigation did not collect a new window inventory. Profiles, policies,
credentials, history and current appearance preferences were not read. There
was no browser launch, restart, settings write, plugin action or deployment.

## Exact Chrome source: a capability-dependent system-frame setting

Official Chromium source at **156.0.8078.79** establishes this chain:

1. `chrome/browser/resources/settings/appearance_page/appearance_page.html.ts`
   exposes the Linux window-decoration toggle, inverted against the profile
   preference `browser.custom_chrome_frame`. Enabling system decorations means
   disabling the custom frame; this is an actual settings UI, not an invented
   command-line flag.
2. `chrome/browser/ui/webui/settings/settings_localized_strings_provider.cc`
   exposes that toggle only if the platform advertises server-side decorations.
3. `chrome/browser/ui/views/frame/browser_native_widget_aura_linux.cc`,
   `UseCustomFrame()`, first checks that capability. If it is absent, Chrome
   **ignores the preference and uses its custom frame**. With the capability
   present and the custom-frame preference false, an ordinary browser window
   can use the native/system frame instead.
4. `ui/ozone/platform/wayland/ozone_platform_wayland.cc` derives the capability
   from the presence of `zxdg_decoration_manager_v1` (apart from test overrides).
5. `ui/ozone/platform/wayland/host/wayland_toplevel_window.cc` requests server-
   side decoration when using a native frame and client-side decoration
   otherwise. Its native-frame check also requires that protocol.
6. Changes to the preference call `FrameTypeChanged()` and `UpdateFrameHints()`.
   The source supports an in-process frame update; a browser restart must not
   be assumed necessary just to try the visible UI toggle.

This gives a plausible supported path: let Hyprland own decorations and let
Omabuntu's existing workspace rules decide when its titlebar is visible.
On a GNOME Wayland compositor **without that protocol**, Chrome's explicit
fallback should retain its own frame and normal buttons despite the preference.
That is a source-derived conditional prediction, not a check of the actual GNOME
session. GNOME/Xorg, XWayland or other compositors must not be folded into that
prediction. A shared profile preference still changes, so this is **not** the
originally requested process-local setting and needs explicit approval.

### Important limitations

- `UseCustomFrame()` explicitly keeps custom frames for web-app and picture-in-
  picture windows. Therefore the ordinary-window candidate is not a universal
  PWA solution. Test ordinary windows, PWAs and dialogs separately.
- Hyprland protocol availability, negotiated mode and actual button rendering
  must be checked natively. Plugin rules do not themselves negotiate browser CSD.
- The current preference could already select system decorations; it was not
  inspected. If it does, changing it again is not a solution: investigate the
  active backend, window type and protocol negotiation instead.
- A system-themed browser frame (`BrowserFrameViewLinuxNative`) can still be
  client-rendered and contain buttons. A GTK/system theme is not the same thing
  as selecting server-side decoration.

## Other candidate paths reviewed

| Path | Evidence and disposition |
| --- | --- |
| `--ui-toolkit=gtk`, `qt`, `fallback` | Exact `ui/linux/linux_ui_factory.cc` selects toolkit integration, not a documented empty button layout. The fallback provider retains default min/max/close ordering in `ui/views/window/window_button_order_provider.cc`. No reason to deploy a toolkit change as a button-removal fix. |
| GTK decoration layout | Exact `ui/gtk/settings_provider_gtk.cc` observes `gtk-decoration-layout`. This explains current CSD; it does not expose a browser command-line override for that property. |
| `GTK_MODULES` | Exact `ui/gtk/gtk_ui.cc` explicitly removes it. The failed Chrome experiment remains rejected; no injection or bypass is proposed. |
| Shared GNOME/GTK settings | Not session-local; rejected because GNOME must remain intact. |
| Browser-specific hide-controls command-line flag | No such supported override was established in the reviewed `chrome/common/chrome_switches.h`, `ui/base/ui_base_switches.h` and Linux frame paths. This is a bounded negative result, not a search of every Chromium source file. |
| hyprbars browser exclusion | Only removes the outer row, leaves tiled CSD and native-minimize semantics unresolved; already rolled back. |

## Edge: independent evidence remains incomplete

The installed Edge version was verified independently through package metadata.
Microsoft's official [Edge policy catalog](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-policies)
was downloaded and reviewed for titlebar/decoration policy entries. No applicable
Linux button-layout isolation policy was identified in that catalog. It is not
a command-line specification, proof that every vendor option is absent, or a
reason to inspect/change corporate policies.

The vendor build's frame implementation and UI were not independently verified.
Chrome's exact tag must not be presented as Edge's exact source version. An Edge
system-titlebar setting, if exposed, is a **separate native test candidate**,
not a confirmed implementation of Chrome's fallback. No Edge flags or policy
changes are recommended on the strength of shared Chromium ancestry alone.

## Smallest next acceptance step (not performed)

If the user accepts trying a supported **profile appearance preference** rather
than insisting on a process-local override:

1. Record the existing toggle and window type/backend without dumping profile
   data. Back up affected state through an agreed, narrowly scoped procedure
   before any change; do not blindly copy a live browser profile or edit its
   Preferences JSON while running.
2. On one ordinary Chrome window, try the visible system-titlebar option once.
   No restart, plugin reload, new browser profile or shared GNOME write is part
   of this test. Stop if the option is absent or already enabled.
3. Check tiled appearance, floating-workspace appearance, titlebar focus,
   close on a disposable window, maximize/restore, Omabuntu minimize and dock
   restore. Roll back the toggle if results fail.
4. Independently verify Edge's visible UI and repeat only with separate approval.
5. Verify normal buttons after a coordinated GNOME Wayland login; validate
   reverse session order and keep GNOME/Xorg outside acceptance until tested.
6. Record PWA/PiP/dialog limitations explicitly. Do not integrate or advertise
   a universal fix unless their behavior is accepted too.

If a shared profile preference is unacceptable, the current result is a blocker:
no supported process-local solution for both browsers was established. Do not
silently substitute global settings, module injection or custom browser builds.

## Public-source provenance

Chromium files above were retrieved from the official repository at the exact
Chrome-matching tag, for analysis only; none was imported into product source:

`https://github.com/chromium/chromium/blob/156.0.8078.79/`

Raw sources, successful-response SHA-256 hashes, URLs and failed requests are
recorded privately in `work/research/browser-decoration-087/sources.json`.
Failed guessed paths were replaced where possible by directory/API discovery;
they are not evidence that a feature is absent. Unit tests establish repository
regression status only, not native browser or security acceptance.
