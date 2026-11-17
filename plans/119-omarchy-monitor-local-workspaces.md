# Adapt workspace management to Omarchy's monitor-local model

## Historical status

This plan records the initial candidate checkpoint. The remaining integration,
deployment transaction, installation and runtime verification were completed in
plan 120. Its unchecked tasks and deployment-readiness statements below describe
the earlier checkpoint, not the current installed implementation.

## Goal
Replace the global workspace simplification with original Omarchy monitor-local
slots across keyboard navigation, per-output bars, window/workspace moves,
saved layout modes and monitor unplug/return behavior. This request authorizes
repository preparation, not unreviewed live desktop changes.

## Evidence compared
- Omarchy v4.5.0 stable commit
  ac2690cd7be4f47e4a255f5e2e78d904d436b068:
  default/hypr/monitor-workspaces.lua, bindings/tiling.lua and the vendored
  shell/plugins/bar/widgets/Workspaces.qml.
- Plan 118's read-only live diagnosis and source comparison.
- config/hypr/minimal.lua, session-template.lua.in, omabuntu-managed.lua;
  tools/session_config.py and deploy_hypr_settings.py.
- LiveStatus.qml, WorkspaceSwitcher.qml, tools/workspace_modes.py,
  TrialDesktopState.qml and the sealed staging/provenance mechanism in
  tools/check_clock_preview.py.
- Before implementing compositor configuration, verify official documentation
  and API sources matching the diagnosed installed Hyprland version.

## Current gaps
The shell bar focuses global IDs 1-6 and highlights global focus, while generic
profiles bind absolute IDs 1-10. Original Omarchy uses physical-monitor identities,
persistent blocks of ten, local slots, explicit monitor moves and hotplug
reconciliation. Saved layouts currently use absolute workspace IDs. Floating
ownership, dock/minimize restoration and generated source mirrors must continue
to address the actual workspace, not the visible local slot. The running session's
binding metadata exposes opaque dispatcher handles; inspect the actual installed
configuration before proposing precise edits. Personal configuration lies outside
the workspace and requires explicit scoped inspection permission.

## Proposed shape
Prefer the original pinned monitor-workspaces module and widget structure, with
narrow reviewed Ubuntu namespace/state/dispatch adaptations, rather than another
simplified replacement. Verify upstream MIT provenance before any product import;
record immutable source hashes and preserve license notices. Separate compositor
policy from repository-only fixtures and deployment orchestration.

Use one policy for every entry point: slots 1-10 on the addressed monitor, actual
IDs in backend/state operations, monitor-local active highlighting and occupancy,
original first-five-plus-existing-slots presentation, and original directional
window/whole-workspace monitor moves. Retain existing layout choices; changing
numbering is not approval to switch every workspace to floating.

Prepare an explicit old-ID/new-ID migration preview from a fresh snapshot. Preserve
which screen currently owns each occupied workspace and preserve window membership
and layout; do not collapse or redistribute windows. Prefer retaining existing local
slot numbers where compatible with the reviewed original adoption algorithm. Explain
any renumbering before applying. Update all relevant saved-ID consumers consistently;
block ambiguous mappings rather than guessing. Initial migration and later hotplug
must not silently change a saved mode belonging to another workspace.

Keep generic fresh-session installation working and preserve its refusal to overwrite
unowned profiles or write them while Hyprland is running. Any separate existing-user
migration needs explicit scope, stale-state checks, backups and rollback rather than
bypassing that safety boundary. Do not patch sealed installed release files in place.

## Safety and approval gates
- No desktop edits, bindings, dispatches, reloads, shell restarts, session changes,
  installation, service changes or commits without explicit approval.
- Request permission to inspect only ~/.config/hypr and the Omabuntu-specific
  installed/state locations under ~/.local/share/omabuntu and
  ~/.local/state/omabuntu (or their explicit XDG equivalents).
- Keep raw installed configuration, inventories and identity maps under ignored
  private work/ only; do not print unrelated personal application data.
- Record existence, content hashes, permissions and backups of every affected path
  before applying. Separate repository completion from deployment and acceptance.
- Preserve monitor geometry/scaling, GNOME, login, corporate services, authentication,
  wallpaper and security policy. No timer lifetime, package additions or upstream
  provisioning. Do not reload automatically just by writing a live-watched config.

## Explicit exclusions
A full Omarchy shell takeover, global floating-default changes, cosmetic-only
renumbering, replacing monitor geometry, automatic window redistribution, autostart
or crash-supervision changes, lock/idle/suspend changes and publication.

## Tasks
- [x] Record the original model and repository integration points.
- [x] Obtain scoped permission and inspect installed configuration/state read-only.
- [x] Verify version-appropriate official compositor APIs and pinned module closure.
- [x] Review license/provenance and adapt original allocation/monitor-local widget.
- [ ] Integrate keyboard, original directional monitor moves and fresh-session path.
- [x] Implement candidate saved-mode/rule/minimized-tag transfer on ID changes;
      live migration and failure recovery remain part of the transaction gate.
- [ ] Implement preview, stale-state guards, backups and rollback for existing users.
- [x] Test identity stability, local focus/moves, occupied slots, unplug/replug,
      saved layout migration and per-operation failure recovery with isolated
      real-Lua fixtures; whole-deployment rollback testing remains pending.
- [x] Update generated mirrors, staging seals, provenance and English documentation.
- [x] Run python3 -m unittest discover -s tests -v.
- [ ] Present exact deployment diff and migration mapping for separate approval.
- [ ] After approval only, deploy and verify without claiming unobserved hotplug or
      visual acceptance; leave disruptive session transitions user-controlled.

## Implementation checkpoint

Scoped installed inspection confirmed the absolute-ID loop is separate from the
personal monitor-geometry profiles. The candidate keeps geometry untouched and
prepares an exact, read-only replacement proposal for that known loop. Raw config,
diff, snapshot and mapping stay private under ignored work/. No host file was
written and no dispatch, reload, shell restart, package installation or commit ran.

The unchanged pinned allocation policy and binding reference now have complete
MIT provenance. Generated Ubuntu policy and widget adapters retain the original
monitor identity allocation, reconciliation, local slot selection, guest handling
and original grid/button layout. The legacy bar remains the default unless a
separately approved policy marker and matching compositor deployment are present.
Original workspace clicks use Quickshell Lua dispatch, without widening BarRun.
Existing saved layouts/minimized tags are transferred on candidate ID changes.

Verification executes the real Lua module and binding factories with synthetic
compositor objects and tests an offscreen original widget in the existing isolated
runtime sandbox. This establishes candidate behavior, not real hotplug or visual
acceptance. A fresh read-only migration preview currently reports no mapping
blockers, but is not an atomic apply transaction.

The work is deliberately not labeled deployment-ready: the generic fresh-session
opt-in, installed release packaging, callback replay in the keybindings menu and
an existing-user journal/backup/inverse-mapping transaction still need completion.
Source per-operation state-write/renumber guards are not a complete rollback for
partial runtime or upstream merged-history failures. See
`docs/monitor-local-workspaces.md`. No further desktop approval is requested until
those safety gates and the final deployment review are ready.
