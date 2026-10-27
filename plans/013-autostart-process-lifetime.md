# 013 — Preserve the shell after the login launcher exits

## Goal and evidence

Correct plan 012's systemd lifecycle mistake without adding crash supervision.
The login journal shows a successful manager start and the shell startup log
shows Configuration Loaded, but the oneshot unit becomes inactive immediately
and the shell disappears. `RemainAfterExit=no` allows systemd to tear down the
unit's control group after the manager exits. A new POSIX session does not
escape that control group. The previous template tests missed this property.
This is Ubuntu/systemd integration, not an Omarchy behavior change; no upstream
code or assets are imported and no upstream commit comparison is needed.

## Shape and constraints

Use `Type=oneshot` with `RemainAfterExit=yes`, preserving the existing target
wiring and default control-group cleanup at logout. Keep no Restart directive.
Active (exited) means the launcher succeeded, not that the shell is healthy;
`omabuntu status` remains the process-health check. Correct earlier misleading
documentation. Do not change Hyprland, authentication, packages, other services,
or installed release contents. No timeout or supervision is introduced.

The user approved backing up and replacing the host unit, daemon-reload and
starting the shell. Save the previous unit bytes and unit enablement/activity
before applying. Do not log out, exercise destructive rollback, or commit.
Rollback restores the saved unit and reloads systemd; restoring the broken
unit may stop the shell and needs separate approval.

## Tasks

- [x] Add a regression assertion and observe failure with the old template.
- [x] Correct template, plan 012 and user documentation; run the full suite
      (471 tests pass).
- [x] Save private previous-state evidence and back up the host unit.
- [x] Deploy the correction, reload and start the approved shell.
- [x] Verify the unit stays active and the same shell process survives after
      the launcher exits; inspect the startup log. Verified active (exited),
      Restart=no, owned process alive in the unit control group after a
      delayed recheck, and Configuration Loaded in the startup log.
- [x] Record results in WORKLOG.md. A fresh-login test remains pending.
