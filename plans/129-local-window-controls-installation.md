# Prepare and install the local Window Controls configuration

## Goal and evidence

Install the user-requested plan-128 partial Window Controls Setup configuration
locally. Compare the verified selected release and exact source delta with the
plan-128 tests and authored-source review. Omarchy component baseline remains
v4.5.0 commit ac2690cd7be4f47e4a255f5e2e78d904d436b068.

## Current gap and shape

The running release does not contain the new menu/backend. Prepare an immutable
private derivative of the verified selected bundle, replacing only required
menu/helper files and recording provenance. Preserve native runtime, installed
manager, hyprbars, existing launcher behavior and personal preferences. Verify
all changed paths and use the established transactional local-update contract,
not in-place mutation of the selected release. Save narrow selector/launcher/
policy prestates and retain the previous immutable release for rollback.

## Safety and approval gates

The user requested local installation, not toolkit-policy activation, app
restarts, session/configuration changes, packages, services, autostart, wallpaper
reapplication, commit or publication. Do not change GNOME or existing app
launchers. Read only required installation metadata and the owned bar context;
never print complete environments or credentials. Back up affected paths and
record exact before-state prior to apply. Ask separately before stopping or
restarting the owned bar if needed to select/activate the candidate. No timed
wrapper: retain the approved session lifetime. Preparation is not deployment.

## Tasks

- [x] Diagnose selected/running release, update contract and exact delta.
- [x] Record private prestates and prepare/verify an immutable local candidate.
- [x] Run tests and review the exact transactional install/preflight plan.
- [x] Obtain any required bar-restart approval before switching the application.
- [x] Apply the approved local update and verify integrity/startup and rollback.
- [x] Document actual outcome and remaining native acceptance; do not commit.

## Preparation checkpoint (before restart approval)

Verified current and previous releases and the owned session-lifetime bar; no
pending deployment/update journals were found. Prepared an immutable private
candidate with exactly five changed manifested files: CommandMenu.qml, the menu
JSONC, menu_model.py, new window_controls.py, and local provenance. Native
runtime, manager and all other bundle files are identical to the selected base.
Private selector/launcher/running/preference prestates and candidate metadata are
under work/window-controls-deployment-129/.

Runtime/package preflight passed without installation or activation. All 1,323
unit tests pass (7.954 seconds); git diff --check passes. The reviewed update
requires stopping/restarting the owned running bar. No selectors, launchers,
preferences, services or desktop state have been changed. Deployment is paused
for that explicit approval. Native rendering and interactive acceptance remain
unverified.

## Approved deployment outcome

After the user's explicit bar-restart approval, the established update transaction
installed the private candidate and restarted only the owned bar. Wallpaper
restoration was disabled for both normal start and failure recovery. The journal
completed successfully; current/previous selectors, strict bundle manifests,
retained fallback, session-lifetime process identity and startup markers verified.
Exactly the five reviewed manifested paths differ from the original release.
No startup error markers or unresolved deployment/update journals were found.

The first standalone post-start menu-definition probe omitted the installed
manager's OMABUNTU_MENU_DEFINITIONS environment and therefore used development
layout defaults. A corrected read-only probe with the installed definitions path
verified all four new menu routes; no second deployment/restart was needed.

Bar, World Clock, dock and window-control preference prestate remained unchanged.
The update did not activate a toolkit policy or change GNOME, existing app
launchers, native runtime, plugins, wallpaper, packages, services, autostart or
compositor configuration. No real application launch, session transition, commit
or publication occurred. Interactive menu layout and native toolkit behavior
remain for user acceptance. Private apply/result/verification evidence is retained
under work/window-controls-deployment-129/.
