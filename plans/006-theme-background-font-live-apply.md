# Theme backgrounds, persistent accent, live font apply

Status: drafted, awaiting the user's approval decisions below. This plan
is not approval for package installation, user-config edits, daemon
starts, bar replacement, or a commit.

## Goal

Four user-reported defects of the live style surfaces, fixed with the
pinned upstream behavior as the model (commit
`03ff1eff3812933f7088484533784d2f63eaf19a`):

1. Themes have no backgrounds: upstream ships
   `themes/<name>/backgrounds/` stills and a `preview.png` per theme; the
   theme picker previews the theme image and a theme apply switches the
   background. Omabuntu records colors only and applies no wallpaper.
2. The active window border stays blue regardless of theme.
3. Font selection (Style > Font) changes nothing visible.
4. Font list entries do not render in their own family.

## Evidence compared

Upstream (read-only probes of the pinned commit):

- `themes/`: 23 themes, 97 still background images, 59.1 MB total;
  video intros (96 MB) are excluded here. Theme picker preview is
  `preview.png`, else the first sorted `backgrounds/` image
  (`bin/omarchy-theme-switcher`, `find_preview`).
- `bin/omarchy-theme-bg-set`: symlink to the chosen image, then the shell
  is told to repaint (`omarchy-shell -q background set`). Upstream's
  shell draws the wallpaper (OWE); Omabuntu has no wallpaper engine.
- `bin/omarchy-theme-set`: keeps a per-theme background choice
  (`theme-backgrounds` state), applies it with the theme.
- `bin/omarchy-font-set`: rewrites terminal configs (ghostty:
  `font-family = "..."` + SIGUSR2), writes
  `~/.config/fontconfig/fonts.conf` prepending the family for `monospace`
  (canonical for the shell and Qt), then restarts the shell. gsettings is
  not used upstream; the existing gsettings write stays as a GTK extra.

Live session (read-only, 2026-10-25):

- `hyprctl getoption general:col.active_border` = `ff7aa2f7`
  (tokyo-night blue) while `current/theme.json` records `last-horizon`.
  Cause: `~/.config/hypr/hyprland.lua` lines 13-14 hardcode
  `rgb(7aa2f7)`/`rgb(414868)`; `hyprctl keyword` in
  `theme_backend.set_theme` applies only until the next config reload
  (the hyprbars/hyprpm load at 23:09 reset it). The theme state itself is
  correct; persistence is missing.
- No wallpaper daemon is installed or running (no swww, hyprpaper,
  swaybg). `hyprpaper 0.8.3-1` is available in Ubuntu `resolute/universe`.
- Bar fonts are hardcoded `"JetBrainsMono Nerd Font"`
  (`Style.qml`, `PreviewContent.qml`, `CommandMenu.qml` `rowFont`);
  `font.txt` records `DroidSansM Nerd Font` from an earlier selection.
  The gsettings write reaches GTK apps only after they restart; nothing
  visible in this Hyprland session changed.
- Upstream `Menu.qml` does not render font rows in their own family; item
  4 is a requested Omabuntu deviation, documented as such.

## Current project gaps

- `config/menu/themes.json` records colors only; background assets were
  never imported (license not cleared per-image upstream).
- `background_backend.py` lists Ubuntu `/usr/share/backgrounds` and
  `~/Pictures`, records the choice, applies nothing.
- `theme_backend.py` never persists border colors to the user's Hyprland
  config (by design); the keyword path is transient.
- `font_backend.py` writes gsettings and state only; the bar does not read
  `font.txt`; provider rows carry no per-row font.

## Safety constraints

- Ask before: installing hyprpaper, editing `~/.config/hypr/hyprland.lua`,
  writing `~/.config/fontconfig/fonts.conf` or the ghostty config,
  starting a daemon, replacing/restarting the bar.
- Back up each affected path before writing (existing
  `menu_common.backup_and_write` plus a config backup for hyprland.lua).
- Asset license: upstream declares only the root MIT; the individual
  photos carry no recorded upstream license. Import stays local; the
  publication gate is unchanged and the caveat is recorded in the
  provenance file. Committing 59 MB of images into Git is the user's
  explicit decision.
- No video wallpapers, no intro videos, no OWE/swww engine, no theme
  deletion, no user theme repositories, no font size selection.
- hyprpaper, when approved, gets the same session-lifetime grant pattern
  as the bar (explicit start per session, no autostart timer, no
  supervision). webp support must be verified on the installed hyprpaper
  before wiring; if unsupported, stills are converted once at import and
  the converter dependency is asked for separately.

## Proposed shape

- Assets under `config/menu/backgrounds/<theme>/` (97 stills, upstream
  file names) plus `config/menu/themes-previews/<theme>.png`; provenance
  with per-file blob SHA and URL in `upstream/theme-backgrounds.json`
  next to the existing source records.
- `theme_backend.set_theme`: keep the live `hyprctl keyword` apply, and
  additionally rewrite only the two color values in hyprland.lua
  (regex-guarded `active_border`/`inactive_border` string literals, backup
  first) so reloads keep the theme; record the per-theme background choice
  and apply that theme's background like upstream.
- `background_backend`: rows list the current theme's backgrounds first,
  then the existing Ubuntu directories; `set_background` applies live
  through `hyprctl hyprpaper preload|wallpaper` when the daemon is
  running, otherwise records only (today's behavior, message stays).
- `font_backend.set_font`: keep gsettings; add the fontconfig
  `monospace` prepend (fonts.conf, backed up) and the ghostty
  `config.ghostty` `font-family` rewrite + SIGUSR2; state file unchanged.
- Bar QML: one watched `font.txt` singleton (the `Color.qml` FileView
  pattern); `Style.qml` family, `CommandMenu.qml` `rowFont`, and the
  preview panel font strings bind to it; fallback stays
  JetBrainsMono Nerd Font. No bar restart is required for later font
  changes; one restart is required to ship the wiring.
- Font provider rows carry `font: <family>`; the CommandMenu provider
  row delegate renders the label in that family (documented deviation
  from upstream).
- ImagePicker themes mode: preview image from
  `themes-previews/<theme>.png` (fallback: first background, then the
  palette chips as today).

## Explicit exclusions

- GTK/terminal/editor color retint beyond the border keywords (upstream
  `omarchy-theme-set` retints many apps; colors apply to bar + borders
  only, as today).
- Background intro videos, animated wallpapers, transition caches.
- dmenu select/input modes, locale catalogs (unchanged plan-002 gaps).
- Font size setting; the existing size-preserving rule stays.
- Any autostart/supervision for hyprpaper or the bar.

## Tasks

- [ ] User decisions: asset commit scope, hyprpaper install, hyprland.lua
      border edit, font user-config writes, bar restart.
- [x] Import the 97 stills + 23 previews with the provenance record.
- [x] `theme_backend`: persistent border colors, per-theme background
      state and apply.
- [x] `background_backend`: theme-first rows, live hyprpaper apply path.
- [x] `font_backend`: fontconfig + ghostty writes next to gsettings.
- [x] Bar QML: watched font singleton, bound font strings, per-row font
      rendering in the menu card.
- [x] Tests: new/updated unit tests for all backends and the QML staging
      contracts; `python3 -m unittest discover -s tests -v` green.
- [x] Docs and WORKLOG updated; live activation steps listed with their
      approval status.
