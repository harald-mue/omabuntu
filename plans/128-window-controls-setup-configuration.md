# Implement central partial window-control configuration

## Goal and agreed scope

Implement Super+Space > Setup > Window Controls after explicit agreement to
partial coverage. Provide Application Default, Hide Supported Application
Controls, and guarded restoration. Keep GNOME and existing hyprbars untouched.
Repository implementation/tests only: no installation or live activation.
Existing launchers/session integration remain separate approval gates.

## Evidence and gaps

Use plan 127 and docs/toolkit-wide-window-controls.md: GTK3 GTK_CSD=0 applies
only to default titlebars; Qt v6.10.2 QT_WAYLAND_DISABLE_WINDOWDECORATION=1
suppresses standard Qt Wayland decorations, not custom content. Omarchy source
baseline is v4.5.0 commit ac2690cd7be4f47e4a255f5e2e78d904d436b068.
Current Setup has Defaults only; menu actions are registry-controlled. There is
no supported universal mechanism or existing approved launcher integration.

## Shape

Add a bounded Python preference backend with read-only status/launch planning,
closed policy choices, atomic writes, exact pre-state transactions, drift-safe
rollback, interruption refusal/recovery, and Python-evaluated menu predicates.
Reuse existing bounded preference-file primitives, not global settings. Supply
an explicit --apply command wrapper for separately approved launches; apply only
the two reviewed environment overrides to that process. Preserve argv and other
environment variables; never export to systemd/D-Bus or use a shell. Clearly
report staged policy, not actual window coverage. Existing app launchers remain
unchanged. Bundle the backend with the normal release helpers.

## Safety and exclusions

Back up changed repository paths privately before edits. No GSettings, GTK CSS,
browser profiles, desktop launcher files, live environment/configuration,
services, packages, compositor/plugin reloads, application restarts, session
transitions, deployment or commit. No timers for approved launch lifetimes.
No custom-header, Electron, X11, dialog or universal acceptance claims.
No native GTK module/injection or imported upstream implementation.

## Tasks

- [x] Back up affected repository paths and record their previous state.
- [x] Implement bounded policy persistence, rollback/recovery and opt-in launch API.
- [x] Add closed-registry Setup entries, truthful feedback and bundle inclusion.
- [x] Add isolated success/failure, session, integrity and integration tests.
- [x] Document staged versus active behavior and explicit invocation/recovery.
- [x] Run all unit tests and review diffs; do not deploy or commit.

## Outcome and verification

Added tools/window_controls.py, tests/test_window_controls.py and
docs/window-controls.md. The Setup submenu uses a closed action registry and
Python predicates; changes save policy only. A persistent scope notice and wider
submenu prevent successful selection being mistaken for live activation. The
explicit run --apply wrapper supplies only the reviewed child-process overrides,
without shell expansion or a lifetime timer. Existing launchers stay unchanged.

Persistence reuses bounded, owned, symlink-rejecting preference-file primitives;
transactions record exact bytes/modes or absence and refuse unrelated drift.
Interrupted writes block new changes/launches until explicit restoration. Release
packaging includes the backend. The authored CommandMenu.qml review hash was
updated after reviewing its feedback/geometry changes; upstream source pins and
admission checks were not weakened. The initial full-suite run correctly rejected
the changed authored file until that review record was updated.

Private pre-state backups/manifests are retained under work/backups/plan-128-*.
The final full suite passes all 1,323 tests, including 26 new isolated cases
(8.704 seconds). Python syntax, documentation local links, whitespace and tracked
file diffs were checked. Native Qt/GTK rendering, real application interaction,
GNOME-session isolation acceptance and release-build execution were not run.
No desktop installation/activation, launcher edits, settings writes, package or
service actions, application restarts, deployment or commit were performed.
