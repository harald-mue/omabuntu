# Start hyprpaper only in a Hyprland session

## Goal and evidence

On the clean VM (Ubuntu 26.04), `hyprpaper` crashes in the GNOME session with
`DRM_IOCTL_MODE_CREATE_DUMB: Permission denied` and a GBM/SIGSEGV. The cause is
not the GPU: Ubuntu ships `/usr/lib/systemd/user/hyprpaper.service` with only
`ConditionEnvironment=WAYLAND_DISPLAY`, `PartOf/Requires/After=graphical-session.target`
and `WantedBy=graphical-session.target`, so the unit starts in **every** Wayland
session, including GNOME. hyprpaper is a Hyprland tool; without a compositor
socket it falls back to standalone KMS/DRM output and cannot get the DRM master
held by GNOME.

Evidence:
- `systemctl --user cat hyprpaper.service` (Ubuntu 26.04, hyprpaper
  `0.8.4-1ppa3~resolute1`) shows only `ConditionEnvironment=WAYLAND_DISPLAY`.
- The journal shows the EGL/KMS/GBM failure followed by `code=dumped,
  status=11/SEGV` and an unforced `Restart=on-failure` loop.
- `strings /usr/bin/Hyprland` shows the compositor itself runs
  `systemctl --user import-environment DISPLAY WAYLAND_DISPLAY
  HYPRLAND_INSTANCE_SIGNATURE XDG_CURRENT_DESKTOP ...` and then
  `systemctl --user start hyprland-session.target`, so both the plain
  (`/usr/bin/start-hyprland`) and the uwsm-managed session make
  `HYPRLAND_INSTANCE_SIGNATURE` visible to the user manager. This matches the
  existing note in [user-installation.md](../docs/user-installation.md) that the
  uwsm session imports the same variable.

This is separate from the update-news popup, which is a real
GPU/software-rendering crash on this VM and is handled by plan 067. hyprpaper
should also not run under GNOME on hardware with a GPU: it still cannot be the
DRM master there.

## Shape

- Ship a reviewed systemd user drop-in template
  `config/systemd/hyprpaper-condition.conf` with only:
  ```
  [Unit]
  ConditionEnvironment=HYPRLAND_INSTANCE_SIGNATURE
  ```
  systemd ANDs conditions of the same type across the unit and its drop-ins, so
  the merged `hyprpaper.service` starts only when both `WAYLAND_DISPLAY` and
  `HYPRLAND_INSTANCE_SIGNATURE` are present: a Hyprland session, never GNOME.
- Deploy it with a new read-only-by-default tool
  `tools/deploy_hyprpaper_condition.py` (`plan` / `apply` / `remove`, standard
  library only), mirroring `tools/deploy_autostart.py`: target
  `~/.config/systemd/user/hyprpaper.service.d/omabuntu.conf`, symlink/traversal
  rejection, backup of any existing file, `--replace` for a differing target, an
  inactive-owner receipt, and a `daemon-reload` only on apply/remove.
- Regression test `tests/test_hyprpaper_condition.py` for the reviewed template
  contents, the read-only plan, the write/backup/refuse paths and the removal.
- Document the change and the exact manual equivalent in
  [user-installation.md](../docs/user-installation.md).

## Safety and exclusions

- The Ubuntu unit stays untouched and enabled: no `mask`, no `disable`, no edit
  of the package-owned file. The drop-in is additive and removed by the tool.
- The tool never starts, stops or restarts `hyprpaper.service` by itself; a
  `daemon-reload` and the one-time stop of the currently running GNOME instance
  are separate, explicitly approved actions.
- The condition is not a supervision or lifetime limit. It only mirrors the
  session type; Hyprland behavior on real hardware is unchanged.
- Residual risk to verify live: if a Hyprland session ever starts
  `graphical-session.target` before the compositor imports
  `HYPRLAND_INSTANCE_SIGNATURE`, the condition would skip hyprpaper there too.
  The user must confirm the wallpaper appears in a real Hyprland login before
  this is called accepted. A `ConditionPathExistsGlob=%t/hypr/*/.socket.sock`
  fallback is the documented alternative if the env condition proves unreliable.
- No session transition, service reload, commit or release happens in this task.

## Tasks

- [x] Write the drop-in template and the deploy/remove tool.
- [x] Add the regression test and the documentation.
- [ ] Run the full test suite, then request a separate live
      `daemon-reload`/login check on the target before claiming success.

## Result

`config/systemd/hyprpaper-condition.conf`, `tools/deploy_hyprpaper_condition.py`,
`tests/test_hyprpaper_condition.py`, the `make hyprpaper-condition*` targets and
the `docs/user-installation.md` section are in place. 10 new tests pass. Nothing
was deployed to a live desktop and no service was reloaded, started or stopped.
Public delivery still needs a follow-up: `install.sh` does not yet offer this
step, so a future release and a reviewed single-entry integration are required
before a curl-based install can apply it. The live Hyprland-login wallpaper check
remains outstanding.
