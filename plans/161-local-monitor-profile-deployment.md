# Deploy persistent monitor profiles locally

## Goal and evidence

Fulfil the owner's explicit installation request for Plan 160 D. Compare current
installed manifests/process ownership, the final verified Plan 160 source-check
bundle, all 154 source seals, and the existing display geometry/state. Original
Omarchy remains pinned to ac2690cd7be4f47e4a255f5e2e78d904d436b068; target Hyprland
is 0.57.0, reviewed against efb50993780079460b0cbed1363e2166a2de1d9f. Implementation
is complete but not installed; native acceptance is separate from this request.

## Shape and safety

Diagnose selectors, managed session process, manifest drift, profile/text state
and unresolved journals. Preserve existing audio/Bluetooth/runtime/assets/menu,
settings and receipts. Back up mutable paths with existence/hash/mode and selector
targets; retain the immutable old release as immediate verified fallback. Derive
only the required display shell/helper/manager/updater and provenance changes,
reject unrelated generic-package differences. Verify units, actual contained
profile UI, fake-IPC recovery/automation tests, source seals and runtime preflight.

Install through existing digest/lock/drift guards and restart only the owned
session-lifetime bar; every normal/recovery start uses restore_background=False.
The new component may read current inventory but this deployment must not apply,
save or select a monitor profile, change text size or enable automatic login/
hotplug behavior. Refuse preexisting automatic or pending profile state rather
than activate it implicitly. Record read-only geometry before/after. No packages,
services, reloads, GNOME/security/session/binding/autostart changes, native audio/
Bluetooth actions, commit or publication. Tests/healthy startup do not establish
physical monitor/login/hotplug/pixel/recovery/security acceptance.

## Tasks

- [x] Diagnose current installation, admitted delta, passive profile state and geometry.
- [x] Back up state and prepare narrow candidate with verified immediate fallback.
- [x] Pass fresh units/profile UI/fake-IPC tests and runtime preflight.
- [x] Apply guarded update with wallpaper-disabled owned-bar restart.
- [x] Verify manifests/process/logs, unchanged geometry/preferences/receipts and journals.
- [x] Document installed scope and separately pending native acceptance.

## Compatibility diagnosis and outcome

The read-only precheck exposed overly strict admission of an owned legacy current
state directory behind its private state root. A narrow helper correction admits
that existing layout without chmod, still rejecting foreign/symlink/unprotected
roots. Regression checks also exposed public intermediate-directory defaults in
library-mode creation; missing private ancestors are now explicitly created 0700.
The initial private candidate was retained uninstalled; the revised candidate
passed 1,625 units (28 focused profile cases), seven private fake-IPC scenarios,
actual contained profile QML and runtime preflight before desktop mutation.

Installed as updated-and-started with exactly thirteen manifested changes: seven
shell files, three display helpers, manager/updater export and provenance. All
154 installed seals and helper/manager bytes match. The managed session-lifetime
bar alone restarted, with wallpaper disabled, zero new warnings and no unresolved
journals. Plan 159 is the verified immediate fallback; Plan 157 is retained and
verified. Read-only geometry before/after and installed status RPC pass. Existing
preferences, permissions and native/audio receipts are unchanged; runtime/menu/
assets/audio/Bluetooth are retained. Profile and text-size paths remain absent;
no automatic watcher or recovery guard is running. No native display profile,
text mutation, auto selection, package/service/security/binding/autostart action,
commit or publication occurred.

Private diagnosis/source and mutable-state backups, both preparations, revised
digest-bound review, test/preflight/update/process/log/geometry/health evidence
remain under ignored work/display-deployment-161/ (applied evidence in revised/).
Native device/login/hotplug/pixel/recovery/security acceptance remains pending.
