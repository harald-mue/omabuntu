# Keybindings menu

Omarchy at commit `03ff1eff3812933f7088484533784d2f63eaf19a` opens a searchable
list of the running compositor's bindings with Super+K. The command is
`omarchy-menu-keybindings`, not a bar widget and not `KeyboardPanel.qml`.
Super+Alt+K and Super+Ctrl+K open separate Tmux and Herdr menus and are not
part of this surface.

The upstream scripts are not vendored and are not executed. The behavior below
is the reviewed Python and shell reproduction. It does not create, edit, or
remove bindings.

## Surface

`config/shell/preview/KeybindingsMenu.qml` is an overlay card, 800 by 500
pixels, using the existing shell colors `#cacccc` on `#101315` and
JetBrainsMono Nerd Font. `TrialShell.qml` creates and destroys it with the
other session surfaces. The production catalog stays empty.

Search is the typed text. Escape clears the search, then closes. Arrow keys
move, and Return or a click runs the selected row. Nothing closes the card on
a timer. The prompt is "Search keybindings…". There is no imported locale
catalog; English text is fixed in the shell.

The card registers a Quickshell global shortcut named `omabuntu:keybindings`.
After the approved bar update, one session-only Super+K binding calls that
shortcut. `~/.config/hypr/hyprland.lua` was not rewritten. The binding is lost
when Hyprland restarts, like Super+Alt+Space.

## Rows

The helper `tools/keybindings_menu.py` reads plain `hyprctl binds`. It does
not use `hyprctl -j binds`, because Hyprland 0.56 emits invalid JSON for that
request. On 0.56.2 a record starts with `bind` and then tabbed `modmask`,
`submap`, `key`, `keycode`, `catchall`, `description`, `dispatcher`, and `arg`.

Lua bindings arrive as dispatcher `__lua`. The helper loads the configured
file (`OMABUNTU_KEYBINDINGS_CONFIG`, or `~/.config/hypr/hyprland.lua`) inside
a restricted Lua 5.4 state and records `hl.bind` calls. The state does not
provide `os`, `io`, or `hl.exec_cmd`, and an instruction limit stops a loop.
This is not the upstream `lua -E` scan and it does not `dofile` the home
configuration with the system `lua` binary. Symlinks and files over 256 KiB
are ignored.

A binding Hyprland reports is shown. The full Omarchy catalog is not invented.
Unlabeled Lua rows get a short label from the recovered call, such as
"Close window" or the command text of `hl.dsp.exec_cmd`. A described row whose
command cannot be recovered stays visible and has no action. Empty Lua rows
that still have no label are hidden, as is the Copilot duplicate `code:201`.

Only Close window, Calculator, Toggle scratchpad, and Move window to scratchpad
share a row, and only when both chords run the same command and the combined
chord is at most 35 characters. The first chord leads. Other repeated labels
stay separate. The helper label keeps a 35-character chord field, ` → `,
then the description, at most 78 characters. The card draws those as two
columns: the chord in JetBrainsMono Nerd Font, the description in the selected
UI font. Adwaita Sans is proportional, so one padded line does not line up.
The list is replaced in one step, and the previous rows stay visible until the
new list arrives. Order follows Omarchy's description
priority, not the alphabet, and that order is applied before any translation.

`code:` names use `xkbcli compile-keymap` when that tool is installed. The
small US fallback is used otherwise. Platform files under
`/usr/share/omarchy-platform/key-names` are not read. Two static web-app
shortcuts from the upstream script are not added. Bind dumps are not cached
in Git.

## Selection

Choosing a row reissues the dispatcher and argument from the list just read:

- `exec` tries `hl.dsp.exec_cmd`, then `hyprctl dispatch exec`.
- `lua` sends the recovered `hl.` expression.
- `sendshortcut` tries a key-down and key-up, then `hyprctl dispatch sendshortcut`.
- Any other dispatcher is `hyprctl dispatch` plus its argument.

The helper refuses the request unless that exact dispatcher and argument are
in the list it just read. It also refuses session-ending commands even when
they are configured: `uwsm stop`, `systemctl`, `loginctl`, `shutdown`,
`reboot`, `poweroff`, `halt`, `hyprlock`, `swaylock`, `swayidle`, and the
words lock, suspend, idle, hibernate, exit, and logout. Those rows stay in
the list, including the approved `SUPER+CTRL+L` lock chord. The card says "Session actions stay on their own keys."

An empty `exec`, `lua`, or `sendshortcut` argument is not launched. A command
that is not in the list just read is not launched.

## Not included

- Tmux and Herdr binding menus.
- Creating, editing, or deleting shortcuts.
- The staged `config/hypr/minimal.lua` profile, which is not installed.
- A permanent Hyprland configuration change, autostart, or a timer that closes
  the menu. The Super+K row is visible because Hyprland reports it, but its
  command is not in the Lua file, so selecting that row does not run a guessed
  command. The key itself still opens the menu.

## Evidence

Python contracts cover the column, the four alternative chords, Copilot
hiding, unresolved Lua rows, priority order, the restricted scanner, and the
refusal to run a command that is absent or session-ending. The offscreen
selector is `work/keys-port/20261025T192458.015893Z/report.json`
(`isolated-keys-fixtures-passed`): search, keyboard movement, the monospace
column, and a synthetic Return that only records the selected action. No host
shortcut is registered there, and no `hyprctl` is called.

The approved update installed `20261025-local.13` and kept `.12` as the
previous release. Relocation check:
`work/user-release-checks/20261025T195719.680152Z/report.json`.
Operation report: `work/installed-update-local.13.json`. The running bar is
the installed release, session lifetime, no autostart. Startup logged the
session grant and Configuration Loaded. The only diagnostic is the existing
portal app-ID warning.

Super+K was unbound before the change (31 bindings) and is bound once after
it (32). The Hyprland configuration file's size, mtime, and hash did not
change. The shortcut opened the menu and the same shortcut closed it. The
helper refused a command that was not in the list and refused the configured
session-ending command without running it. Focus left, then focus right, ran
through the helper. No bind dump was saved. This is not acceptance of every
configured command, Tmux, Herdr, or behavior after a Hyprland restart.
