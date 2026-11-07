# Expose stable bar and dock appearance controls

## Goal and evidence

Implement the first recommendation from plan 093: original Appearance > Menu
Bar rows for visibility/background/clock/battery percentage and Appearance > Dock
rows for autohide/position. Preserve hierarchy, labels, icons and checked/visible
states from Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Relevant MIT menu/helper blobs were
verified in plan 093; the upstream notice remains preserved. Use original
components with narrow adapters, not replacement panels or upstream shell scripts.

## Gaps and shape

Bar visibility/background already have read-side support; clock and battery
settings are in-memory. Dock preferences/backend/context actions already exist.
Add a standard-library, narrowly allowlisted preference backend, private
per-change prestate/absence/mode journals, atomic writes, lock and conditional
rollback. Reads/guards must not create directories. Mutations require an
unambiguous Hyprland Wayland session and no GNOME desktop identifier. Preserve
unknown existing state fields and dock pins. A shared in-process adapter applies
successful writes to all bar outputs and dock state; failed requests remain
visible rather than silently closing the menu. Persist clock/battery choices
without breaking original widget bindings. Update sealed authored/derived
source hashes and bundle helper closure, not upstream vendor bytes.

## Safety and exclusions

Back up repository paths before edits. Implementation/tests only: no actual
user-state write, live deployment/restart/reload, service activation, package
install, commit or publication. Preserve the independently registered menu
shortcut when hiding the bar; visibility must not stop shell/menu/dock. No bar
positioning, compositor blur rules, window preferences, default-workspace changes,
branding, boot/Plymouth, lock/idle/suspend, GTK/global settings or arbitrary
commands/QML. No automatic state migration, autostart or lifetime timeout.
Every runtime mutation records the prior state before apply and supports exact
rollback only when the recorded after-state still matches.

## Tasks

- [x] Back up sources and implement validated preference transactions/rollback.
- [x] Add original menu rows, read-only guards and allowlisted dispatch.
- [x] Wire shared persisted bar/indicator state and dock synchronization.
- [x] Update source hashes, packaging closure, regression tests and documentation.
- [x] Run full unit suite, clean-source and contained UI checks where available.

## Result and acceptance boundary

Implemented 23 closed menu actions, persistent shared bar/clock/battery state,
dock synchronization and shared dock-writer locking. Exact-byte/mode/absence
receipts precede preference replacement; rollback refuses later modifications.
Documented scope and recovery in `docs/appearance-controls.md`.

Verification: 1105 unit tests passed, clean-source export/check passed, and
contained menu, clock and desktop-panel fixtures passed. The extended menu
fixture uses synthetic session identity in a sealed private home to exercise
queued shared-adapter writes, checked state and Hide/Show recovery. Native
layershell, keyboard recovery, real battery, multimonitor, GNOME and fresh-machine
acceptance remain unverified. An attempted published-workspace runtime was
correctly refused by the checker path boundary; subsequent fixtures used the
existing direct project build without weakening that boundary. Private logs,
prestate and failed-attempt evidence remain under ignored `work/`.

No real user preferences, running desktop, bindings, packages or services were
changed. No commit, deployment, restart, reload or publication was performed.
