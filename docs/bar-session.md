# Bar session lifecycle

## Installed manager supersedes the workspace launcher

After explicit user approval, release `20261025-local.3` was installed and the
running bar was handed off from the workspace trial to the installed manager.
Use `~/.local/bin/omabuntu start|stop|status|verify` for the installed instance.
The workspace `tools/bar_session.py` commands and run IDs below are retained as
historical trial evidence; they do not control the installed process. Session
lifetime remains unchanged. No autostart, service supervision, lock or login
change was activated. See [user installation](user-installation.md).

The user approved running the bar without automatic expiry on 2026-10-24.
Normal desktop components must no longer disappear because a diagnostic timer
elapsed. Timed runs remain available only for explicit disposable tests.

## Current behavior

- Explicit grant: `{"schema_version":1,"scope":"bar-session-v1","lifetime":"session"}`.
- No expiry timer is started for that scope, and no external timeout wraps it.
- The process is detached from the launching terminal; it is not a background
  promise made by the assistant or dependent on the command tool staying open.
- Missing/invalid grant or a changed grant still revokes the running instance.
- The original full-shell startup remains excluded; lifetime does not expand
  admitted capabilities or authorize additional services.
- Existing app shortcut remains session-local. No keybinding/config file was edited.
- No autostart, crash restart, system installation or login/session modification.
  Login persistence is a separate deployment change, not implied by session lifetime.

From the project root:

```sh
python3 tools/bar_session.py start --build-dir work/builds/<build-id>
python3 tools/bar_session.py status
python3 tools/bar_session.py stop
```

Start validates the reviewed source profile and pinned stage before launching.
A second start reports the existing matching process rather than duplicating
it. Any other Quickshell instance prevents start. Status/stop check the recorded
PID, owning UID, process start ticks and exact command with workspace paths;
they do not kill unrelated processes or use `uwsm stop`. Stop ends only this
bar/app-launcher process, leaving Hyprland and applications running.

Inputs and logs are staged in ignored private work/bar-session/<timestamp>/.
The current.json pointer records the process identity; it contains no copied
D-Bus address or other environment credentials. Prior timed trials are retained.
No active desktop config file needs a backup because none was edited. Rollback
of this run is the targeted stop command; the source change can be reverted
independently without changing the user's Hyprland configuration.

## Evidence and limitations

175 Python contracts pass. The explicit session grant, invalid/mixed grants
and timed boundaries pass the actual isolated policy probe in
work/clock-preview/20261024T152431.186764Z/report.json. The probe does not open
real session surfaces. Process tests never start/stop actual applications.

Live run: work/bar-session/20261024T152434.147770Z, PID 375385. The log contains
OMABUNTU_BAR_SESSION_NO_EXPIRY and Configuration Loaded. Exactly one process
and three 26px layers were observed. A second start was idempotent. The original
application shortcut remains registered; Hyprland configerrors is empty and
hyprland.lua retains its October 22 timestamp. The known portal app-ID warning
remains. No restart, logout or reboot was performed to test login persistence.

This is persistent operation **within the current login**, not a claim that the
bar is complete, installed, crash-proof, or automatically restored after login.
For a later autostart proposal: scope it only to the existing Hyprland session,
record/backup affected paths, preserve GNOME, and obtain approval before editing
config or enabling any user service. Super+Shift+Escape still ends the entire
uwsm Hyprland session and is not the bar-only stop command.
