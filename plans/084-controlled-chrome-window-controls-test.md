# Controlled Chrome restart for process-local window-control acceptance

> **Closed after plan 085 rollback:** the controlled browser test failed; no
> module integration was deployed, and the earlier browser exception is removed.

## Goal and evidence

The user explicitly approved closing/restarting Chrome with the already built
GTK3 module after the normal browser restart did not load it. Continue
plan 083 using the exact source/artifact hashes and current Chrome-owned window
identity. Baseline remains Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068` on Hyprland 0.57.0.

## Shape and current gap

The browser has not been started with GTK_MODULES; a normal restart cannot test
the candidate. Save private filtered process/window prestate and build evidence,
then request close only for windows owned by the verified Chrome process. Wait
for orderly exit; if it remains without windows, a normal SIGTERM is allowed for
that exact verified process, never forced kill. Relaunch the standard Chrome
launcher with its existing profile and one-shot restore-last-session, preserving
existing GTK modules and adding only the reviewed module to the child environment.
Verify a fresh Chrome window, artifact loading and session guard environment.
Keep/return it to the recorded workspace and output if necessary. Do not claim
button visibility or behavior without user visual confirmation.

## Safety and exclusions

Do not inspect or copy browser profiles, credentials, page titles or URLs. The
browser itself handles profile/session persistence; restoring tabs is best effort,
not a backup guarantee. Stop if ownership is ambiguous or a close/save prompt
requires user input. No force kill, profile replacement, sandbox weakening,
Edge restart, global GNOME/GTK write, plugin/compositor reload, app deployment,
autostart, persistent launch integration, hyprbars matcher restoration or commit.
Use no process lifetime limit; readiness waits are bounded diagnostics only.
Keep previous module/variant-1 state available until visual acceptance.

## Tasks

- [x] Verify and record exact Chrome/window/module prestate privately.
- [x] Close the verified Chrome process and relaunch with the scoped module.
- [x] Verify fresh process, module loading, workspace and unchanged GNOME state.
- [ ] Record result and request user visual acceptance before further deployment.

## Result: browser-specific blocker, no further deployment

The approved restart completed through the normal Chrome launcher with the
existing profile and one-shot session restoration. The original owned process
exited, a fresh Chrome window appeared, and it was returned to the recorded
workspace/output. The reviewed module was not present in the new process maps.
Shared GNOME layout and compositor configuration-error checks were unchanged.
No Edge/shell/plugin/compositor restart or persistent integration was performed.
Private prestate, launch log and result are under ignored
`work/window-controls-chrome-test/`.

The exact installed Chromium source tag 156.0.8078.79 contains a module-settings
interceptor and explicitly unsets GTK_MODULES before GTK initialization in
`ui/gtk/gtk_ui.cc`. The earlier main-branch initialization review did not contain
that version-specific filtering. GTK-only tests therefore could not establish
Chrome compatibility. Process environment/cmdline memory was zeroed after launch,
so procfs environment absence alone was not treated as evidence of launch loss.

The module is rejected for browser deployment. No attempt will bypass filtering
or weaken browser policy/sandboxing. User visual acceptance was not requested
because the module-load prerequisite failed; that checkbox remains incomplete.
Chrome is running normally, variant 1 remains active, and
`docs/process-local-window-controls.md` marks the research as blocked. The actual
requested variant-2 behavior is not implemented. Further work needs a separately
supported mechanism, not repeated restarts or persistent installation of this
candidate.
