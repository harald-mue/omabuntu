# Original Omarchy monitor-local workspaces

## Status and provenance

The repository implementation includes original allocation and presentation,
fresh-session opt-in, sealed release artifacts, keybinding-menu replay and a
reviewed existing-user migration/rollback path. Implementation is not activation:
a running installation still uses its previous model until a coordinated,
explicitly approved release/configuration deployment completes.

The original Omarchy v4.5.0 policy, binding reference and workspace widget are
pinned to `ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Source bytes are unchanged
under `vendor/omarchy/`; immutable identities are in
`upstream/monitor-workspaces.json` and the complete MIT notice is in
`licenses/Omarchy-MIT.txt`. No original bootstrap, installer, helper PATH,
provisioning, or full-shell takeover is involved.

## User model

Every monitor has local slots 1-10. Hyprland keeps globally unique real IDs in
blocks of ten: 1-10, 11-20, and so on. Each bar renders its own local numbers and
highlights that monitor's visible workspace, not global focus. The tenth slot is
shown as `0`; original numeric shortcuts address the physical 1-0 key row.
The first five slots are shown initially, followed by existing
higher slots and visiting workspaces from disconnected monitors.

| Binding | Action |
| --- | --- |
| Super + number | Select a slot on the focused monitor |
| Super + Shift + number | Move a window to that monitor's slot and follow |
| Super + Shift + Alt + number | Move a window without following |
| Super + Tab / Super + Shift + Tab | Next/previous workspace on that monitor |
| Super + Ctrl + Tab | Former workspace on that monitor |
| Super + Shift + Ctrl + direction | Move a window to the monitor in that direction |
| Super + Shift + Alt + direction | Move the entire workspace to that monitor |
| Ctrl + Alt + Tab / Ctrl + Alt + Shift + Tab | Focus next/previous monitor |

Click another slot to select it; click the visible slot to cycle tiling,
scrolling and floating through the existing Ubuntu backend. Clicking another
monitor's visible slot focuses that monitor before changing its layout.
Existing tiling defaults and saved choices are retained; this does not switch
all workspaces to floating. Directional monitor movement follows configured
screen geometry, which this feature never changes.

## Implementation

- `vendor/omarchy/default/hypr/monitor-workspaces.lua`: original identity/block
  allocation, adoption, unplug/merge/return, local focus and monitor moves.
- `vendor/omarchy/default/hypr/bindings/tiling.lua`: original binding reference.
- `tools/monitor_workspaces.py`: checked policy/widget derivation, no activation.
- `config/hypr/monitor-workspaces.lua`: generated standalone policy.
- `config/hypr/workspace-state.lua`: embedded saved-mode/minimized-tag adapter;
  atomic replacement and explicit errors for monitor/mode/history state writes.
- `config/hypr/monitor-workspace-bindings.lua`: reviewed opt-in binding module.
- `config/shell/preview/MonitorWorkspaces.qml`: original grid/buttons, slot and
  guest layout, adapted to Quickshell Lua IPC and the existing layout backend.
- `LiveStatus.qml` / `TrialDesktopState.qml`: retain the legacy adapter until the
  separately deployed `monitor-workspaces-policy` marker reads `monitor-local-v1`.
- `tools/workspace_migration.py`: conservative read-only mapping preview and exact
  replacement of the known legacy numeric-binding loop.
- `tools/workspace_deploy.py`: explicit review/apply/recover with private journal,
  full file backups, window identity/membership guards and inverse ID mapping.

Original workspace clicks use direct Quickshell Lua dispatch; the existing
BarRun shell-command allowlist is not widened. Backend modes, dock membership and
minimized targets use actual global IDs, never visible slot numbers. Renumbering
transfers saved modes, clears the old scrolling rule and updates minimized tags.

The keybinding scanner represents the four monitor factories inside its restricted
Lua environment, without loading allocation policy or executing compositor/file
operations. Only the known local session/binding modules are expanded. The menu
matches real Hyprland callback records and permits only the bounded source-derived
factory expressions which are present in current bindings.

## New managed profiles

The normal session planner supports explicit opt-in:

```sh
python3 tools/setup.py --session-config --monitor-local-workspaces
```

Review the plan and use the normal exact `--approve`/`--apply` gate if desired.
This path still requires Hyprland to be stopped, preserves unowned profiles and
edits, records ownership of both policy modules and the marker, and never starts
or reloads a desktop. The selected verified release must include all artifacts.
An existing personal profile is not automatically adopted. Nonempty global saved
layouts/allocation/history also require explicit migration rather than guessing
their monitor attribution in the stopped-session installer. Disabling an active
policy requires a separately reviewed configuration/saved-state migration, not
just deleting the marker or changing a flag.

`tools/package_user.py` verifies the original-source policy and generated mirrors,
includes both deployable Lua modules in the sealed manifest and records policy
provenance. Release updates reject incompatible global-only bundles while the
policy marker is active and reject switches during an unresolved workspace
transaction. Roll back the workspace configuration before selecting an older
incompatible application release.

## Existing personal profiles: read-only review

The existing-user migration currently targets the reviewed clean Hyprland 0.57.0
API and the exact known absolute-ID binding loop. Unknown/edited binding syntax,
existing policy modules/markers, saved destination collisions, unattributed saved
layouts, empty out-of-block workspaces and existing merged-history state block
initial migration instead of being guessed. The current desktop must be stable
across consecutive snapshots and share the shell's state directory. Live binding
metadata is included in the stale-review guard; extra or duplicate chords which
would conflict with any of the 45 original bindings block migration.

After preparing a verified local candidate, request a private review:

```sh
python3 tools/workspace_deploy.py plan \
  --config-dir "$HOME/.config/hypr" \
  --data-dir "$HOME/.local/share/omabuntu" \
  --state-dir "$HOME/.local/state/omabuntu" \
  --launcher "$HOME/.local/bin/omabuntu" \
  --bundle "$PWD/work/user-releases/<candidate>" \
  --review-out "$PWD/work/workspace-review/plan.json"
