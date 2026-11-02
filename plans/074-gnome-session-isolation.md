# Keep GNOME sessions free of Omabuntu's Hyprland pieces

## Goal

Two regressions surfaced when the user logged into GNOME on 2026-11-02:

1. `omabuntu-shell.service` starts in **every** graphical session because it
   is `WantedBy=graphical-session.target` with only
   `ConditionEnvironment=WAYLAND_DISPLAY` — which GNOME satisfies too. In
   GNOME its `ExecStartPre` wait helper cannot find a Hyprland instance,
   fails ("Hyprland session environment is not ready"), and Ubuntu's
   `fumon` failure monitor turns that failed unit into a desktop popup.
   The shell unit must be skipped silently in GNOME, like hyprpaper
   (plan 068) and hyprsunset already are.
2. Windows in GNOME have **no minimize/maximize/close buttons**: on
   2026-10-25 the user-global GNOME key
   `org.gnome.desktop.wm.preferences button-layout` was changed to
   `appmenu` (recorded in `work/window-buttons/…/record.json`, previous
   value `appmenu:minimize,maximize,close`). That key is session-global:
   it strips the buttons in **every** CSD app of a GNOME session too.
   Omabuntu must not break GNOME; the Ubuntu default must be restored, and
   install.sh must offer the same repair.

## Evidence compared

- Live GNOME session (2026-11-02): `systemctl --user show-environment`
  shows `XDG_CURRENT_DESKTOP=GNOME`, `DESKTOP_SESSION=gnome`,
  `WAYLAND_DISPLAY=wayland-0` and **no** `HYPRLAND_INSTANCE_SIGNATURE`;
  `systemctl --user status omabuntu-shell.service` shows
  `failed (exit-code)` from 15:59:01 with the wait helper's message.
- Plan 068/069 evidence: Hyprland itself runs
  `systemctl --user import-environment … HYPRLAND_INSTANCE_SIGNATURE …`
  before starting `hyprland-session.target`, so the variable is present
  in the user manager before `graphical-session.target` activates units.
  The deployed hyprpaper drop-in proves the skip works: hyprpaper is
  `inactive (dead)` in this GNOME session, not failed. hyprsunset has
  the same `10-hyprland-only.conf` drop-in already.
- `gsettings get org.gnome.desktop.wm.preferences button-layout` returns
  `'appmenu'`; the record in
  `work/window-buttons/20261025T221259.243159390Z/record.json` holds the
  previous value `appmenu:minimize,maximize,close` and the restore
  command. No installer stage ever set this key; it was a manual change
  following the Omarchy pin (docs/hyprbars.md CSD section).
- `config/systemd/omabuntu-shell.service` template: only
  `ConditionEnvironment=WAYLAND_DISPLAY`. The unit is deployed by
  `tools/deploy_autostart.py` (plan 012) and rendered into the
  session-activation payload for generic profiles by
  `session_activation.render`; fixing the template covers both paths.
- `tools/published_install.py` post-install offers follow the
  `offer_*` pattern (e.g. `offer_hyprpaper_condition`, plan 069).

## Shape

- `config/systemd/omabuntu-shell.service`: add
  `ConditionEnvironment=HYPRLAND_INSTANCE_SIGNATURE` to `[Unit]` next to
  the existing `WAYLAND_DISPLAY` check (systemd ANDs them). Skipped in
  GNOME instead of failed; unchanged start in Hyprland.
- New `tools/repair_gnome_buttons.py`: review/apply/rollback restoring
  `org.gnome.desktop.wm.preferences button-layout` to the recorded
  Ubuntu default `appmenu:minimize,maximize,close`, writing a private
  state record (previous value, time, restore command) before changing
  it, refusing when the value is already the default, and rolling back
  from the record. No other GNOME key is touched.
- `tools/published_install.py`: `offer_gnome_buttons_repair()` as a
  post-install step, following `offer_hyprpaper_condition`: silent when
  nothing is to repair, explicit confirmation otherwise.
- Makefile targets `gnome-buttons`, `gnome-buttons-plan`,
  `gnome-buttons-rollback`; tests extend `tests/test_autostart_unit.py`
  (condition line) and add `tests/test_repair_gnome_buttons.py`.
- Docs: correct the CSD note in docs/hyprbars.md (the 2026-10-25
  appmenu change is reverted; tradeoff documented) and note the unit
  condition in docs where the autostart is described.
