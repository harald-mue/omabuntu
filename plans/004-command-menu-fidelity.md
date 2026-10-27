# Command menu fidelity

Status: applied. The user approved packaging and a bar restart on
2026-10-25. Release `20261025-local.18` was started for this change.
Rollback at that install was `.15`. Release `20261025-local.19` later
replaced the running bar; see `WORKLOG.md`.
Releases `.16` and `.17` were installed and not left running: `.16` did not
load because `Color.qml` used `FileView` without its import, and `.17` was
stopped because several files used `Commons` without the import alias.

## Goal

Make the Super+Space card follow the pinned Omarchy menu at
`03ff1eff3812933f7088484533784d2f63eaf19a` instead of the reduced top-aligned
stand-in. Broken icons are wrong codepoints, not a missing font.

## Evidence compared

`shell/plugins/menu/Menu.qml` centers the card, paints it from the theme
menu colors, and draws a plain "Go…" search line. The selected row uses the
foreground at 8% and the accent as its text. Icons are Nerd Font scalars at
`Style.font.iconLarge` (18). `JetBrainsMono Nerd Font` on this machine
contains every pinned glyph used by the rows we kept, including U+F003B.

`config/shell/omabuntu-menu.jsonc` stored several of those scalars as broken
`\u` surrogate escapes. Apps, Learn, Theme, Hibernate, and Shutdown decode
to lone surrogates, which render as missing glyphs. Suspend and Logout
decode to different, valid codepoints.

Before this release, `CommandMenu.qml` sat at the top, used the bar colors
`#101315` / `#cacccc`, a filled search pill, 16 px icons, and a flat
selection. It did not read the active matte-black palette. Root rows are
only Apps, Learn, Style, and System. Trigger, Setup, Install, Remove,
Update, and About stay excluded.

## Safety constraints

No Hyprland config edit, no new binding, no power action, and no theme or
background apply. Excluded sections are not stubbed as clickable rows.
The approved restart is release `.18`.

## Proposed shape

- Rewrite kept icons as the pinned scalars. A test compares those codepoints
  and rejects a lone surrogate.
- `menu_model.py defs` includes the current palette's background, foreground,
  and accent. The card uses them the way Omarchy's menu colors do: scrim at
  half the background, selected fill at 8% of the foreground, selected text
  in the accent.
- Center the card. Drop the filled search pill. Search text is the plain
  title plus ellipsis at 58% until the user types. Icon size 18, row label
  16, padding 18, header 34.
- Ask before packaging and restarting the bar.

## Explicit exclusions

- Trigger, Setup, Install, Remove, Update, About, dmenu, and locale catalogs.
- Importing `Menu.qml` itself. It needs the upstream shell host, app library,
  and dmenu paths that this bar does not run.
- A wallpaper daemon, autostart, or a Hyprland config write.

## Tasks

- [x] Store the pinned icon scalars and test them.
- [x] Paint and place the card from the original menu rules and the active palette.
- [x] Update `docs/command-menu.md` and `WORKLOG.md`.
- [x] Ask before packaging and restarting the bar. Applied as
      `20261025-local.18` after the load errors above were fixed.
