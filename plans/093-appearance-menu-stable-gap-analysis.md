# Assess Omarchy 4.5 stable Appearance menu additions

## Goal and evidence

Identify useful Omarchy Appearance entries missing from Omabuntu and recommend
bounded Ubuntu-native adaptations. Compare the original menu and action helpers
at v4.5.0 stable commit `ac2690cd7be4f47e4a255f5e2e78d904d436b068` with
Omabuntu's menu registry, frame/dock, workspace persistence, theme and state
backends. Verify recorded source bytes against the pinned Git tree. Distinguish
an existing backend from a missing menu route and from a new integration.

## Gaps and shape

Omabuntu currently exposes Theme, Background and Font only. Review upstream
Menu Bar, Windows, Branding, Dock, Default Workspace Layout, Animations and
Unlock entries. Rank practical utility, implementation size, fidelity and
GNOME/session-safety boundaries. Preserve original menu hierarchy/components;
do not propose replacement panels. Record excluded features and clarify that
Unlock is a boot/unlock appearance path, not browser/window controls.

## Safety and exclusions

Read-only repository/public-source analysis plus this plan/report. No upstream
helper execution, import, package installation, desktop setting write, reload,
window action, service change, session transition, commit or publication. Boot,
Plymouth, authentication, lock/idle/suspend integration remain excluded. A menu
entry is not authorization to run unreviewed Omarchy scripts. Future Hyprland
configuration changes require official version-specific review and backups.

## Tasks

- [x] Verify stable menu/helper evidence and enumerate missing entry groups.
- [x] Compare current project backends and classify reuse versus new work.
- [x] Document priorities, exclusions and approval/acceptance boundaries.
- [x] Run full tests and diff checks after repository documentation changes.

## Outcome

`docs/appearance-menu-assessment.md` records all additional stable groups and
priorities. Sixteen original menu/helper/toggle blobs match the pinned stable
tree. Dock preferences are already implemented; bar visibility/background have
read-side support, while clock/battery settings need persistence and menu wiring.
Window preferences and default-workspace semantics require bounded new backends.
The top-only bar frame makes position controls substantial fidelity work.
Upstream glass changes terminal/GTK files; Unlock invokes Plymouth. These are
not safe menu-only imports or permission to modify GNOME/boot configuration.

All 1086 unit tests and `git diff --check` pass. Private source-verification
records and test log remain in ignored `work/research/appearance-093/`.
No product code, live settings, source imports, commit or publication changed.
