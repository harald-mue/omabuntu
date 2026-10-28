# Screenshot through Omasnap

## Goal

Take screenshots the way pinned Omarchy does: the Print key and
`SUPER+SHIFT+S` start Omasnap, and Omasnap captures, copies, saves, and
annotates. Do not build a grim/slurp replacement.

This plan does not approve installation, a key binding, a Hyprland reload,
or a capture.

## Evidence compared

Pinned Omarchy commit `03ff1eff3812933f7088484533784d2f63eaf19a`.

- `default/hypr/bindings/utilities.lua` binds both `PRINT` and
  `SUPER + SHIFT + S` to `omarchy-capture-screenshot`, description
  "Screenshot".
- `bin/omarchy-capture-screenshot` does not capture anything itself. It
  execs `omasnap`. `copy` becomes `--copy`, `save` becomes `--save`, a bare
  `slurp` argument is dropped, and every other argument is passed through.
  If `OMASNAP_SCREENSHOT_DIR` is unset and `OMARCHY_SCREENSHOT_DIR` is set,
  the legacy directory is copied into the Omasnap variable.
- `default/hypr/apps/screenshot-selection.lua` keeps the Omasnap layer
  immediate (`namespace = "^omasnap$"`, `no_anim`, `animation = "none"`,
  `no_screen_share = true`). The `selection` rule in that file belongs to
  slurp, which screenshots no longer use.
- `test/shell.d/omasnap-test.sh` requires `omasnap` in the base package list
  and forbids Satty and Tensaku. Fresh installs no longer use those tools.
- `bin/omarchy-capture-region` is the frozen slurp picker shared by
  recording, OCR, and QR. The screenshot bind does not call it.

Omasnap is a separate MIT project, `https://github.com/omacom/omasnap`,
described as a native Wayland screenshot and annotation editor for Omarchy
and Hyprland. Its current build uses Qt 6, Layer Shell Qt, and the staging
protocols `ext-image-copy-capture`, `ext-image-capture-source`, and
`ext-foreign-toplevel-list`. No Omasnap commit is pinned yet. A read of
`main` is orientation only: the default capture is smart selection, a fresh
capture copies to the clipboard and saves a PNG under
`~/Pictures/Screenshots`, and a floating preview follows. Bundled Neucha,
JetBrains Mono, and Inter Display fonts are SIL Open Font License; the
Lucide icons have their own notice. Those facts must be re-read at the
pinned commit before anything is built or kept.

Hyprland 0.56.2 (`efb509937800`) is the running compositor. Its Lua stub
exposes `no_screen_share` on a layer rule. The live configuration is
`~/.config/hypr/hyprland.lua`. `config/hypr/omabuntu-managed.lua` is
installer-owned and must not gain this rule.

On this machine, `omasnap`, `grim`, `slurp`, `satty`, and `hyprpicker` are
not installed. `wl-clipboard` is installed. Ubuntu has `grim`, `slurp`,
`hyprpicker`, and Layer Shell Qt packages; it has no `omasnap` or `satty`
package. `qt6-base-dev` and `libdeflate-dev` are already installed. Whether
the running compositor advertises the capture protocols was not checked,
because `wayland-info` is not installed. That check stays read-only and
must happen before a build.

`tools/keybindings_menu.py` already ranks a "Screenshot" description. Its
session-action tokens refuse lock and power commands. They do not match
`omasnap` or `screenshot`, so a listed screenshot row can be dispatched.
That is intentional and different from the lock row.

The reviewed Hyprlock config was a flat color when this plan was written.
It had no screenshot path, and this work does not give it one. Plan 039 later
points that config at the recorded still; it still does not use a screenshot.

## Current project gaps

- No screenshot command, binding, or package is present.
- The capability matrix still lists clipboard/capture as untested and names
  Omasnap only as an upstream dependency to review.
- Omasnap's commit, license text, and bundled font and icon notices are not
  recorded in this repository.

## Safety constraints

- Do not install packages, bind keys, reload Hyprland, or take a screenshot
  while writing or reviewing this plan. A capture can contain private
  screen contents and must not be run by the agent.
