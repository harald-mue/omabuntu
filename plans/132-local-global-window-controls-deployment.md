# Install the global Window Controls setting locally

## Goal and evidence

Apply the user's explicit request to install plan 131 locally for testing,
including an owned-bar-only restart as disclosed immediately before approval.
Compare verified selected/previous release manifests with the reviewed menu,
backend and authored QML hashes. Omarchy source baseline remains v4.5.0 commit
ac2690cd7be4f47e4a255f5e2e78d904d436b068; no upstream imports are involved.

## Gap and shape

The current local plan-129 menu uses the obsolete process-only policy. Prepare
an immutable derivative with exactly CommandMenu.qml, the menu JSONC,
window_controls.py and local provenance changed. menu_model.py and the native
manager/runtime already match and need no replacement. The separate historical
repair source change is not a runtime helper in this bundle and remains source
for future installer builds. Use the standard update journal and rollback path,
retain the prior release, and disable wallpaper restoration for start/recovery.

## Safety

Back up selector/launcher/running records, relevant preference files and the
one shared button-layout key's effective/user-override state before applying.
No GSettings/dconf writes: the user will test the switch manually. Do not activate
hide/show, launch/restart user applications, alter GNOME beyond the approved
future switch, change keybindings/launchers, packages, services, autostart,
compositor/plugin configuration, or publish/commit. Use the existing non-expiring
session grant. Keep all machine-specific evidence private under ignored work/.

## Tasks

- [x] Verify current state and save private prestate/backups.
- [x] Prepare the exact immutable candidate and run preflight/tests.
- [x] Apply the approved transactional update and owned bar restart.
- [x] Verify new routes, startup/integrity and unchanged shared setting/preferences.
- [x] Record outcome and remaining user/native acceptance without commit.

## Outcome

The approved transactional local update completed and only the owned bar was
restarted, with its existing session-lifetime grant. Exactly four manifested
paths differ from the previous immutable release, as planned. Runtime preflight
and all 1,330 unit tests passed before application. Strict installed manifests,
previous/fallback releases, clean startup markers and all three global
confirmation routes were verified after startup. No unfinished deployment/update
journals remain.

The installed helper's read-only status confirms the new user-wide scope and the
shared button-layout value/user-override state is unchanged. Bar, World Clock,
dock and old partial-policy file prestates are unchanged. No buttons were toggled,
no user application was launched/restarted, and no wallpaper, launcher/binding,
GNOME preference, package, service, autostart, compositor or plugin change was
performed by deployment. Original and fallback versions remain available.

Private preparation, backups, journal references and verification are retained
under work/global-window-controls-deployment-132/. After installation, the user
reported the menu test looks good and works, following the GNOME Files test
request. This records local user acceptance, not a fresh GNOME-login,
concurrent-session, browser-specific or universal-application acceptance claim.
Installation itself performed no button toggles or commit/publication.
