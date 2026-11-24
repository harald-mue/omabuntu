# Persistent reversible monitor profiles

## Goal, evidence and current gaps

Implement D completely in source: named persistent output profiles, supported
modes, positions, transforms, scale, enable/disable with a surviving output,
original text-size controls, explicit review/apply/keep/revert, interrupted-action
recovery and opt-in exact-topology login/hotplug reapplication. Existing brightness
and runtime scaling are not persistent profiles. Compare the original MIT monitor
Panel at Omarchy v4.5.0 ac2690cd7be4f47e4a255f5e2e78d904d436b068, the pinned
Hyprland 0.57.0 Lua/monitor/IPC contracts and current workspace ownership. Check
official version-appropriate documentation before configuration work.

## Shape and safety

Use Python standard library, private closed-schema profiles and fsynced receipts,
locks, session/topology/identity/digest guards, readback and explicit recovery.
Keep original panel/layout; add a distinct profile-management page, not a
replacement normal panel. Keep text sizing shell-local and explicitly describe
that scope instead of silently changing GNOME/GTK/global application fonts.
Apply output rules through documented Lua with reviewed modes and numeric fields,
never arbitrary programs. Back up all affected paths/state before mutation. A
bounded apply-confirmation watchdog is transaction safety, not component expiry.
Preserve unrelated monitor options, GNOME, corporate settings, login, workspace
policies, brightness and bindings. Auto reapplication is explicit per-profile
consent, only for a previously kept exact connected topology; it is not a service,
a new autostart registration or an external-writer override loop.

Source development/testing/packaging only: do not apply to the live desktop,
reload, restart, install packages/services, edit real compositor/session config,
activate automation, commit or publish. No HDR/VRR/color/custom modelines, mirroring,
workspace reassignment, GNOME/global text sizing, security/boot changes or claim
of pixel/hardware/hotplug/recovery/security acceptance from mocks. Unsupported or
ambiguous identities/modes/topologies refuse explicitly.

## Tasks

- [x] Record official contracts, source baseline backups and narrow integration seams.
- [x] Implement validation, persistent profile CRUD, digest-bound review and safe apply.
- [x] Implement keep/revert/watchdog/interruption recovery and external-drift refusal.
- [x] Implement explicit exact-topology session/login/hotplug automation.
- [x] Restore original text-size controls with reversible shell-local persistence.
- [x] Integrate original panel/profile UI, shared owner, source seals and packaging.
- [x] Test pure contracts, failure/recovery/automation and actual contained QML.
- [x] Pass full regressions and document exclusions/deployment/acceptance boundaries.

## Source outcome

The original monitor parent remains intact; the strict derived surface restores
its text-size section and opens a separate explicit profile page. One shared
session owner controls named private profiles, identity/mode/geometry validation,
reviewed sequential apply, Keep/Restore, an independently surviving confirmation
guard and previously accepted exact-topology automatic reapplication. Original
runtime scaling cooperates with the same recovery lock/fence. Previous layouts
are available as fresh reviewable recovery drafts. Known advanced color/VRR/
mirroring configurations refuse; wildcard-default, full rule ownership and
window/workspace placement rollback limitations are disclosed in the UI/docs.

Passed 1,624 units (27 focused profile cases), seven real-process private fake-IPC
scenarios including parent/text-write death and startup/hotplug, actual original
QML/Process/editor/automation revocation/re-enable/text-readback controls, 43 audio,
39 frame, eight tooltip, desktop/clock and clean-source regressions. A private
source-check bundle verifies all 154 seals, three display helper modules, manager,
updater closure, immutable manifest and runtime preflight, retaining the Bluetooth
helper. No live monitor or text setting, auto policy, session/config, package,
service, binding/autostart, commit or publication was changed. Plan 159 remains
the installed checkpoint, not an installation of these source changes.

See docs/display-profiles.md for supported behavior and exclusions. Private
baseline backups with hashes/modes, research contracts, fake IPC/QML tests and
package/regression evidence remain under ignored work/display-profiles-160/.
Deployment and native display/login/hotplug/pixel/recovery/security acceptance
remain separate unperformed gates at this source checkpoint; collection and mocks
do not close them. The owner's subsequent request is fulfilled separately by
Plan 161: a narrow derivative is installed with a managed-bar-only wallpaper-
disabled restart. Its legacy-directory compatibility fix preserves existing
permissions and passes 1,625 units/28 focused profile cases. Geometry/text are
unchanged, no profile/automation is activated, and native acceptance stays open.