- Do not run Omasnap's `install-omarchy`. It uses Omarchy's package helper.
- Do not import the Omasnap source tree, fonts, or icons into Git before
  their licenses are recorded. Do not commit a built binary, a screenshot,
  or a private build log.
- Build only under ignored `work/`. Ask before any package installation and
  before copying the binary onto the machine. Do not place an unreviewed
  Omarchy `bin` directory on `PATH`.
- The helper resolves one approved Omasnap executable. It does not search
  an Omarchy install and does not call `hyprctl`, `grim`, `slurp`, or
  `notify-send`.
- A later binding edits only `~/.config/hypr/hyprland.lua`, after a backup
  under ignored `work/`. Do not press either chord from the agent. A reload
  is not a capture test.

## Proposed shape

1. Pin one Omasnap commit. Record its MIT notice and the bundled font and
   icon notices, with hashes, under `upstream/` and `licenses/`. Do not copy
   the source tree into the repository.
2. Read-only, list the missing build and runtime packages and check whether
   the running compositor offers the three capture protocols. Stop and ask
   before installing anything. `grim` and `slurp` are not requirements.
3. After approval, build that commit in ignored `work/` and install it only
   to the approved prefix. Confirm the executable and that its license files
   landed beside it. Do not launch it.
4. Add a small Python helper that performs the pinned wrapper's argument
   mapping and then execs that one binary. Unit tests cover `copy`, `save`,
   dropped `slurp`, directory precedence, and refusal of a missing binary.
   Tests never execute Omasnap.
5. After a separate approval, back up the live Hyprland configuration and
   add the two binds, both described "Screenshot", plus the Omasnap layer
   rule (`no_anim`, no animation, `no_screen_share`). Reload, confirm each
   bind once, and confirm no new config error. Super+K may list the row and
   may run it, because it is not a session action. The user makes the first
   capture.

## Explicit exclusions

- Screen recording, webcam overlay, OCR, color picker, QR capture, and the
  capture menu (`SUPER+CTRL+C`).
- `omarchy-capture-region`, slurp, hyprpicker, Satty, and Tensaku.
- A grim-based fallback if Omasnap cannot be built.
- Changing Hyprlock, idle, DPMS, suspend, portals, or the clipboard manager.
- Putting the rule or the binds in `config/hypr/omabuntu-managed.lua` or
  `config/hypr/minimal.lua`.
- An agent-run capture, including a "smoke" capture of the bar.
- Publishing a release or committing before the user asks.

## Tasks

- [x] Pin one Omasnap commit and record its MIT, font, and icon notices.
- [x] Check build dependencies and capture protocols without installing or capturing.
- [x] After approval, build and install that commit to the approved prefix.
- [x] Add the argument-mapping helper and unit tests that never run Omasnap.
- [x] After approval, bind Print and `SUPER+SHIFT+S`, add the layer rule, and reload.
- [x] Update the screenshot note, the capability matrix, and `WORKLOG.md`.
- [x] Run the unit suite.

## Check result

Omasnap commit `a432f40b14598a4a02b89fa0054f9a0ba3662dd4` (1.24.0) is pinned.
Notices are under `licenses/Omasnap-*`. The running Hyprland 0.56.2 session
advertises `ext_image_copy_capture_manager_v1`,
`ext_output_image_capture_source_manager_v1`,
`ext_foreign_toplevel_image_capture_source_manager_v1`, and
`ext_foreign_toplevel_list_v1`. Qt 6, Wayland, libdeflate, CMake, Ninja, and
the protocol XML files are already installed. Ubuntu's Layer Shell Qt 6.6.4
packages were unpacked under the user prefix because `sudo` had no password
prompt; apt was not used. The binary is installed at `~/.local/bin/omasnap`.
Print and `SUPER+SHIFT+S` are bound, the layer rule is loaded, and the reload
reported no configuration error. `omasnap --version` printed 1.24.0 through
the offscreen platform and left no process. Nothing was captured.
