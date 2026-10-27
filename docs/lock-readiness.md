# Screen-lock readiness: not activated

## Requirement and current evidence

The user requested a usable screen lock before daily-use deployment. Do not
confuse a visually fullscreen password panel, `loginctl lock-session`, a locked
hint or GNOME's own lock with an authenticated lock of this Hyprland session.
The existing GNOME session/login and corporate authentication must be preserved.

Initial read-only investigation on this target found (historical pre-install state):

- Hyprland runs under UWSM's `wayland-session@hyprland.desktop.target`.
- No `hyprlock` or `swaylock` executable is installed.
- dpkg reports hyprlock in residual-configuration state, not installed.
- The existing configured Hyprland PPA offers hyprlock
  `0.9.6-1ppa1~1resolute1`; the Ubuntu archive also offers `0.9.2-1build4`.
- APT simulation for the exact 0.9.6 candidate proposes one new package,
  no upgrades and no removals. No source was added and nothing was installed.
- The downloaded candidate package contains `/etc/pam.d/hyprlock`. A read-only
  comparison found that its bytes match the existing residual service file.
  There is no proposal to hand-edit PAM or replace the account's auth policy.
  Matching bytes do NOT prove authentication works or corporate acceptance.

Private evidence is under `work/lock-readiness/`,
`work/lock-package-review/` and `work/hyprlock-install-simulation.txt`.
Do not publish inventories, auth configuration or package snapshots.

## Standalone Hyprlock approved and installed; acceptance pending

The original Omarchy Quickshell lock is not admitted by the current selected
shell profile. Starting the full original shell to obtain its lock would also
activate unrelated security-sensitive services and is forbidden here. Importing
that original lock separately needs its own source/authentication/protocol review.

The user explicitly approved standalone packaged Hyprlock alongside the original
bar/panels and the exact one-package 0.9.6 transaction. This is an agreed
substitute for the original lock UI, not an original-source parity claim.
Package path pre-state, existing PAM service bytes, package version/residual
state and auto-mark state were recorded and verified before the attempt under
ignored `work/hyprlock-install/`. A noninteractive sudo attempt stopped before
APT because interactive authentication was required. No package was installed;
PAM bytes remained unchanged at that point. The user subsequently completed the
approved package command in their local terminal and reported success. Read-only
verification now confirms `/usr/bin/hyprlock`, upstream version v0.9.6 and dpkg
installed version `0.9.6-1ppa1~1resolute1`. The PAM service still matches its verified
pre-install backup byte-for-byte. It delegates its auth stack to the existing
`login` service. No password, authentication attempt or session lock was collected
or triggered by this verification. The installed bar continues running normally.

Reviewed the official v0.9.6 PAM implementation: it defaults to the `hyprlock`
service and uses `pam_authenticate`. The CLI offers no authentication-only or
safe parse-only mode; `--help` and `--version` exit without locking. Grace mode
is not a non-locking authentication test and must not be used as a workaround.
The active local Wayland session reports VT 2. This identifies the expected
return console for a user-approved TTY check, but does not prove recovery works.
An inactive getty unit alone is not evidence that a console login is unavailable
or that it has been tested. No getty service was started or enabled.

Never request credentials through an agent or chat. User config/binding changes
still require their own reviewed backup/approval. Package-managed PAM content
must not be silently changed or replaced if it differs from reviewed pre-state.

## Prepared supervised manual lock (not yet performed)

A static lock surface now ships inside the verified release as
`lock/hyprlock.conf`. It contains no `cmd[...]`, `onclick`, script, source or user
config inclusion and does not override the PAM service, so the package default
`hyprlock` authentication applies. Upstream's packaged sample config is
intentionally not used because it executes `date` and `hyprctl`.

`helpers/lock_session.py` and the installed manager's `lock` action provide one
explicit, single-shot lock. They require `--apply`, refuse root, a non-Hyprland or
mismatched session, an unexpected Hyprlock version/binary, an already running
Hyprlock, a symlinked or directive-bearing config, and always pass `--config`
explicitly (user config files are therefore not consulted). There is no idle
timer, daemon, restart, autostart, suspend or session-control call.

Preflight passed without locking on installed release `20261025-local.5`:
binary `/usr/bin/hyprlock`, reviewed v0.9.6, reviewed static config, display
`wayland-1`, status `planned-not-locked`. Tests: 282 pass
(`work/manual-lock-unit-tests.log`). Preflight is not an authentication verdict.

