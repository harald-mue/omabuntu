# Controlled Appearance controls deployment and live verification

## Goal and evidence

Deploy plan 094's reviewed Menu Bar/Dock controls to the existing Hyprland
shell, preserving a working recovery path and all unrelated configuration.
User explicitly approved deployment and controlled live testing. Compare the
verified current installed release with sealed repository QML, the three
Appearance-related Python helpers and menu definitions. Original menu behavior
is pinned to Omarchy v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Plan 094 passed 1105 unit tests,
clean-source and contained menu/clock/panel fixtures, not native acceptance.

## Current gaps and proposed shape

The running installed shell predates these controls. Prepare a new private local
release by cloning the verified installed bundle and replacing only reviewed
Appearance files; retain runtime, assets, native artifacts, manager and all other
bytes. Record changed-file digests and local provenance; rebuild and verify the
release manifest. Use the existing reviewed update transaction with bar-only
restart, session-lifetime grant and wallpaper restoration disabled. Record
prestate and preserve selectors/launcher and relevant preference paths before
mutations. Verify independent keyboard menu bindings before any bar-hide test.
Use backend transaction tokens to restore any temporary preference changes.
Native visual, keyboard and interaction acceptance requires user feedback.

## Safety and exclusions

No package, service, autostart, session/login transition, Hyprland config/reload,
keybinding edit, plugin activation, wallpaper change, GNOME/profile/GTK setting,
lock/idle/suspend or boot/authentication operation. No timed desktop wrapper,
force kill, publication or commit. Never alter the selected immutable release
in place or modify the published v0.2.0 artifacts. Abort on unexpected identity,
source drift, missing recovery route or incompatible update contract. Restore
the previous application selection/startup if the new shell fails. Keep raw
bind details, machine-specific state and logs under ignored private work/ only.

## Tasks

- [x] Diagnose running release, preferences and independent menu recovery route.
- [x] Back up prestate and prepare/verify a narrowly adapted local release.
- [x] Apply transactional update with bar-only restart and inspect startup.
- [x] Verify live preference plumbing/recovery without retaining diagnostic changes.
- [x] Run unit tests and document results and outstanding user acceptance.

## Result and live-discovered correction

The first private release changed only the seven reviewed QML files, three
helpers, menu definitions and provenance. Application-only update preserved
runtime/assets/native artifacts and performed no state migration. Startup passed.

Native diagnostics exposed stale bar state after rollback removed a previously
absent preference file. Backed up the affected repository sources and corrected
the actual file watcher's load-failure refresh path and state-home override.
An extended contained menu fixture now uses that production watcher and asserts
default restoration after file deletion once pending requests have drained.
The corrected fixture passed, while an intentionally broken watcher was rejected
at that deletion assertion. The final 1105-test unit suite and clean-source
export/check also passed.
A second narrowly adapted local release (watcher and provenance only) was
transactionally deployed and started successfully.

Final live diagnostics passed: preference persistence without shell errors,
three-output bar hiding and exact position recovery, and independent named menu
opening while bars were hidden. All diagnostic transactions were reversed to
the fresh baseline. A separate background selection made between test phases
was preserved rather than overwritten. An initial baseline mismatch correctly
stopped verification instead of silently undoing the later selection.

Failed attempts and recovery evidence remain private under ignored work/. These
include the obsolete pre-0.57 dispatcher syntax refusal and diagnostic-generated
Python bytecode, which was archived out of the installed bundle to restore its
manifest integrity; subsequent helper diagnostics disable bytecode writes.

No physical keyboard, visual, right-click, dock interaction, real battery,
GNOME or fresh-machine acceptance is claimed. User feedback is still required.
No bindings, compositor configuration, wallpaper, services, packages, login,
lock/authentication or published artifacts were changed. No commit was made.