```

This writes only the explicitly requested private report. The default terminal
summary omits full personal configuration and window IDs. It prints the exact
approval digest; keep it with the private review. Reports/identity maps must not
be committed. A preview hash is not an atomic snapshot or permission to apply.

## Approved live application

First install the exact candidate through the existing reviewed release transaction;
never patch an immutable installed release. An ordinary bar restart before policy
migration still selects the legacy adapter, so it is safe to stage this separately.
A release switch is a separate approval from preparing a bundle.

Only with explicit configuration/reload approval:

```sh
python3 tools/workspace_deploy.py apply \
  --config-dir "$HOME/.config/hypr" \
  --data-dir "$HOME/.local/share/omabuntu" \
  --state-dir "$HOME/.local/state/omabuntu" \
  --launcher "$HOME/.local/bin/omabuntu" \
  --review "$PWD/work/workspace-review/plan.json" \
  --approval <printed-digest> --apply
```

Apply requires the exact installed manifest and a fresh match of configuration,
layouts, monitors, window membership and the reviewed runtime option. It records
and backs up every affected file before writes, under the private Omabuntu
`workspace-transactions/` directory. Only the owned shell is stopped. Automatic
configuration reload is temporarily suppressed while both modules and the exact
main-config replacement are staged; a manual reload performs original adoption.
The helper verifies window identity, output, mode and minimized membership, then
writes the marker, restores the previous autoreload option and restarts the shell
without wallpaper restoration. Normal shell lifetime remains session-based.

The migration renumbers occupied workspaces on their existing screens, preserving
their local slot where unambiguous. It does not redistribute applications, modify
monitor profiles, start services, install packages, or log out/reboot.

## Failure and rollback

Caught apply failures attempt conservative restoration of config, modes, state,
ID mappings and the prior shell-running choice. Every inverse membership is
validated before the first inverse renumber. Changes to window ownership, occupied
rollback destinations, layouts, configuration, permissions, backups, monitor
geometry or merged history can require manual recovery; they are never forcefully
overwritten or repaired by moving unrelated windows.

Explicit rollback or interrupted-operation recovery uses the original private
journal (replace its timestamp):

```sh
python3 tools/workspace_deploy.py recover \
  --config-dir "$HOME/.config/hypr" \
  --data-dir "$HOME/.local/share/omabuntu" \
  --state-dir "$HOME/.local/state/omabuntu" \
  --launcher "$HOME/.local/bin/omabuntu" \
  --journal "$HOME/.local/state/omabuntu/workspace-transactions/<timestamp>/transaction.json" \
  --apply
```

Recovery restores the recorded prestate rather than resuming an unfinished forward
migration. Unresolved journals block another workspace apply or release switch.
A rollback after further desktop use may correctly refuse reused IDs or changed
membership. These are guarded, recoverable operations, not a guarantee against
power loss, filesystem failure or arbitrary concurrent edits. After a failure,
consult the journal before another reload or release rollback. Original runtime
hotplug reconciliation still operates independently of the initial deployment
transaction; atomic state-file replacement is not a multi-step hotplug transaction.

## Verification and acceptance

Run `python3 -m unittest discover -s tests -v`. Real-Lua fixtures cover original
allocation, binding factories, local focus/moves, saved layouts, minimized tags,
connector changes, unplug/merge/return, full-block guests, collisions and inverse
membership guards. Fixture-only deployment tests cover stale reviews, partial
reloads, failed startup, restore/retry and refusal of concurrent edits. Installer
and release tests cover opt-in ownership and incompatible update prevention.

`tools/monitor_workspace_fixtures.py --runtime <explicit-runtime-prefix>` checks the
original widget offscreen in the existing bubblewrap sandbox: no real display,
IPC socket, bus or service. It checks local selection, original slot/guest layout,
click targets, geometry and ID refresh, rejecting warnings/errors. Its process
deadline is a disposable diagnostic limit, not a desktop component lifetime.

Official API comparison used Hyprland 0.57.0 commit
`0aa6745f705f2c4b0a5004eb019ef76e5bbdb426`, its dispatcher/config watcher sources,
and the official wiki dispatchers at revision
`ec1068fed41a68d9bace129de16aed785dd785ee`.

Successful unit/isolated checks and read-only inspection do not prove real hotplug,
fresh-login, interactive or visual acceptance. After approved deployment, verify
independent slots on two outputs with a disposable window first; test physical
docking only after basic navigation and recovery are accepted. Existing normal
component lifetimes, security policy, GNOME and corporate integration are unchanged.
