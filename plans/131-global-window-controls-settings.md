# Configure the original user-wide window-control mechanism

## Goal and explicit scope approval

The user explicitly approved the original button-layout mechanism affecting as
many applications as possible, including GNOME, with a Settings switch to show
and hide buttons. This supersedes the earlier GNOME-preservation requirement for
this one preference, not for unrelated settings. Implement repository code/tests
first; do not change the live key or deploy without a separate action.

## Evidence and gaps

Plans 074 and 080–089 record the earlier effective mechanism:
org.gnome.desktop.wm.preferences button-layout was changed from
appmenu:minimize,maximize,close to appmenu. The earlier GNOME side effect is now
an explicitly accepted user-wide scope. Omarchy behavior remains pinned to
v4.5.0 commit ac2690cd7be4f47e4a255f5e2e78d904d436b068; do not misrepresent
this authored preference switch as an upstream universal solution. Applications
that ignore the setting remain outside guaranteed coverage.

Plans 128–129 implemented a staged partial GTK3/Qt policy that does not solve
the user's Files case. Plan 130's unfinished launch integration was not deployed;
archive those experiments and restore their exact prestate instead of carrying
an unrelated launcher rewrite into this request.

## Shape

Replace the partial-policy backend with a closed show/hide/restore registry for
exactly the one GSettings key. Read actual live state for menu checks; include
explicit confirmation submenus warning that GNOME and other sessions are affected.
Before any write record the previous effective value and whether a dconf user
value existed; restore its value or absence with drift/integrity guards. Preserve
hyprbars and native application launch semantics. Provide bounded command probes,
read-only status/plan and explicit CLI mutation approval. No session-login toggle.

## Safety and exclusions

Back up all affected repository paths and archive abandoned experimental files
privately under ignored work/. No live GSettings/dconf writes, app/bar restarts,
launcher/binding edits, package installs, systemd/D-Bus environment exports,
compositor changes, deployment, commit or publication. The only proposed runtime
mutation is the explicitly disclosed user-wide button-layout key after a user
confirmation. Never promise custom application-drawn controls obey it. No native
module injection or whole-headerbar CSS removal.

## Tasks

- [x] Back up current work and restore/archive uninstalled launch experiments.
- [x] Implement live-key status, confirmation-gated menu actions and reversible transactions.
- [x] Replace partial-policy tests with isolated global-setting success/failure contracts.
- [x] Document user-wide behavior, recovery and application exceptions.
- [x] Verify source review hashes and run all unit tests without live activation.

## Outcome and limits

The backend now operates exclusively on the one explicit user-wide GSettings key;
show/hide/restore actions require confirmation rows labelled All Desktops. Checks
read actual state rather than the obsolete saved partial mode. Standard Show
sets all three buttons on the right; Restore reinstates a custom previous layout
or absence of a dconf user override. Backups, prepared journals, drift detection,
managed-lock refusal and command verification cover failure/recovery paths.

Legacy GNOME repair now recognizes a verified intentional hide and defers for
unfinished/corrupt global transactions instead of undoing the user's preference.
Source packaging already includes this helper. No application-launch changes
remain: exact pre-plan-130 sources were restored, its new experimental files
were archived privately, and its plan is explicitly superseded. Private source
prestates are retained under work/backups/plan-131-*.

All 1,330 unit tests pass, including 33 global-setting contracts; the authored
CommandMenu.qml hash was reviewed/updated and git diff --check passes. Real
read-only status and hide-plan probes also passed: the actual key is readable,
writable and consistent with dconf; no key write was performed. Documentation
and README explicitly disclose the user-wide GNOME scope.

This is a repository implementation, not deployment. The locally installed
plan-129 partial menu is unchanged until a separately reviewed local update and
bar restart. No live global preference mutation, application restart, launcher
change, compositor/service/package action, session transition, commit or
publication occurred. GNOME Files 50.2.2 and other native visual/interaction
acceptance remain unverified; applications may override/ignore the layout.