- Live repair on this machine (user-ordered): redeploy the unit with
  `deploy_autostart.py apply --replace` (backup + daemon-reload +
  enable), `systemctl --user reset-failed`, apply the button-layout
  revert with its record, and verify **in the running GNOME session**
  that `systemctl --user start omabuntu-shell.service` is skipped by the
  condition and that `gsettings get` shows the Ubuntu default.

## Accepted tradeoff

Restoring `button-layout` brings min/max/close buttons back into
Chrome/GTK CSD apps **inside Hyprland tiling** (the cosmetic reason for
the 2026-10-25 change). GNOME correctness wins; the buttons match stock
Ubuntu behaviour everywhere. Floating workspaces keep their server-side
hyprbars buttons; tiling windows close via Super+W as before.

## Safety and exclusions

- No systemd unit is started or stopped by the deployment tools;
  `reset-failed` only clears the failed marker, `daemon-reload` only
  reloads unit files. `enable` does not start the unit.
- The GNOME key change is one reviewed gsettings write with a recorded
  backup; no dconf dumps, no GNOME extension or schema changes.
- hyprpaper/hyprsunset drop-ins are already correct and untouched.
- Nothing else of the Hyprland session leaks: the activation files and
  the managed snippet are only read by Hyprland itself; GNOME never
  executes Lua config.
- No commit/push/release without separate approval; the plan is the
  source record, the live actions are backed up as described.

## Tasks

- [x] Add the Hyprland condition to the shell unit template.
- [x] Add `tools/repair_gnome_buttons.py` (review/apply/rollback, record).
      The repair fires only on the exact documented damage signature
      ('appmenu'); the stock schema default on Ubuntu 26.04 ('appmenu:close',
      upstream default — the Ubuntu vendor extension does not apply to the
      plain key) and any user layout stay untouched.
- [x] Wire `offer_gnome_buttons_repair()` into `published_install.py`.
- [x] Add Makefile targets (`gnome-buttons`, `-plan`, `-rollback`) and tests;
      run the full suite + clean-source. 1058 tests pass; clean-source passes.
      The published-flow tests patch the new offer like `offer_hyprpaper_condition`.
- [x] Update docs/hyprbars.md and the plan result.
- [x] Deploy the unit live (backup, daemon-reload), reset-failed, apply
      the button-layout revert with record.
- [x] Verify in the GNOME session: unit skipped on manual start
      ('ConditionEnvironment=HYPRLAND_INSTANCE_SIGNATURE was not met'),
      gsettings default restored, window buttons back.

## Result

The unit template and deployment carry
`ConditionEnvironment=HYPRLAND_INSTANCE_SIGNATURE` next to the existing
`WAYLAND_DISPLAY` check: GNOME (XDG_CURRENT_DESKTOP=GNOME, no
HYPRLAND_INSTANCE_SIGNATURE in the user-manager environment) skips the unit
silently instead of failing it; Ubuntu's failure monitor has no popup left.
Verified live in the GNOME session on 2026-11-02: a manual
`systemctl --user start omabuntu-shell.service` reports 'start condition
unmet … was not met' and stays inactive. Hyprland keeps importing the variable
before the session target activates (plan 068 evidence), so the autostart
there is unchanged.

`tools/repair_gnome_buttons.py` restores the recorded pre-change value
`appmenu:minimize,maximize,close` only where the exact 2026-10-25 damage
signature `appmenu` is present, records the previous value under
`~/.local/state/omabuntu/gnome-buttons/<stamp>/record.json` first, and rolls
back from that record. `make gnome-buttons` runs plan+apply;
`install.sh` offers the same repair after installation
(`offer_gnome_buttons_repair`, silent when nothing is damaged).

Honest note: the live button-layout revert first happened through a test-run
leak on 2026-11-02 15:13 — one published-flow test called the unpatched offer
against the real machine and applied exactly this reviewed repair, writing
the proper record. The published-flow tests are now patched like
`offer_hyprpaper_condition`, so no later run mutates the desktop. The
resulting state is identical to the ordered repair: value
`appmenu:minimize,maximize,close`, record present, rollback available.

Trade-off in Hyprland: CSD apps paint their min/max/close buttons again in
tiling (the cosmetic reason for the 2026-10-25 change). GNOME is stock-intact
again; floating workspaces keep the server-side hyprbars buttons.

Commit/push and a new signed release remain separate approvals; the
installer ships the fix through its bundle after that.