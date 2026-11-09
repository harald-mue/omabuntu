# Deploy persistent World Clock preferences

## Goal and evidence

Deploy the source repair from plan 111 to the user's existing installation with
an explicitly approved, bar-only restart. The current installation is the verified
release-0.2.3 bundle. Omarchy component behavior remains pinned at
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; no upstream imports or native changes.
Compare installed bundle integrity, the reviewed source derivation and the
existing release-update transaction/rollback path before switching.

## Gap and proposed shape

The active bar still uses process-only preferences. Prepare a private immutable
local derivative of the installed bundle with only the Elsewhen panel, shared
settings adapter/module registration, fixed settings helper, manager helper
environment and recorded local provenance changed. Preserve the original bundle
and native runtime. Verify exact changed-file scope and run runtime preflight.
Use the established update journal, selector/launcher backups and rollback on
startup failure. Record preference-file prestate before restart and keep private
machine-specific evidence under ignored work/.

## Safety and exclusions

User approval covers deployment and the owned bar restart, not commit,
publication, installation of packages, session transitions, config reloads,
wallpaper reapplication, lock, plugins, services or native runtime changes.
Do not print process environments or city/person values. Read only the necessary
session environment keys for the owned process. Keep session-lifetime behavior;
no timed wrapper. Existing unsaved process-only cities are not recoverable through
the old panel's public API; do not claim migration. A clean startup and on-disk
state are not interactive or next-login acceptance.

## Tasks

- [x] Verify installed bundle, owned process, narrow file differences and prestate.
- [x] Prepare and verify a private candidate and update plan; run unit tests.
- [x] Deploy through the backed-up update transaction and restart only the bar.
- [x] Verify bundle integrity, startup logs and settings state; document outcome.

## Outcome

The established update transaction deployed a verified private derivative with
exactly six changed bundle files, including local provenance. Runtime preflight
and all 1196 unit tests passed. The owned bar restarted with session lifetime;
wallpaper restoration was explicitly disabled for both start and rollback.
No native transition, state-schema migration, package or compositor change ran.

Post-start checks verified bundle integrity, clean startup, creation of valid
mode-0600 settings and the unchanged original release retained as previous.
Private prestate, candidate scope, journals and verification are retained under
`work/world-clock-deployment-112/`. Interactive city edits, persistence after
another live restart and next-login acceptance remain unverified. No commit or
publication was performed.
