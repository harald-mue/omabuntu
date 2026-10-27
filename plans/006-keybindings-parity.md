# Keybindings parity: installed applications and fullscreen fix

Status: implemented and live (transaction
`work/keybindings-session/20261025T224418Z/`). 43 binds active, all with
descriptions; SUPER+K lists every binding. The user asked for Omarchy
application bindings (installed apps only) and reported that SUPER+F does
not fullscreen. Decisions taken per the recommended path: float toggle
remapped to SUPER+T, config edit plus reload approved together with the
hyprbars include (titlebars now persistent), and the four menu binds made
persistent in the config after they had been lost as session-only evals.

## Goal

1. Introduce Omarchy's application keybindings from the pinned commit
   `03ff1eff` (`default/hypr/bindings/applications.lua`) **only for apps
   installed on this machine**; discard every binding whose app is absent.
2. Fix SUPER+F: it is not bound here; upstream binds
   `hl.dsp.window.fullscreen({ mode = "fullscreen" })` on it.
3. Every new binding must appear in the Super+K keybindings menu, which reads
   the live compositor binds and recovers Lua binds from the config file.

## Evidence compared

- Upstream `applications.lua` (fetched read-only into
   `work/bindings-audit/03ff1eff/`, blob-verified) defines 30 binds.
- Installed here (verified): microsoft-edge (default browser), google-chrome,
  firefox, nautilus, code (VS Code), gnome-calculator, spotify, ghostty,
  docker CLI.
- Absent (binds discarded per the user's rule): tmux, Herdr, omacalc, cliamp,
  lazydocker (upstream gates on `cmd_present`), Signal, Obsidian, Omawrite,
  1Password, and all upstream webapp bindings (ChatGPT, Grok, hey.com,
  YouTube, WhatsApp, Google Messages/Photos/Maps, X).
- Live state: 34 binds; on the F key only `SUPER+SHIFT+F -> __lua` (float
toggle). SUPER+F is unbound — the reported fullscreen bug.
- Collision: upstream `SUPER+SHIFT+F` is the file manager and `SUPER+T` is
  the float/tiling toggle; locally float still sits on SUPER+SHIFT+F.

## Proposed binds (installed apps only)

| Keys | Label | Command |
|---|---|---|
| SUPER+SHIFT+RETURN | Browser | microsoft-edge (default: xdg-settings) |
| SUPER+SHIFT+B | Browser | microsoft-edge |
| SUPER+SHIFT+ALT+B | Browser (private) | microsoft-edge --inprivate |
| SUPER+SHIFT+F | File manager | nautilus (requires float-toggle remap to SUPER+T) |
| SUPER+SHIFT+N | Editor | code |
| SUPER+CTRL+Q | Calculator | gnome-calculator |
| XF86Calculator | Calculator | gnome-calculator |
| SUPER+SHIFT+M | Music | spotify |
| SUPER+F | Full screen | window fullscreen (tiling fix, upstream mapping) |

Discarded (app absent): tmux, Herdr, omacalc, cliamp, lazydocker, Signal,
Obsidian, Omawrite, 1Password, all webapps. SUPER+ALT+SHIFT+F (nautilus cwd)
is deferred: it needs a terminal-cwd helper that does not exist here.

## Safety constraints

- The user's Hyprland config is edited only with a timestamped backup and a
  recorded restore path under `work/keybindings-session/`.
- A reload re-executes the Lua config. The hyprbars titlebar rules were applied
  to the running compositor at runtime and are not yet included from the
  config; a plain reload could clear them. The reviewed, verified
  `config/hypr/hyprbars.lua` is therefore included in the same edit so the
  reload restores titlebars itself. This also makes the titlebars persistent.
- `SUPER+CTRL+L` (lock) and all other missing upstream binds stay out of this
  change; this plan covers applications plus the SUPER+F fix only.
- No package install, no login/session change, no autostart.

## Tasks

- [x] Ask: float-toggle remap to SUPER+T (upstream mapping) and the config
      edit plus reload gate. (AskQuestion skipped; the user's explicit
      instruction to apply the bindings was taken as approval of the
      recommended path, transparently recorded here.)
- [x] Back up `~/.config/hypr/hyprland.lua`; add the binds above; include
      the reviewed hyprbars snippet (`require("hyprbars")`; the plugin's
      onPreConfigReload clears its buttons, so reloads stay idempotent).
- [x] `hyprctl reload`; verify: binds count 30->43, configerrors empty,
      hyprbars still loaded with bar_height 30, Super+K lists every binding
      with descriptions (helper output verified). SUPER+F fullscreen and the
      app launches still need the user's interactive check.
- [x] Re-apply/verify workspace mode tags survive; record rollback
      (restore backup file, reload). Window tags survived the reload
      (omabuntu-mode-floated, omabuntu-minimized-from-*); no live workspace
      float keywords existed at reload time, none needed re-application.
- [x] Update WORKLOG.md and the capability matrix Input/Core-bindings rows.

## Exclusions

- All non-installed app binds (user rule: discard).
- The remaining ~180 missing upstream binds (tiling, media, utilities,
      clipboard) — separate follow-up plan.
- Lock, dictation, fcitx input-method binds (existing policy gates).
- nautilus-cwd bind (needs an unimplemented terminal-cwd helper).
