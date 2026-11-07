# Analyze fresh/update session actions and missing wallpaper

## Goal and evidence

The user rejects hidden opt-in gates for ordinary logout/reboot/shutdown and
expects normal actions to work immediately, including repair on updates. The
new installation now reports no crash message but displays no wallpaper and
cannot set one. Compare current action dispatch/state/update paths, background
backend/result handling and original components against pinned Omarchy v4.5.0
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`, plus official Hyprpaper v0.8.5
(commit reported by the guest: `a8e93f4e60eabc432dde43449dfeb9a565c54da2`).

## Gaps and proposed analysis

Determine exactly where ordinary actions are gated and whether either public or
menu updates repair/default those settings. Separate supported session logout
from the hard-coded UWSM backend. Keep lock/idle/suspend/hibernate authentication/
recovery constraints separate from ordinary session ending. Inspect wallpaper
listing, default recording, daemon readiness, IPC/version behavior, response
validation and visible failure reporting; distinguish known code defects from
unobserved guest state after VM graphics changes.

## Safety and exclusions

Analysis and documentation/private references only in this plan. No session-
ending action, lock/suspend/hibernate, wallpaper change, service/reload/restart,
package/source installation, VM change, live preference migration, commit/push
or release publication. Do not probe the development host as a substitute for
the remote guest. Preserve unrelated pending release documentation. No new
upstream product import, replacement wallpaper renderer or broad user-session
termination. Any implementation must have reviewed rollback/default semantics;
normal actions should not need private helper commands to become usable.

## Tasks

- [x] Trace ordinary action gates, session backend and fresh/update behavior.
- [x] Review official version-appropriate Hyprpaper IPC/rendering and current backend.
- [x] Identify proven gaps, candidate causes and minimal read-only guest evidence.
- [x] Record the proposed repair boundaries and run tests/whitespace checks.

## Findings

### Ordinary session actions

`power_actions.perform()` refuses logout/reboot/shutdown on a fresh empty state.
The same refusal survives ordinary updates: neither the published install repair
sequence nor the application-only updater initializes these grants. The latter
explicitly refuses state-schema migration. A fake-runner reproduction confirms
all three refusals without executing any power command. Logout is independently
hard-coded to `uwsm stop`; the generic profile is not evidence of a UWSM-managed
login. Enabling flags alone is not a correct session-aware repair.

The requested target is ordinary actions available without an extra private
consent command, on fresh installs and after updates. Prefer a closed ordinary-
action policy in the shipped helper, rather than hidden mutable flags that can
become stale again: a helper update can then repair availability without writing
unrelated user state. Existing suspend/hibernate constraints remain separate;
no new sleep, lock or idle grants. Logout must validate the actual current
Hyprland session and use a supported backend; do not replace it with broad user
termination, killall, forced exit or inhibitor bypass. Ubuntu authorization still
applies to reboot/shutdown; removing an application gate is not a polkit grant.
This is a proposed implementation boundary, not an implemented or deployed fix.

### Wallpaper

1. **Proven empty-picker path:** `backgrounds()` includes private downloaded
   theme stills only if `current/theme.json` names a theme. `theme_backend.current()`
   returns no default. With no theme selected, an empty Pictures directory and
   no top-level Ubuntu background files, the picker is empty even when downloaded
   theme images exist. A temporary fixture reproduced zero listed rows alongside
   one available theme still. Ubuntu subdirectories are not scanned recursively.
2. **Proven diagnostic loss:** the backend discards hyprctl's error output and
   collapses monitor, connection, protocol, file and timeout failures into the
   same boolean. `set_background()` still returns `ok: true` for a recorded but
   unapplied choice; the picker normally stays open with a generic daemon note.
   A fake handshake failure reproduced the loss and inappropriate legacy preload
   fallback. This does not prove that this guest had a handshake failure.
3. **Login restore gap/candidate:** the generated hyprpaper configuration only
   disables the splash. A wallpaper must be supplied separately. Initial recording
   is part of deferred next-login session activation, not a universal application
   installation step. Shell start attempts restore once, without waiting for
   hyprpaper readiness; a failed restore does not block the shell and has no
   retry in that path. Starting/recovering the daemon later need not restore it.
   The menu updater deliberately does not restore wallpaper, to preserve unrelated
   state. These are code paths, not confirmation of the guest's login ordering.
4. **Not an established syntax/version mismatch:** official Hyprland 0.57.1
   `hyprctl/src/hyprpaper/Hyprpaper.cpp` accepts `wallpaper <monitor>,<path>`;
   it uses Hyprwire and returns a failing exit status for IPC errors. Official
   Hyprpaper 0.8.5 accepts that client protocol and supports `listactive`.
   Its IPC apply success is not proof of successful image rendering. Missing
   targets are valid when no wallpaper setting was supplied. Earlier EGL/GBM
   failures remain unclosed without current guest evidence; absence of a popup
   establishes neither daemon/socket readiness nor rendering success.

## Evidence and next diagnostic boundary

Private reports and source/license references: `work/session-wallpaper-108/`.
Existing original references for `omarchy-system`, `omarchy-theme-bg-set`, and
menu definitions were verified against the pinned Omarchy tree before comparison.
New official source collection checked BSD-3-Clause licenses before downloading
code and verified seven Hyprpaper and three Hyprland blobs against pinned Git
trees. No upstream code/assets were imported into product files. A stale assumed
Hyprland source path returned HTTP 404; the pinned tree established the actual
`hyprctl/src/` layout before verification continued.

Request bounded, read-only guest evidence from a terminal inside the affected
Hyprland login, not the TTY/development machine: hyprpaper unit state/restart
count, `hyprctl hyprpaper listactive` with exit status and current-boot recent
journal. Also distinguish an empty picker from a recorded-but-unapplied choice
or a picker that closes without rendering. These determine whether image/default
selection, login restore/daemon readiness, session socket, or renderer needs the
next repair. Do not run `set`, `restore`, daemon restarts or a power action as a
diagnostic. Implementation/deployment/publication remain separate from this
analysis. Existing v0.2.2 documentation edits are untouched.

Verification: all 1158 unittest tests pass; `git diff --check` passes. This is not
fresh-VM, graphical, logout or power acceptance.
