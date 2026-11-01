# Suppress the update-news popup in the generic fresh profile

## Goal and evidence

Plan 067 added `ecosystem.no_update_news = true` to the installer-managed
snippet `config/hypr/omabuntu-managed.lua` after `hyprland-update-screen`
(hyprland-guiutils) crashed with SIGSEGV in Hyprtoolkit on a GPU-less Q35 VM.
Hyprland's `CVersionKeeperManager` launches that screen once per compositor
major upgrade; see plan 067 for the pinned source evidence.

The **generic fresh profile** `config/hypr/session-template.lua.in` (rendered
by `session_config.render` into `~/.config/hypr/omabuntu-session.lua` for
machines without their own Hyprland configuration) still sets only
`ecosystem = { no_donation_nag = true }`. A fresh public install therefore keeps
the update-news popup and, on GPU-less systems, the plan-067 crash.

## Shape

- `config/hypr/session-template.lua.in`: `ecosystem = { no_donation_nag = true,
  no_update_news = true }` — one line, same table, matching the managed
  snippet. Both keys exist in the 0.56.2 and 0.57.0 schema (plan 067 evidence).
- `tests/test_session_config.py`: assert the rendered generic module contains
  both keys, so the fresh profile and the managed snippet stay in sync.
- `tests/test_hypr_settings.py` continues to cover the managed-snippet side.

## Safety and exclusions

Config value only: no binds, autostart, plugin load, monitor rule or activation
change. Existing private profiles (including this machine's) are never rewritten
by this template change; only fresh generic profiles and future `--session-config`
re-renders of owned modules acquire it. No commit/push/release beyond the
reviewed commit; public delivery through a later signed release (v0.1.8).

## Tasks

- [x] Add the key to the template.
- [x] Add/extend the session-config test.
- [x] Run the full suite.

## Result

`config/hypr/session-template.lua.in` sets
`ecosystem = { no_donation_nag = true, no_update_news = true }`; the rendered
config Lua test asserts both keys. Full suite passed. Private installed
profiles are untouched; fresh generic profiles acquire the suppression through
the next render.