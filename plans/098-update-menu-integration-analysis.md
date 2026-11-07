# Assess the original Update menu and a safe Omabuntu integration

## Goal and evidence

Locate the original Update hierarchy and actions in Omarchy v4.5.0 stable,
pinned to commit `ac2690cd7be4f47e4a255f5e2e78d904d436b068`, and propose an
Ubuntu-native integration into Omabuntu's command menu. Compare the pinned menu
and relevant upstream helpers with the existing closed menu registry, signed
published-release download path and reviewed application-update transaction.
Clarify that the existing documented menu shortcut is Super+Space, while the
user named Ctrl+Space; do not change any binding as part of this analysis.

## Current gaps and proposed analysis

Omabuntu excludes the original Update root. Public release installation/update
and prepared-bundle rollback already exist but have no command-menu route.
Determine safe reuse, launcher/packaging closure, confirmation/restart boundaries,
and handling of locally adapted releases versus the latest public release.
Preserve original hierarchy where useful; do not import Arch update/provisioning
scripts or conflate application updates with Ubuntu or corporate management.

## Safety and exclusions

Repository/source analysis and documentation only. Do not execute update helpers,
fetch/install releases, change repositories/packages, reset configuration,
restart components, alter keybindings, modify user state, commit or publish.
No kernel, firmware, Plymouth, password/authentication, timezone/system-time,
network/audio service or security-policy changes. A future implementation needs
its own approved scope and live deployment gate. Keep raw/source-verification
records under ignored work/; no private machine details in repository documents.

## Tasks

- [x] Verify relevant pinned upstream menu/helper blobs and map Update entries.
- [x] Compare existing signed update/rollback paths and identify integration gaps.
- [x] Document a recommended menu shape, safety gates and explicit exclusions.
- [x] Run unit tests and diff checks after the documentation changes.

## Result

`docs/update-menu-assessment.md` records the exact upstream hierarchy and a
first-batch Update > Omabuntu terminal-review proposal, with optional later
Status/Rollback and Process > Shell adaptations. Eight original blobs match the
pinned stable Git tree. Existing public download verification and application
transactions are reusable, but a check-only API, packaged trusted dependency
closure, explicit local/public version policy and wallpaper-preserving restart
path are required. The general installer is broader than an application update.
Ctrl versus the configured Super menu binding remains to be clarified.

All 1107 unit tests and `git diff --check` passed. Private verification/test
records remain under ignored `work/update-menu-098/`. No product/live change,
release-service request, commit or publication was performed.
