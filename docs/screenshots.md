# Screenshots

Pinned Omarchy commit `03ff1eff3812933f7088484533784d2f63eaf19a` binds both
Print and `SUPER+SHIFT+S` to `omarchy-capture-screenshot`, described as
"Screenshot". That command does not capture anything itself. It execs
Omasnap. `copy` becomes `--copy`, `save` becomes `--save`, a bare `slurp`
argument is dropped, and every other argument is passed through.
`OMARCHY_SCREENSHOT_DIR` fills `OMASNAP_SCREENSHOT_DIR` only when the native
variable is unset.

Omasnap is a separate MIT program. This repository pins commit
`a432f40b14598a4a02b89fa0054f9a0ba3662dd4` (version 1.24.0). Its MIT notice,
the SIL Open Font License notices for the bundled Neucha, JetBrains Mono,
and Inter Display faces, the Lucide ISC notice, and the upstream font
provenance note are stored under `licenses/Omasnap-*`. The source tree,
fonts, and icons are not imported. See `upstream/omasnap-source.json`.

`tools/capture_screenshot.py` performs that argument mapping and then
replaces the process with one approved binary. The default path is
`~/.local/bin/omasnap`. `OMABUNTU_OMASNAP` may select another absolute
regular file, and the file name must be `omasnap`. A symlink is refused.
The helper does not search `PATH`, does not call grim, slurp, hyprctl, or
`notify-send`, and does not capture a screen while the binary is missing.
It accepts the real process environment. This Hyprland process does not
export `WAYLAND_DISPLAY`; when exactly one Wayland socket is present, the
helper passes that name to Omasnap. Without it, Qt tries the X11 plugin
and exits before the overlay appears.

## What is installed today

Omasnap 1.24.0 from the pinned commit is installed as a regular executable
at `~/.local/bin/omasnap`. Its font and icon notices are beside it under
`~/.local/share/licenses/omasnap/`, together with a copy of its MIT license.
`~/.local/bin/omabuntu-capture-screenshot` is the reviewed wrapper.

Ubuntu has no Omasnap package. The build needed Layer Shell Qt, and `sudo`
had no password prompt in this session, so the Ubuntu packages
`liblayershellqtinterface6`, `liblayershellqtinterface-dev`, and
`qml6-module-org-kde-layershell` (6.6.4) were downloaded and unpacked
instead of installed with apt. The runtime library is
`~/.local/lib/x86_64-linux-gnu/libLayerShellQtInterface.so.6`, which the
binary's run path uses. Its LGPL copyright is under
`~/.local/share/licenses/layer-shell-qt/`. No system package was changed.

The live Hyprland configuration binds Print and `SUPER+SHIFT+S` to the
wrapper, both described "Screenshot", and keeps the `omasnap` layer out of
animations and screen shares. The configuration was reloaded with no new
error. Super+K may run the row. The lock row stays refused. No screenshot
has been taken.

## Exclusions

- Screen recording, webcam overlay, OCR, the color picker, QR capture, and
  the capture menu.
- grim, slurp, hyprpicker, Satty, and Tensaku.
- A fallback capturer if Omasnap cannot be built.
- Hyprlock, idle, DPMS, suspend, portals, and the clipboard manager.
- Taking a capture from the agent. The user makes the first one.
