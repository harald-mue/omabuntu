# Top bar parity: menu icon, keyboard layout, frame/theme

Status: implemented in the repository; live activation (packaging, bar
restart) not yet requested. Tests pass. No bar release was staged, installed,
or started. The user separately installed `libxkbcommon-tools` on 2026-10-25
(see exclusions).

## Goal

Close three deviations of the Omabuntu top bar against the pinned Omarchy
commit `03ff1eff3812933f7088484533784d2f63eaf19a`:

1. The missing menu widget at the left edge: the Omarchy mark plus the
   root-menu click behavior of `shell/plugins/menu/BarWidget.qml`.
2. The keyboard-layout widget in the right section, in Omarchy's default
   position (between tray and Bluetooth).
3. The frame/theme deviations recorded in `docs/bar-port.md` and
   `docs/bar-frame.md`: fixed passive colors instead of the palette state,
   no 420 ms color transitions, no glassy/transparent bar backgrounds, no
   bar-off flag.

## Evidence compared (pinned upstream commit)

Fetched read-only into ignored `work/bar-parity/03ff1eff/` and matched against
the pinned Git tree (blob SHAs and sizes verified):

- `shell/plugins/menu/BarWidget.qml`: logo glyph `\ue900` in the "omarchy"
  icon font; left click toggles the root menu, right click opens a terminal.
- `default/fonts/omarchy/README.md` + `omarchy.ttf`: U+E900 is Omarchy's own
  mark; the font also contains third-party agent marks, so the binary font is
  NOT imported (plan 002 excluded upstream fonts). The U+E900 outline was
  extracted with a stdlib TrueType parser (`tools/extract_menu_mark.py`) into
  recorded path data; the upstream `BarIconButton` already supports custom
  icon components, so the mark rides the original button through that slot.
- `shell/plugins/bar/widgets/KeyboardLayout.qml` +
  `KeyboardLayoutModel.js` + `KeyboardLayout.manifest.json`: hyprctl
  `-j devices` reading, activelayout events, `switchxkblayout` cycling,
  `xkbcli list --load-exotic` briefs, `InputDevices`/`InputMethodState`.
