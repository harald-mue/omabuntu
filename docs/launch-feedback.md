# Application launch notice

## Source and scope

Omarchy shows a short bottom-center notice when an application started from
the app grid or the dock has not opened a window after two seconds. The pinned
source is `omacom/omarchy@03ff1eff3812933f7088484533784d2f63eaf19a`,
`shell/services/AppLibrary.qml` `beginLaunchFeedback()` and
`shell/plugins/osd/Osd.qml`. The English strings are `appLibrary.launching`
("Launching %1…") and `appLibrary.launchingApp`.

`config/shell/preview/LaunchFeedback.qml` draws that one message. The app grid
and the floating dock call `begin(name)` immediately before the existing
`DesktopEntry.execute()`. `TrialShell` creates the overlay once and destroys
it with the rest of the shell.

## Behavior

The notice waits 1000 ms. Omarchy waits 2000 ms; the shorter delay is a
local choice. It appears only when the toplevel count has not increased and
the active toplevel is still the one recorded at launch. It closes when
either of those changes, and after 15000 ms even if no window
appears. A second launch replaces the tracked baseline. The glyph is U+F14DE,
the same character Omarchy sends to its OSD.

The overlay uses namespace `omabuntu-launch`, sits above windows, reserves no
screen edge, takes no keyboard focus, and sets an empty input mask so clicks
pass through. Text uses the applied UI font. Labels stay on the staged English
catalog; `%1` is replaced in the overlay, not by a catalog loader.

## Explicit exclusions

- No notification daemon, toast stack, or `notify-send`.
- No original shell OSD command, and no volume, brightness, or media OSD.
- No `uwsm-app` or terminal-launcher wrapper. The entry still starts through
  `DesktopEntry.execute()`.
- Programs started by a key binding do not show the notice. Omarchy does not
  show it for those either, because they do not call `AppLibrary.launch()`.
- The dock icon pulse is unchanged and separate.
- The approved bar restart now serves the one-second delay. Hyprland was
  not reloaded.

Source fidelity here is the copy and the click-through overlay. The show
delay is one second rather than Omarchy's two. It is not visual acceptance
of the live session.
