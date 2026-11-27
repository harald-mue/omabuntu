# Remove background image import and restore the shell

## Goal and evidence

The owner explicitly requests removal of background image import and its badly
rendered dialog, followed by a shell restart. Plan 187 preserved a real SIGSEGV
in Qt's file-dialog show/select path. Omarchy behavior remains pinned at
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`: retain its personal per-theme folder
and original carousel, not a replacement chooser. The import convenience is
withdrawn, not approved for replacement by another dialog.

## Shape and constraints

Remove the import menu route, QML dialog/lifecycle adaptations, helper CLI,
copy/validation implementation and installer prerequisite. Keep safe personal
folder opening/enumeration, Pictures/built-in sources and per-theme choices.
Retain user images, old import receipts, failed artifacts and crash evidence.
Back up every affected source path with hashes/modes before edits. Build only
a minimal sealed overlay; preserve notification runtime/source, audio, display,
screenshot and security components. Restart with a fresh exact session/parent
notification grant and GDB, without wallpaper restore or provider activation.

The shell is already dead: admission must verify its exact stale record,
completed fatal capture, unchanged selected release and same compositor session,
absence of other shells and notification owners, and the existing provider fence.
Do not weaken the normal running-shell upgrade preflight or reuse a spent grant.
Failure must remain explicit and fail closed rather than revive the crashing
import dialog or start a competing notification server.

## Tasks

- [x] Back up affected source files and retain completed crash evidence.
- [x] Remove import completely while preserving folder/picker/theme functionality.
- [x] Add withdrawal/stopped-session guards and test retained functionality.
- [x] Run full unit, source integrity and contained picker/native checks.
- [x] Prepare the minimal overlay, back up live metadata and restart with fresh grant/GDB.
- [x] Verify shell, notification ownership/readiness/DND, capture and removed surface.

No package installation/removal, service activation, wallpaper change, user image
removal, commit or publication is authorized by this plan.

## Completion

Removed the import action, CLI, copying implementation and dialog completely.
Restored ImagePicker, CommandMenu and TrialShell to their pre-import source,
including ordinary paint/input/focus behavior. Personal folder enumeration,
original-style directory opening, existing image sources and remembered choices
remain. Removed the chooser prerequisite declaration without uninstalling any
pre-existing system package or touching user images/receipts.

The full suite passes 1,839 tests, including new exact stopped-session admission
and withdrawal refusals; the clean-source gate passes all nine checks. The
contained original offscreen/native carousel checks pass without any chooser.

Installed `background-folders-no-import-188`, verified all 387 seals, and restored
the session shell with a fresh consumed parent-bound notification grant and GDB.
The sole notification owner is the restored shell, role readiness is true and
DND remains off. Runtime/source notification closure, audio, display and screenshot
components are unchanged; the runtime provider fence remains in place. The
QuickDialogs library is not loaded in the restored shell. Wallpaper restore was
not requested. Fourteen source backups, three live metadata backups and all
thirteen prior crash evidence files were verified; the original crash run is
unchanged. Startup verification is not indefinite stability or pixel acceptance.

Private reports and the explicit restart transaction are retained under ignored
work/ and private state. No commit, publication or unrelated desktop change was
performed.
