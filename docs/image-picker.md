# Image picker (theme app and backgrounds)

Omarchy opens a dedicated `omarchy.image-picker` plugin from Style > Theme:
a full-screen carousel with one large centered preview (768x475), skewed
neighbor slices, a label line, and type-to-filter narrowing. This is the
reviewed Omabuntu reproduction: `config/shell/preview/ImagePicker.qml` with
the pure logic ported in `config/shell/preview/ImagePickerModel.js`, from
the pinned commit `03ff1eff3812933f7088484533784d2f63eaf19a`. No upstream
picker script is imported or executed.

## Surface

The carousel keeps the pinned constants: expandedWidth 768, expandedHeight
475, sliceWidth 108, sliceHeight 432, sliceSpacing -30, skewOffset 28, the
preview radius from the screen width, the Shape + MultiEffect skewed slice
masks, the 0.42 dim on unselected slices, and the reveal contract (the card
renders at opacity 0 until the visible previews have settled, with the 400
ms fallback). Left/Right/Tab move with wrap, Return applies, Escape clears
the filter then closes, printable keys filter, a click selects or applies.
Keyboard focus is OnDemand like the other reviewed surfaces, not upstream's
exclusive grab. Colors come from the watched theme singleton: background,
foreground, accent, and urgent for the note line.

## Sources

- Themes: the 23 recorded palettes from `config/menu/themes.json`, each
  with its imported upstream preview image under
  `config/menu/themes-previews/` (per-file provenance and the license
  caveat in `upstream/theme-backgrounds.json`). The preview shows the
  imported image; a theme without one falls back to the palette painting
  (background, accent bar, seven color chips, the name, and the mode). The
  current theme is preselected.
- Backgrounds: the current theme's imported upstream stills first (under
  `config/menu/backgrounds/<theme>/`), then Ubuntu's
  `/usr/share/backgrounds` plus files in `~/Pictures`, all read through the
  reviewed helper. The preview shows the image file itself
  (WebP needs the Qt image plugin from
  `qt6-image-formats-plugins`; see [dependencies](dependencies.md));
  there is no on-disk thumbnail generation and no video support
  (ffmpegthumbnailer stays out). Only static images appear.

## Apply

Selection dispatches through `tools/menu_model.py run <provider row id>`;
the surface never runs a command and never sends a file path. A theme apply
is the reviewed `theme_backend.set_theme`: state plus backup, the live
bar recolor plus the two Hyprland border keywords, the same two color
literals persisted in the user's `hyprland.lua` (backup first, shape
checked, never reloaded by the backend), and that theme's background
recorded and applied through the reviewed background path; the picker then
closes like upstream. A background apply records state plus backup and, when a hyprpaper daemon
answers, sets the still per monitor through the current request
`hyprctl hyprpaper wallpaper <mon>,<path>` (hyprpaper 0.8.4); a daemon that
rejects that request falls back to the pre-0.8.4
preload/wallpaper/unload sequence. An applied choice closes the picker like
upstream; only an unapplied choice keeps it open with the recording note
("Background recorded. No wallpaper daemon answered…"), shown only when the
helper reports `applied` false. A refusal shows the note line and keeps the
picker open.

## Not included

- Upstream video backgrounds and intro/transition presentations, PreviewHold
  decode warming, theme deletion, user theme repositories, dmenu modes,
  locale catalogs. The imported stills and previews carry only the upstream
  root MIT with no per-image license record; publication of the repository
  with those assets bundled is a separate user decision.
- hyprpaper autostart, supervision or service activation: the apply path only
  uses a daemon that is already running (see [dependencies](dependencies.md)
  for the installed package). Starting it per session is an approved
  session-lifetime grant, not an autostart or a verified logout-cleanup
  mechanism; session lifecycle enforcement still needs testing. A further
  session start needs approval. Any persistence across a Hyprland
  restart beyond the reviewed hyprland.lua color edit is excluded.

## Evidence

Python contracts: `tests/test_image_picker.py` (derivation witnesses, the
preview-image wiring with the palette fallback), `tests/test_menu_model.py`
(picker route registry, provider rows carrying palette colors and the
preview image), `tests/test_menu_backends.py` (border persistence, the
per-theme background choice, the hyprpaper sequence against fakes),
`tests/test_clock_preview.py` (authored profile rules:
one helper Process, exactly one 400 ms reveal Timer, no execDetached).

Offscreen report: `work/picker-port/20261025T232700.448600Z/report.json`
(`isolated-picker-fixtures-passed`): 23 theme rows with palette colors,
the current theme preselected, filter narrowing, carousel movement, a
theme apply recording state plus backup, background rows from a staged
`~/Pictures`, and the unapplied-choice daemon note — all through the real
helper inside bwrap. No shortcut registration, hyprctl success, live
wallpaper apply, native focus, or visual acceptance is claimed. A live
apply against the installed hyprpaper 0.8.4 records `applied: true`
(see WORKLOG, 2026-10-26); the painted wallpaper is the user's visual
check.