The supervised test must be started deliberately by the user in the live session:

```sh
~/.local/bin/omabuntu lock --apply
```

Test order: confirm the lock appears on every output, submit a deliberately wrong
password once (expect a clear failure without losing the session), then the
correct password (expect unlock), then confirm the bar still runs. Password entry
happens only inside Hyprlock; never in a terminal, agent, chat or log. If the
screen does not lock, do not retry blindly; report the private log path under
`~/.local/state/omabuntu/locks/`. If unlocking fails, recover through the TTY
console route already verified by the user and report the failure.

Still not performed or claimed: real lock/unlock acceptance, multi-output
verification, reconnect/DPMS behaviour, lock-screen input focus, corporate
policy approval, and any automatic lock. A shortcut or idle/lid policy remains a
separate reviewed change after this acceptance.

## Supervised manual lock accepted on 2026-10-25

The user started `~/.local/bin/omabuntu lock --apply` in the live Hyprland session
and reported that the lock appeared and that unlocking worked. The helper's
private log confirms the same event rather than only the user's summary:

- `ext_session_lock_manager_v1` was bound and `Locking session` logged.
- Lock surfaces were configured on all three outputs: eDP-1 1920x1200 at 150%
  fractional scale, DP-7 3440x1440 and DP-9 1920x1080.
- The PAM prompt was `Password: `, followed by `auth: authenticated for hyprlock`
  and `Unlocking session` / `Unlocked, exiting!`.
- Hyprlock exited with status 0, no Hyprlock process remained, and the installed
  bar (PID 880277) was still running.

Accepted: explicit manual lock, correct-password unlock, all three outputs, and a
clean locker exit with the bar surviving. The user's credentials were entered only
in Hyprlock; nothing was captured in a log beyond the PAM prompt text.

Not yet accepted: the wrong-password path (no failed attempt is recorded), long
idle before locking, output hotplug while locked, DPMS/suspend during lock,
fingerprint, automatic locking, and corporate-policy sign-off for the
delegated `login` PAM stack. These stay excluded or pending; they are not
implied by the successful round trip.

## Manual shortcut

On 2026-10-27 the user approved one chord. `SUPER+CTRL+L` in the live
Hyprland configuration runs `~/.local/bin/omabuntu lock --apply` and nothing
else. The previous file was copied under ignored `work/lock-shortcut/` before
the edit. After reload the compositor reports the chord once, with description
`Lock system`, and reports no config error. The keybindings menu lists that
row and still refuses to launch it, the same way it treats logout.

The chord was not pressed as part of the first bind. The earlier supervised
lock remains the acceptance record for actually locking. Idle, lid, screen-off
and suspend are still not bound.

On the later same-day use, the chord still fired on key press. The first lock
unlocked. Its log recorded two stray key releases, which is the held chord
reaching Hyprlock. The second lock reached the password prompt and then
recorded no authentication and no exit. It stayed the session lock until the
compositor process was replaced about an hour later and the machine was
power-cycled. No kernel GPU hang is in that boot's log. The bind now uses
Hyprland 0.56.2 `release = true`, so the helper starts only after Super, Ctrl
and L have been released. That reload is not a new lock test. If a lock ever
stops taking input, switch to the text console with Ctrl+Alt+F3 instead of
powering the machine off. Do not start a second Hyprlock while one is running.

## Remaining gates after the supervised test

1. Record the actual lock/unlock result, including every output and the wrong
   password path. Do not infer success from one monitor or from the process
   having started.
2. Agree on a corporate-policy check for the `login` PAM stack if the account
   uses a company-managed authentication agent; a local password success is not
   that approval.
3. Done for the manual chord above. A bar action is still a separate change.
4. Automatic idle, screen-off, lid and suspend integration stay separate
   reviewed changes with authentication and recovery re-verified.

The project provides no idle timer, session-lock object, lock service,
autostart or suspend command. The only lock launcher is the explicit
`lock --apply` action, now also bound to `SUPER+CTRL+L`. Use
`python3 tools/lock_readiness.py` for bounded read-only collection; its report
always marks authentication/recovery as unverified and activation as disallowed.
Successful prerequisite collection is never a security verdict.
