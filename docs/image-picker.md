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
  reviewed helper. Before any theme is selected, all available theme stills
  are listed instead of hiding downloaded artwork. The Ubuntu/Pictures roots
  remain non-recursive. The preview shows the image file itself
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
recorded and applied through the reviewed background path. A background apply
records state plus backup and sets the still per active monitor through
`hyprctl hyprpaper wallpaper <mon>,<path>` (reviewed against Hyprland 0.57.1 /
hyprpaper 0.8.5). Only an explicit legacy "not preloaded" reply enables the old
preload sequence; connection/handshake/file/rendering failures never trigger
legacy fallback. Cleanup unloads that file, not every client's preloads.
Comma/control-separated paths are refused rather than misparsed by IPC.

The helper retains command errors, stderr, missing commands, timeouts and partial
output failures. It queries `listactive` after acceptance and checks each active
output against the selected image. Missing/wrong targets are not reported as
applied. Older daemons explicitly lacking this status query can report acceptance
with `active_reported: null`; this is not target or rendering verification.
An applied choice closes the picker; an unapplied choice stays open with
"Background recorded." and its actual failure. A theme whose colors were saved
but whose wallpaper failed also stays open with that distinction. No rollback
of successfully changed colors is implied by the wallpaper error.

Login restoration retries only transient daemon/output readiness within a total
13-second IPC/readiness budget (per-probe maximum 5 seconds); interactive image
selection does not wait for or start a missing daemon. The manager's existing
20-second helper boundary remains. Saved wallpaper bytes/choices are preserved;
application-only updates deliberately do not reapply wallpaper.

### Read-only wallpaper diagnosis

After deploying a release containing this repair, run from the affected
Hyprland terminal:

```sh
omabuntu wallpaper-status
```

This validates the installed release and runs its `background_backend.py diagnose`
helper without creating state/control locks, selecting an image, starting a daemon
or changing a service. The five fixed probes each have a 3-second timeout. Reports
include selected-file existence, available image count, selected session variables,
active targets, service state, version and the last 30 current-boot hyprpaper journal
entries. Missing commands, timeouts and partial failures stay explicit. Review
private paths/display names before sharing; do not commit reports.

A healthy daemon, accepted request or correct active-target report is **not proof
of rendered pixels**. Reports always retain `rendering_verified: false`. If the
VM stays black despite a correct target, examine the actual guest renderer and
EGL/GBM journal errors; no speculative permission/environment/graphics override
is applied. Plan 109 has no guest rendering, service activation or native logout
acceptance.

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
