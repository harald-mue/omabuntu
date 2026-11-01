# Deliver the Hyprland-only hyprpaper condition through install.sh

## Goal and evidence

Plan 068 added the additive systemd user drop-in that starts Ubuntu's
`hyprpaper.service` only in a Hyprland session (and not in GNOME), deployed with
`tools/deploy_hyprpaper_condition.py` / `make hyprpaper-condition`. `install.sh`
does not yet offer that step, so a curl install never applies it and the GNOME
`hyprpaper` crash remains for public users.

Evidence: `tools/published_install.py` offers post-install desktop steps through
small `offer_*` functions (`offer_artwork`, `offer_session`); the drop-in tool
already enforces the reviewed template, `daemon-reload`-only behavior and a
backup path; the user requires `install.sh` to be the single entry point with no
internal subcommands.

## Shape

- Add two small functions to `tools/deploy_hyprpaper_condition.py`:
  - `review(home=None)` returns the resolved target, whether it exists, whether
    it already equals the reviewed template, and whether the base unit exists.
  - `deploy(home=None, *, systemctl_binary=SYSTEMCTL, dry_run=False)` writes or
    refreshes the drop-in (backing up a differing file) and runs the
    `daemon-reload` only. It never starts, stops or restarts the unit.
- Add `offer_hyprpaper_condition()` to `tools/published_install.py`, called once
  after `offer_artwork`:
  - skip silently when Ubuntu's `hyprpaper.service` is not installed or the
    drop-in is already current (never repeat the question);
  - otherwise one `[Y/n]` question; on yes, deploy with a backup and print that
    the change takes effect at the next login and that no service was touched;
    on no, print that hyprpaper keeps starting in every Wayland session.
- Tests: `review`/`deploy` unit tests in `tests/test_hyprpaper_condition.py` and
  an `offer_hyprpaper_condition` flow test; patch the new offer in the
  `published.main()` tests so the suite never writes to a real home.

## Safety and exclusions

- Additive and reversible: the drop-in is backed up and removed by
  `make hyprpaper-condition-remove`; the package-owned unit stays untouched.
- No service is started, stopped or restarted by the installer; only
  `daemon-reload` runs. An already running GNOME instance keeps running until it
  is stopped separately.
- The offer is skipped when it would change nothing, so the installer does not
  add a repeated prompt. It is not a substitute for the live Hyprland-login
  wallpaper check.
- No commit, push or release happens in this task.

## Tasks

- [x] Add `review`/`deploy` and their tests.
- [x] Wire the offer into `published_install.py` and update the flow tests.
- [x] Run the full suite; keep public delivery behind a later signed release.

## Result

`tools/deploy_hyprpaper_condition.py` exposes `review(home)` and
`deploy(home, *, systemctl_binary, dry_run)`; `tools/published_install.py` offers
`offer_hyprpaper_condition()` once after the artwork step, skips when the unit is
absent or the drop-in is current, and only reloads. `docs/installer.md` documents
the offer. Full suite: 1031 tests OK. The step reaches curl installs only after a
later signed release (v0.1.8); nothing was deployed or reloaded on a live
desktop in this task.
