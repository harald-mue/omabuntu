# Complete monitor-local workspace integration

## Goal and evidence
Finish the Omarchy-based candidate from plan 119 and independently verify whether
the current desktop actually uses it. Compare Omarchy v4.5.0 stable commit
ac2690cd7be4f47e4a255f5e2e78d904d436b068 with the generated policy/widget,
installed Hyprland 0.57.0 at 0aa6745f705f2c4b0a5004eb019ef76e5bbdb426,
existing migration preview, installer, sealed release packager and keybindings
scanner. Read-only live inspection currently still shows the global-ID model;
that is not evidence of monitor-local activation.

## Gaps and proposed shape
Complete fresh-session opt-in, sealed configuration artifacts, safe callback
catalog recovery and an existing-user deployment journal with backups, stale-input
checks and conservative inverse-ID recovery. Preserve the original widget and
allocation module. Do not replace the user's monitor geometry, floating choices,
applications, desktop services or security configuration.

The existing-user path must stop only the owned shell, suppress automatic config
reload while staging files, replace only the exactly reviewed numeric-binding
loop, manually reload once, verify window/workspace/monitor membership and state,
then start the verified installed shell without changing wallpaper. Every affected
file and runtime option needs a recorded previous state and rollback. Recovery
must refuse concurrent edits or ambiguous ID ownership rather than moving unrelated
windows. Shell updates remain ordinary verified release installations, not patches
to an immutable selected release. No normal component receives a timeout lifetime.

## Safety and exclusions
Implementation and read-only diagnosis are authorized. Before a live deployment,
present its concrete changes and obtain explicit installation/configuration/reload
approval; earlier reload approval did not install this candidate. Keep personal
snapshots, diffs, window IDs and logs private under ignored work/ or approved
Omabuntu state. No package installation, logout/reboot, privilege, lock/idle,
services, GNOME or corporate-agent changes; no commit or publication.
A failed or interrupted migration must remain diagnosable and recoverable, not
silently marked successful. Real hotplug/visual acceptance stays separate.

## Tasks
- [x] Inspect current live activation and confirm actual installed version/model.
- [x] Complete conservative migration snapshots and rollback/journal handling.
- [x] Integrate opt-in fresh-session policy and sealed configuration packaging.
- [x] Support monitor-local binding callback discovery/replay in the safe scanner.
- [x] Add executable regression, stale-state and failure/recovery tests.
- [x] Verify generated/provenance seals and isolated widget behavior.
- [x] Run python3 -m unittest discover -s tests -v.
- [x] Document exact supported deployment route and remaining acceptance limits.
- [x] Present the final concrete live-deployment scope for approval.

## Implementation result and approval boundary

The full suite passes 1,279 tests. Generated mirrors, provenance and 127 staged
shell files verify; the isolated original-widget fixture passes without diagnostic
warnings/errors. The official 0.57.0 evaluator comparison exposed that `eval`
returns success rather than expression values; state-directory inspection uses
`repl`, only after checking the pinned version and existing config errors.

A sealed private derivative was prepared without modifying the selected release.
Its twelve changed files are limited to four workspace shell files, the binding
scanner, three configuration artifacts, provenance and the safe updater closure.
The existing runtime, manager, network work and other release artifacts remain
unchanged. An independently refreshed migration review has no current blockers,
including all 45 candidate binding chords. Private candidate metadata, exact
configuration diff and identity/snapshot review are under `work/workspace-120/`.
The stopped-session opt-in also refuses pre-existing global saved state without
explicit attribution; it does not guess where old layout choices belong.

The concrete next approval covers an ordinary local release switch/launcher
update, the exact legacy workspace-loop replacement plus two new Lua modules,
saved-state/ID adoption and marker deployment, backup/journal creation, one
Hyprland config reload and stop/start of the owned shell without wallpaper
restoration. Existing output geometry and application placement are preserved.
The normal inverse release rollback follows workspace restoration first.
At the end of implementation no live install/migration/reload had been performed;
activation required a separate explicit approval.

## Approved activation follow-up

After the user's explicit approval, the sealed local release was installed through
the existing backed-up release transaction. The reviewed workspace migration then
completed with private file backups and its inverse mapping journal. Post-apply
checks confirmed unchanged window identity/membership, floating/fullscreen modes,
monitor geometry, occupied-workspace layouts and the previous autoreload setting.
All 45 original workspace chords have exactly one live registration. Hyprland
reports no configuration errors and the owned shell runs with session lifetime.
Wallpaper restoration was explicitly suppressed for both shell starts.

The shell startup log contains one Qt host-portal app-ID registration warning;
the identical warning was already present in the prior release's log. No portal,
service or security configuration was changed to hide or repair it. Reports and
rollback pointers remain private under `work/workspace-120/activation-*/` and the
normal user-state transaction directories.

- [x] Revalidate the approved artifact/configuration hashes and workspace mapping.
- [x] Install the sealed local release with launcher/selector backups.
- [x] Apply the journaled workspace migration and restore autoreload/session lifetime.
- [x] Verify runtime membership, output/layout preservation, binding uniqueness and logs.
- [x] Obtain positive user feedback for the interactive workspace/window/monitor operations tried.
- [ ] Verify real docking/hotplug and fresh-login behavior separately.

The user subsequently reported that the tried workspace and cross-monitor window
operations work. This is positive interactive feedback, not independently observed
physical hotplug, fresh-login or pixel-level acceptance.
