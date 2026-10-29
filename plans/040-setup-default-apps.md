# Setup default browser and terminal

## Goal and evidence

Add Omarchy's Setup > Defaults > Browser and Terminal rows to the Super+Space
menu. Pinned Omarchy `03ff1eff` lists fixed browser and terminal choices with
`checked:` guards and `omarchy-default-browser` / `omarchy-default-terminal`.
This Ubuntu step keeps only installed programs and uses `xdg-settings` and
`xdg-terminal-exec` instead. Nothing is installed or removed from the menu.

On this machine the live defaults were Edge (`microsoft-edge.desktop`) and
Ptyxis (`org.gnome.Ptyxis.desktop`). Chrome, Ghostty, and Kitty are also
installed.

## Gap

The authored menu had Apps, Learn, Style, and System only. There was no
`tools/defaults_backend.py`, no providers, and no Setup root row.

## Safety and exclusions

- Discover browsers and terminals from `.desktop` files with working binaries
  only. Hide `NoDisplay` entries and collapse duplicate vendor ids.
- Browser apply: `xdg-settings set default-web-browser <desktop-id>` through
  a fixed argv allowlist.
- Terminal apply: write `~/.config/hyprland-xdg-terminals.list` (or the generic
  `xdg-terminals.list` when the session desktop is unknown), clear the
  xdg-terminal-exec cache, and verify with `--print-id`. Do not call
  `update-alternatives` or install packages.
- No editor, agent, dictation, DNS, keyboard, or other Setup sections in this
  step.
- No bar restart, compositor reload, or commit until asked.

## Tasks

- [x] Add `tools/defaults_backend.py` and wire providers in `menu_model.py`.
- [x] Add Setup > Defaults > Browser/Terminal to `omabuntu-menu.jsonc`.
- [x] Package the helper and cover discovery/apply with unit tests.
- [x] Update `docs/command-menu.md` and `WORKLOG.md`.
- [x] Run the unit suite.
- [x] After approval, back up and replace the active release copies of the helper,
  menu model, and menu definition. Integrity verification passed. The bar was
  not restarted.