- `shell/Commons/Util.qml` (pure functions), `shell/Commons/InputDevices.qml`
  (`inotifywait` present on this machine), `shell/Commons/InputMethodState.qml`
  (spawns upstream's fcitx indicator script — not portable).
- `config/omarchy/shell.json`: default layout order `left: menu, workspaces`;
  `right: tray, keyboard-layout, agents, bluetooth, network, audio, monitor,
  power`.
- `shell/plugins/bar/Bar.qml`: 420 ms OutCubic `Behavior`s on
  foreground/background/urgent, opaque/glassy/none background looks,
  blur sync via `omarchy-bar sync-glass` (Hyprland toggle file + reload),
  bar-off flag probe with a toggles-directory watch, transparent-foreground
  sampling helper.
- `bin/omarchy-bar`: background cycle `none -> glassy -> opaque`; glassy blur
  through a Hyprland config toggle snippet and `hyprctl reload`.

Machine facts (read-only checks): `inotifywait` installed, `xkbcli` missing
(the widget falls back to the first word of the layout description, "GER"),
`xdg-terminal-exec` installed, blur currently disabled
(`decoration:blur:enabled bool: false`), every keyboard reports the single
layout `de`, the active Omabuntu palette state is `matte-black`
(`~/.local/state/omabuntu/current/theme.json`, written by the reviewed
`tools/theme_backend.py`).

## Current project gaps

- No menu widget on the bar; only Super+Space / Super+Esc shortcuts.
- No keyboard-layout widget; `Commons/Util.qml`, `InputDevices.qml`,
  `InputMethodState.qml` are not staged.
- `Color.qml` is a fixed palette; the bar hardcodes `#101315`/`#cacccc`
  and ignores the theme state it already has.
- No color transitions, no background looks, no bar-off flag.

## Safety constraints

- No package install (offering optional `xkbcli` separately), no Hyprland
  config edit or reload, no login/session change, no autostart.
- The glassy blur sync uses live-only `hyprctl keyword layerrule` on the
  bar's own layer namespace; it never flips `decoration:blur:enabled`
  (global desktop appearance stays user-owned) and never reloads.
- `bar.run` on the panel bar API is an allowlist (exact regexes:
  `hyprctl switchxkblayout <quoted-name> <index>` segments and
  `xdg-terminal-exec`), executed detached through bash only after every
  `;`-separated segment validates. PortTrayHost keeps its documented
  no-command-runner boundary.
- The upstream fcitx input-method indicator is not ported;
  `InputMethodState` is a restricted authored singleton (no state, cycle
  refuses) so the widget shows the xkb layout only.
- bar-off is observed from `~/.local/state/omabuntu/toggles/bar-off`; no
  tool writes that flag in this change set.

## Proposed shape

1. Menu widget: authored `MenuButton.qml` using the original `BarIconButton`
   with an `iconComponent` hosting `OmarchyMark.qml` (a `QtQuick.Shapes`
   `PathSvg` of the extracted outline; the module is already staged via
   `IconContentBounds`). Left click toggles the root route of the existing
   `CommandMenu` through a new `openMenuRoute` wiring; right click runs
   `xdg-terminal-exec` through the allowlisted `run`. Mounted first in the
   left section, before the workspaces.
2. Keyboard layout: vendored byte-identical `KeyboardLayout.qml`,
   `KeyboardLayoutModel.js`, `Commons/Util.qml`, `Commons/InputDevices.qml`;
   authored restricted `Commons/InputMethodState.qml`. One witnessed
   transformation (`keyboard-layout-widget-v1`): the visibility rule gains
   `|| setting("alwaysShow", true)` because this seat runs a single layout
   and upstream would hide the widget the user explicitly asked for.
   Mounted between tray and Bluetooth. Click cycles layouts through the
   allowlisted `run`.
3. Frame/theme: `Color.qml` loads the Omabuntu theme state (`theme.json`)
   through a watched `FileView` (defaults unchanged) and exposes
   `bar.background`/`bar.active`; `TrialPanel.qml`, `PortTrayHost.qml` and
   `LiveStatus.qml` bind to it instead of hardcoding. The bar gains the
   upstream 420 ms OutCubic color behaviors, the three background looks read
   from `~/.local/state/omabuntu/current/bar.json` (default opaque), live
   layerrule blur sync for glassy, and the bar-off probe/watch with the
   upstream park-off-screen + `ExclusionMode.Ignore` behavior.

Provenance: new upstream records in `upstream/clock-preview.json` (blobs,
SHAs, transform ids, mirrors), mark path data recorded in
`upstream/omarchy-mark.json`, staging maps updated in
`tools/check_clock_preview.py`.

## Explicit exclusions

- Importing `omarchy.ttf` (third-party agent marks inside the binary font);
  rendering uses the extracted U+E900 outline only.
- Upstream input-method indicator (`indicator.py`, fcitx/ibus integration).
- `xkbcli` briefs were initially missing (fallback label "GER"); the user
  installed `libxkbcommon-tools` 1.13.1-1 on 2026-10-25 from the already
  configured `universe` archive, so the label reads "DE". Recorded in
  [dependencies](../docs/dependencies.md).
- Global blur enablement, Hyprland reload, any toggle/config-file write.
- Widget drag/drop, center gestures, hover reveal, per-monitor workspace
  blocks, position other than top: unchanged existing exclusions.
- Menu rows or CLI to switch bar background or bar-off state: follow-up.
- Transparent-look foreground contrast sampling (`omarchy-bar-text-color`):
  `none` keeps the theme foreground; documented deviation.

## Tasks

- [x] Fetch and verify pinned upstream sources for all three items.
- [x] Write `tools/extract_menu_mark.py`, extract and record the U+E900
      outline (`upstream/omarchy-mark.json`).
- [x] Author `OmarchyMark.qml`, `MenuButton.qml`, `InputMethodState.qml`.
- [x] Vendor `KeyboardLayout.qml`, `KeyboardLayoutModel.js`, `Util.qml`,
      `InputDevices.qml` byte-identically; witnessed visibility transform
      with mirror in `config/shell/preview/`.
- [x] Rework `Color.qml` onto the theme state; rebind `TrialPanel.qml`,
      `PortTrayHost.qml`, `LiveStatus.qml`; add color behaviors, background
      looks, bar-off, allowlisted `run`, menu wiring. Blur sync was dropped
      after a live probe: Hyprland 0.56 has no runtime layerrule keyword
      (config-only), so glassy keeps the faint background and blur stays the
      user's own global setting.
- [x] Update provenance manifests and `check_clock_preview.py` staging maps.
- [x] Tests: mark data/manifest consistency, keyboard transform witnesses,
      allowlist validation, background-look parsing, suite green (399 pass).
- [x] Update `WORKLOG.md` and docs.
- [ ] Ask before packaging and replacing the running bar process.
