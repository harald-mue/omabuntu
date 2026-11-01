# Disable the Hyprland update-news popup

## Goal and evidence

On the clean VM (Ubuntu 26.04, Hyprland 0.57.0, Q35 without 3D
acceleration), the first Hyprland session after a Hyprland upgrade showed an
apport crash dialog:

- `ExecutablePath /usr/bin/hyprland-update-screen`
- `Package hyprland-guiutils 0.2.2-1ppa2~1resolute1`
- `Title hyprland-update-screen crashed with SIGSEGV in Hyprtoolkit::C...`

Hyprland's `CVersionKeeperManager` (pinned 0.56.2 source
`src/managers/VersionKeeperManager.cpp`, unchanged in 0.57.0) compares the
last-seen version and, once per Hyprland major upgrade, launches
`hyprland-update-screen --new-version <ver>` to show "update news". The tool
renders through Hyprtoolkit/EGL; without hardware GL its EGL init fails and
it segfaults. The crash was also observed for hyprpaper in a GNOME session
(same EGL/DRM cause). It is not caused by Omabuntu code and does not affect
the session; it is a one-time popup because `lastVersion` is written before
the launch.

`config/hypr/omabuntu-managed.lua` already sets `ecosystem.no_donation_nag`,
the same class of Hyprland notification nag. Setting
`ecosystem.no_update_news = true` suppresses the popup. Both keys exist in the
0.56.2 and 0.57.0 config schema (`ConfigValues.cpp`, `hl.meta.lua`), so the
change stays valid for the legacy and target versions.

## Shape

- Add `no_update_news = true` to the `ecosystem` table in
  `config/hypr/omabuntu-managed.lua` (one line, same table as
  `no_donation_nag`). No other managed setting changes.
- Extend `tests/test_hypr_settings.py` `ManagedTemplateTests` to assert the
  new key so the reviewed managed snippet and the deployed snippet stay in
  sync (the file is compared byte-for-byte by `session_config.adoptable`).

## Safety and exclusions

The managed snippet still contains no binds, autostart, monitors or window
rules. The change is a config value only and reversible; the previous file is
backed up under `work/update-news-before/`. It removes the upstream
"what's new" popup for every Omabuntu session, which is the accepted tradeoff
for a popup that crashes on GPU-less systems. No package, service, desktop
deployment, reload, commit or release happens in this task; public
availability needs a later signed release.

## Tasks

- [x] Back up the managed snippet and its test.
- [x] Add `no_update_news = true` and the regression assertion.
- [x] Run the full test suite and whitespace check; report the release
      limitation.

## Result

`config/hypr/omabuntu-managed.lua` `ecosystem` now sets
`no_update_news = true`; the reviewed test asserts it and
`docs/user-installation.md` documents why. Previous files are under
`work/update-news-before/`. Full suite: 1011 tests OK; `git diff --check`
clean. The change ships only when a later signed release deploys the new
managed snippet; it does not touch the running VM.
