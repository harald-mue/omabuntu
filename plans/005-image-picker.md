# Image picker for themes and backgrounds

Status: applied. The user approved packaging and a bar restart on
2026-10-25. Release `20261025-local.19` is running. Rollback is
`20261025-local.18`. This plan does not approve a Hyprland binding, a
package installation, a wallpaper daemon, or a commit.

## Goal

Reproduce Omarchy's theme app: the pinned `omarchy.image-picker` plugin at
`03ff1eff3812933f7088484533784d2f63eaf19a` (files fetched read-only into
ignored `work/image-picker-analysis/03ff1eff/`). Upstream, Style > Theme
opens that picker as a full-screen carousel with one large centered preview
(768x475), skewed neighbor slices, a label line, and a type-to-filter
narrowing. Selecting a theme runs `omarchy-theme-set`. This plan ports the
picker as an Omabuntu surface, gives themes a palette preview, and gives
backgrounds the same carousel from Ubuntu's own background directories.

## Evidence compared

- `shell/plugins/image-picker/ImagePicker.qml` (905 lines): OverlayWindow,
  WlrLayershell namespace `omarchy-image-selector`, exclusive keyboard
  focus, carousel constants (expandedWidth 768, expandedHeight 475,
  sliceWidth 108, sliceHeight 432, sliceSpacing -30, skewOffset 28,
  previewRadius from the panel width), Shape mask + MultiEffect for the
  skewed slices, reveal-on-settled (opacity 0 until every visible preview
  decoded and two frames presented, 400 ms fallback), Left/Right/Tab
  navigation with wrap, Return applies, Escape clears the filter then
  closes, printable keys filter, click selects / applies, dim overlay 0.42
  on unselected slices, label line with text outline.
- `shell/plugins/image-picker/ImagePickerModel.js`: pure logic (row
  loading, filter matching, index bookkeeping, visible window sync that
  preserves delegates while selection moves).
- `shell/plugins/image-picker/list.sh`: enumerates image dirs, generates
  video thumbnails with ffmpegthumbnailer, falls back to the file itself
  for static images.
- Theme rows come from `omarchy-theme-switcher --print-rows` (one preview
  image per theme); applying runs `omarchy-theme-set`.
- `style.theme` in `default/omarchy/omarchy-menu.jsonc` summons the picker
  with `{"source":"themes"}`; `style.background` runs the background
  switcher script.
- Machine facts: `qml6-module-qtquick-shapes` and `-effects` 6.10.2 are
  installed (QtQuick.Shapes, QtQuick.Effects available to the reviewed
  runtime). No wallpaper daemon is installed.

## Current Omabuntu gaps

- Style > Theme opens the flat provider submenu inside the command menu
  card; there is no carousel and no visual preview of a theme.
- Style > Background lists file names only; no preview.
- `background_backend.py` records state but applies nothing (no daemon);
  theme apply recolors the bar and the two Hyprland border keywords.

## Safety constraints

- Derive the surface and the model from the pinned sources with narrow,
  reviewed adaptations; record provenance. No upstream theme background
  images are imported (license not cleared; third-party artwork).
- Background previews render Ubuntu's `/usr/share/backgrounds` files and
  files in `~/Pictures` only, read-only; the picker writes no image files
  and generates no thumbnails on disk (static images only, upstream's
  in-memory fallback path).
- Applying a theme or background goes through the existing allowlisted
  helper dispatch (`menu_model.py run <provider row id>`); the surface
  never runs a shell command and never sends a file path to execute.
- Keyboard focus is OnDemand like the other reviewed surfaces, not
  upstream's exclusive grab; nothing activates a lock or idle state.
- No new keybinding; the picker opens from the command menu's Style rows.
- No wallpaper daemon activation: applying a background still records
  state only, and the picker says so instead of implying a live wallpaper.

## Proposed shape

1. `config/shell/preview/ImagePickerModel.js`: the pinned pure logic
   (nameForPath, labelForPath, itemMatches, firstMatchingIndex,
   indexForSelectedImage, nextSelectedIndexForFilter, matchingIndices,
   visibleWindow, syncWindow) ported unchanged; the delete-theme helpers
   stay out (no user theme repos).
2. `config/shell/preview/ImagePicker.qml`: the derived carousel. Rows come
   from the reviewed helper (`providers style.theme` / `providers
   style.background`). Theme preview cards are painted from the recorded
   palettes (background ramp, accent, color chips, name, mode); background
   preview cards show the image file itself. Apply dispatches through the
   helper; a gate refusal shows the note line and keeps the picker open.
3. `tools/menu_model.py`: the themes provider rows carry the palette subset
   the preview needs; the surface-internal action registry admits
   `omabuntu-open:themes|backgrounds`.
4. `config/shell/omabuntu-menu.jsonc`: `style.theme` and `style.background`
   become action rows that open the picker (upstream shape); their
   `provider` fields stay, because apply dispatch re-derives rows by id.
5. `CommandMenu.qml` routes `omabuntu-open:themes|backgrounds` to the
   picker through TrialShell wiring; `TrialShell.qml` mounts and destroys
   the picker with the other surfaces.
6. Tests: helper row contract, action registry, derivation witnesses, and
   an offscreen bwrap fixture (`tools/check_image_picker.py`) that drives
   the real surface against the real helper: theme carousel row count,
   current-theme selection, filter, apply recording state plus backup, and
   background rows from a staged `~/Pictures`.
7. `check_command_menu.py` stages adapt: the Theme row now opens the picker
   (route counter) instead of entering the provider submenu; the provider
   apply coverage moves to the picker fixture.

## Explicit exclusions

- Video backgrounds and ffmpegthumbnailer.
- Theme deletion, user theme repos (`omarchy theme install`), PreviewHold
  decode warming, background transition snapshots and intro videos,
  dmenu tempfile handshake, right-to-left catalog text, locale catalogs.
- Upstream theme background images in any form.
- A live wallpaper apply: `background_backend.set_background` keeps
  recording state only until a daemon is separately approved.
- Persistence of a theme choice across a Hyprland restart without an
  approved user-config edit.

## Tasks

- [x] Port `ImagePickerModel.js` and derive `ImagePicker.qml`.
- [x] Helper: theme rows carry palette colors; action registry admits the
      two new surface-internal routes.
- [x] Menu definitions and CommandMenu routing; TrialShell mounting.
- [x] Unit tests and the offscreen picker fixture; adapt the menu fixture.
- [x] Update docs and WORKLOG.
- [x] Ask before packaging and restarting the bar. Applied as
      `20261025-local.19`; rollback is `.18`.
