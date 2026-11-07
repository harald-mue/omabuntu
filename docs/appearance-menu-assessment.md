# Omarchy 4.5 stable Appearance menu assessment

## Evidence and current gap

Compared the original menu at Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`,
`default/omarchy/omarchy-menu.jsonc`, with
`config/shell/omabuntu-menu.jsonc`. The current Omabuntu menu exposes Theme,
Background and Font; it deliberately does not expose all upstream commands.
The component rebase in 0.2.0 was not full shell/configuration integration.

Twelve relevant original menu/helper files were checked against recorded stable
Git blob IDs. Additional toggle definitions were inspected to distinguish a
menu label from its actual effects. Raw verification evidence remains private
under ignored `work/research/appearance-093/`. This is a source assessment, not
native acceptance, an upstream script import or authority to run those scripts.

## Recommendation by original entry group

| Original entry | Existing Omabuntu support and gap | Recommendation |
| --- | --- | --- |
| Theme / Background / Font | Already exposed through reviewed Ubuntu backends. | Keep; no duplicate replacement UI. |
| Menu Bar: Hide / Show | `TrialPanel.qml` already watches the Omabuntu bar-off flag and releases its reserved screen space when hidden. No Appearance action is registered. | High value, small integration: add an owned, backed-up state writer and original menu rows. Preserve a tested keyboard route to reopen the menu/show the bar. |
| Menu Bar: Background | The bar reads opaque/glassy/none from its Omabuntu `bar.json`. No reviewed menu writer is wired. Its glassy look does not itself manage compositor blur. | High value, small-to-medium integration. Expose original choices, without claiming new blur or copying upstream layer-rule mutations. |
| Menu Bar: Indicators / Clock | Original format cycling exists. `TrialPanel.qml` shares `clockSettings` between outputs but currently changes it in memory; its `updateEntryInline` does not implement upstream shell.json persistence. | High value: expose original horizontal format presets and add narrowly scoped persistent state. Do not assume the upstream widget's persistence comment describes this adapted host. |
| Menu Bar: Indicators / Battery % | The power controller and right-click toggle exist, but `showPercentage` is currently an in-memory property. | Useful on machines with a battery. Add persistent preference and show the row only with an applicable battery; no power-profile or system-policy change. |
| Menu Bar: Position | The admitted frame is top-only/horizontal, with popup geometry, anchors and exclusive-zone assumptions. | Defer as a substantial original-frame port, not a menu-only addition. Bottom and vertical placement require multi-output/scale/focus testing; do not advertise unsupported positions. |
| Windows: Gaps | No reviewed Appearance toggle backend. Upstream loads a persistent Hyprland toggle. | High utility and bounded scope, but a new version-reviewed, reversible Hyprland preference backend is required. Preserve prior gaps and per-workspace overrides. |
| Windows: Corners | Upstream offers Theme, Sharp and Rounded via theme-precedence toggle files. No equivalent menu/backend is currently admitted. | Sensible companion to gaps. Theme must remove the override and recover the underlying theme, not restore a guessed numeric default. |
| Windows: Opacity | Upstream's opaque mode targets tagged transparent windows, not every application. Transparent removes mode overrides; it does not mean making all windows translucent. Glassy also edits terminal theme files and shared GTK CSS and restarts affected components. | Defer the full feature. A compositor-only subset would be an explicitly documented Ubuntu adaptation, not equivalent upstream Glassy. Do not write shared GTK files that also affect GNOME. |
| Windows: 1-Window Ratio | Upstream sets a 1:1 single-window layout ratio to avoid extremely wide lone windows. Current workspace support does not provide this preference. | Useful optional feature for wide displays. Review Hyprland 0.57 behavior and layout coverage; preserve user layout choices and do not describe it as a floating-window size control. |
| Workspace Layout | Upstream menu changes the default for otherwise unassigned/empty workspaces. Omabuntu currently persists per-workspace modes and uses dwindle as fallback. | High utility, medium integration. Reuse the existing switcher/reconciliation, but add an explicit default state model rather than cycling the current workspace. Protect occupied workspaces and minimized-window origins. |
| Animations On / Off | Upstream's no-animations toggle disables animations, blur and shadows together. No equivalent Appearance backend is admitted. | Useful accessibility/VM/performance option, with its full effects explained. Restoring On should remove the override and recover previous/theme values, not blindly enable all three. Shell/QML animations are separate and are not automatically covered. |
| Branding: About | Original About surface/branding pipeline is outside the admitted shell. | Low current utility; defer rather than add a substitute panel for a logo/text editor. |
| Branding: Screensaver | Screensaver integration is not admitted; idle/lock/authentication boundaries apply. | Exclude from this feature batch. Branding must not become implicit screensaver/idle activation. |
| Unlock | The menu invokes the Plymouth switcher/reset/theme path through a terminal. It is boot/unlock presentation, not application decorations or an ordinary Hyprland appearance option. | Excluded: boot/system changes are outside this project's allowed scope. |
| Dock: Auto-hide / Always-on / Position | Existing `dock_state.py`, `DockState.qml` and `DockWindow.qml` support these choices, including all four positions. The dock already has corresponding context-menu actions. | Best low-risk parity addition: wire the existing reviewed backend into the original Appearance > Dock hierarchy. Keep upstream floating-workspace visibility and existing application/session state. |

## Proposed implementation order

1. **Menu Bar and Dock convenience:** bar show/hide, existing background looks,
   horizontal clock formats, battery percentage when applicable, dock position
   and autohide. This mostly exposes already present behavior, but bar/indicator
   writes still need validated, backed-up persistence and explicit rollback.
2. **Bounded Hyprland appearance preferences:** gaps, corners, single-window
   ratio and the documented animation/blur/shadow override. Add one consistent,
   version-reviewed state/override mechanism instead of unrelated shell scripts.
3. **Default Workspace Layout:** extend the established workspace model with
   explicit default/override semantics and busy/minimized-workspace protection.
4. **Larger fidelity work, separately scoped:** original bar positioning/frame
   integration and app-specific transparency/Glass. No replacement panels or
   global GNOME/GTK writes as shortcuts.

Menu hierarchy, labels, checked states and applicable visibility conditions
should follow the original source. Keep the existing action allowlist; do not
add arbitrary command execution, expose an unreviewed upstream bin directory
through PATH or import upstream shell.json wholesale.

## State, recovery and acceptance boundaries

Every writable preference needs a recorded original value or absence, safe
owned-path checks, private backup and explicit rollback. Session lifetime must
remain independent of autostart or crash supervision. Bar hiding must not stop
the shell, dock, menu route or unrelated components.

Hyprland configuration work must first consult official 0.57.0 documentation
and validate theme/rule precedence, reload semantics and recovery. A property
shown in an upstream toggle is not proof it can be safely toggled live in this
Ubuntu adaptation. No compositor reload is authorized by this assessment.

Test applicable checked/hidden menu rows, persistence across restart/login,
mixed workspace modes, minimized windows, multiple outputs/scales and restoration
of user values. Keep GNOME unchanged. Native visual and interaction acceptance
is separate from source checks/unit tests. No desktop settings were changed by
this analysis, and no feature in this recommendation is claimed implemented.
