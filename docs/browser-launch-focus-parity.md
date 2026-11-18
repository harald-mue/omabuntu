# Browser launch and existing-window focus: Omarchy comparison

## Finding

At the initial comparison, the inspected Omabuntu session did not use Omarchy's
original activation-focus policy. This was a concrete discrepancy consistent
with the reported symptom:
selecting an already running browser in the application grid can leave the visible
workspace unchanged. It is not proof of the exact browser/profile/protocol path,
because no real browser launch or activation was performed during this analysis.

The comparison is against Omarchy v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`, not an unpinned current branch.

## Original behavior

- `shell/plugins/dock/AppGrid.qml`, `launch()`: closes the grid and calls
  `dock.launchEntry(entry)`, or AppLibrary directly if no dock is attached.
- `shell/plugins/dock/Dock.qml`, `launchEntry()`: delegates to AppLibrary; this
  does not call the dock's separate existing-window `activate()` path.
- `shell/services/AppLibrary.qml`, `launch()`: ordinary graphical applications
  use `uwsm-app -- gtk-launch <desktop-id>.desktop`; terminal entries use the
  original TUI launcher. It does not unconditionally add `--new-window`, search
  for a browser window, or move a window to the current workspace.
- `default/hypr/looknfeel.lua` explicitly sets
  `misc.focus_on_activate = true`.
- `bin/omarchy-launch-browser` is a separate default-browser/URL entry point,
  not an implicit substitute for every browser selected in the app grid. It
  includes a guarded Chromium singleton-socket handoff and, when given a URL,
  calls `omarchy-hyprland-focus-app`. Neither helper is executed/imported by
  Omabuntu's application grid.

Thus the ordinary grid launch retains application-specific singleton/new-window
behavior, while the compositor is configured to honor eligible application focus
requests. This can reveal an existing window's workspace rather than create a
new window or bring it onto the launch workspace. It is not an unconditional
focus guarantee: application requests, valid activation context and per-window
rules/request suppression still matter.

## Omabuntu behavior

`config/shell/preview/AppLauncher.qml`, `launchSelected()`, begins launch feedback,
calls `DesktopEntry.execute()` and closes the grid. There is no existing-window
search/focus or workspace switch in that path. In the pinned Quickshell source
(`2b4501a282689792b62e94f3fb30d8f512324fe6`),
`src/core/desktopentry.cpp` forwards the parsed desktop-entry command and working
directory to `QuickshellGlobal::execDetached()`; it does not perform window focus.
The delayed launch notice is visual feedback, not a focus or recovery mechanism.

At the time of the analysis, the project's Hyprland templates did not set
`focus_on_activate`. The narrow
read-only runtime probe `hyprctl -j getoption misc:focus_on_activate` returned
`bool: false, set: false`. In reviewed Hyprland 0.57.0 commit
`0aa6745f705f2c4b0a5004eb019ef76e5bbdb426`, `ConfigValues.cpp` defaults it to
false. `CWindow::activate()` sets urgency but returns without focusing when this
policy/per-window override disallows focus. The XDG activation handler calls
that same function after validating a token; invalid tokens are a separate
possible failure, not established by this inspection.

The floating dock is different: `FloatingDock.qml`, `activate()`, picks an
existing matching window, restores a minimized window when applicable and
explicitly focuses it. The grid does not use that dock activation path. Original
Omarchy also distinguishes launching from dock activation.

## Suggested next step and limits

For original focus-policy fidelity, review adopting
`hl.config({ misc = { focus_on_activate = true } })` with a backup of the affected
configuration and the recorded previous runtime state. This is a global policy:
it permits eligible focus requests from other applications too, not only browser
launches initiated through the grid. It requires separate configuration/reload
approval and should first be tested with a disposable browser window on an
otherwise hidden workspace, including another monitor and an already focused
window. No profile data or tab/history inspection is required.

The `uwsm-app`/GTK desktop-launch chain remains a separate source-level difference;
changing the focus policy alone does not establish full launcher parity. If focus
still fails, diagnose activation-context/request handling before claiming a fix.
An app-grid-only launch-or-focus policy is another possible design, but is not
what the original app-grid source does. Forcing `--new-window` is a separate user
behavior choice, not original launch/focus parity.

During the initial analysis no browser was launched, focused or moved and no
desktop configuration, launcher, service, package, installed release or browser
profile was changed.

## Approved local follow-up

After explicit approval, plan 124 added the single `focus_on_activate = true`
setting to the existing personal Hyprland misc block and reloaded configuration.
The active option is now true/explicitly set, with no configuration errors.
Window identities/membership, floating/fullscreen states, occupied-workspace
layouts and output geometry matched the pre-change snapshot. The previous
autoreload option was restored. Exact original configuration bytes, permissions,
hash and runtime prestate are retained in a private backup/journal under ignored
`work/browser-focus-124/`.

No synthetic browser launch or workspace transition was used to claim acceptance.
The owner subsequently confirmed that the browser interaction works well and
requested installation/update integration. This is positive acceptance of that
interaction, not proof of every application's activation-token behavior. The
published v0.2.4 defaults remain unchanged.

## Installation and update integration (plan 125)

Published [v0.2.5](releases.md#v025-release-scope) enables
`misc.focus_on_activate = true` in both the generic session template and standalone
evaluation profile. Its verified bundle ships `config/hypr/focus-policy.lua`;
the normal published installer, setup release
workflow and application-menu updater reconcile it after a successful app
transaction. Already-current installer/update checks also reconcile the policy.
An older bundle without the artifact remains supported and is not retroactively
modified. Publication assets, signature, exact source and bundle checks passed;
all 1,297 tests pass. Publication does not install this helper or establish fresh
login/fresh-machine acceptance.

For an existing personal profile, `tools/focus_policy.py` adds only
`~/.config/hypr/omabuntu-focus.lua` and a marked
`require("omabuntu-focus")` at the end of `hyprland.lua`. It does **not** redeploy
the broader legacy managed settings. The first addition asks separately before
writing and, in the current Hyprland session, reloading configuration. Stopped
sessions stage the setting for the next login. Current owned settings require no
repeat question, write or reload. Noninteractive setup defers the separate desktop
grant and records its outcome instead of treating an app digest as approval.

This global policy allows eligible application focus requests, including existing
windows on hidden workspaces. It is not a grid-only browser search, a forced
`--new-window`, or a guarantee that every request has a valid activation token.
No browser profiles, launcher arguments, monitor rules or keybindings are changed.
Edited modules, ambiguous includes, configuration errors, stale approval inputs
and another session's compositor are refused/deferred, not overwritten.

The application switch and this configuration stage are separate transactions.
Declining or failing the latter does not roll back the installed application;
results expose `activation_focus` separately. Low-level manager/package operations
remain app-only. App rollback does not remove this independent desktop policy.
Private backups, original existence/modes, input hashes and runtime/autoreload
state are kept under `$XDG_STATE_HOME/omabuntu/focus-policy-transactions/`
(default `~/.local/state/omabuntu/`). Failure restores only matching transaction
content; concurrent edits require manual review. No live deployment of this new
helper was performed during implementation.

For explicit review/recovery from a matching source checkout:

```sh
python3 tools/focus_policy.py plan --review-out /absolute/private/focus-review.json
python3 tools/focus_policy.py apply --review /absolute/private/focus-review.json --approval DIGEST --apply
python3 tools/focus_policy.py recover --journal /absolute/private/transaction.json --apply
```

Plans contain private profile text: keep them outside Git. Recovery verifies the
journal, backup integrity, current content and original session identity before
restoring; do not edit a journal or discard concurrent changes to force recovery.
