# User theme backgrounds and image import

## Goal and evidence

Implement the owner-approved per-theme user artwork folder, open-folder and
multi-image import actions, preserving the existing carousel and Pictures source.
Compare Omarchy v4.5.0 `ac2690cd7be4f47e4a255f5e2e78d904d436b068` helpers
`omarchy-theme-bg-install`, `bg-switcher`, `bg-next`, `bg-set` and theme selection.
The original opens a user theme folder and lists it with supplied artwork; the
multi-select copy dialog is an explicit Ubuntu convenience adaptation.

## Gaps and shape

The current backend enumerates supplied artwork and nonrecursive Ubuntu/Pictures
roots, not per-theme personal artwork. Add an XDG-config user root independent of
releases and Git, safe direct-child theme IDs, deterministic bounded image rows,
allowlist/restore integration, and original-style folder opening. Inspection found
QtQuick.Dialogs already available, so use its FileDialog for multi-selection,
without installing a dependency or replacing the original carousel. Unlike the
initial Zenity idea, file URLs are JSON rather than ambiguous delimited filenames.
Import only validated supported still files, never overwrite or move originals,
reserve collision-free names atomically and record private import receipts. No
wallpaper/theme change on import, no unsolicited opening/scan of personal files.
Selection cancellation is benign; partial failures are explicit and preserved.

## Safety and live completion

Back up affected project/live paths with hashes/modes. Test synthetic images,
unsafe paths/symlinks/collisions/limits and provider/restore behavior without real
personal data. Preserve current audio/monitor/notification components and user DND.
Prepare a minimal overlay of the verified live release, not unrelated source
cleanup. The owner authorizes implementation through completion without further
questions, including the scoped backed-up live shell/GDB transition. Maintain the
notification activation fence and issue a fresh exact session grant; preserve
current notifications/state without collecting their contents. Startup failure
restores the prior release/capture. Do not install packages, activate lock/session
changes, change wallpaper on deployment, commit or publish. Normal interactive
components/dialogs do not expire; only disposable diagnostics have watchdogs.

## Tasks

- [x] Inspect current picker/menu/backend/theme/live release integration contracts.
- [x] Implement bounded personal artwork enumeration and safe copy/import/open actions.
- [x] Integrate original menu/picker and theme/restore selection without regressions.
- [x] Add unit/integration/refusal coverage and run full units/clean-source checks.
- [x] Prepare/back up/verify the minimal live overlay and complete the approved restart.
- [x] Verify actual release, notification role/DND and GDB; document use and recovery.

## Completion

Implemented and deployed `theme-backgrounds-186-v3` as a minimal overlay, preserving
387 file seals, the exact notification runtime/source closure, audio/monitor
components and screenshot integration. Existing runtime-only SwayNC fencing and
DND were preserved; the new shell has a fresh claimed session/parent grant and
verified GDB capture. Deployment did not request wallpaper restoration.

The real native chooser exposed a layering defect in the first live increment:
a normal dialog was covered by the overlay carousel. The final picker keeps its
parent mapped but suspends overlay paint, pointer input and keyboard focus while
the chooser is visible. A private real-pointer Cancel and virtual-keyboard local
file selection pass with the original PanelWindow, exact copied bytes, provider
refresh and no import-triggered apply. Failed controls remain private; no test
warnings were suppressed. Initial input before an acquired seat is not confused
with actual user interaction or Hyprland focus-policy acceptance.

Added synthetic admission/collision/path/refusal/partial-failure/theme-memory and
upgrade-guard regressions. Legacy artwork tests now isolate XDG config as well as
state, rather than depending on personal folders in the real home. The full unit
suite passes 1,846 tests and the clean-source gate passes all nine checks. The
runtime prerequisite manifest declares the reused QtQuick.Dialogs module; no
packages, sources, services, wallpaper, lock configuration or autostart were
installed/changed by this request.

Private evidence, verified backups, native captures, both live journals and
retained failed candidates are under ignored `work/background-import-186/` and
the existing private state directories. Recovery remains explicit, ownership-
checked and sequential, with a fresh prior-release notification grant; no live
failure recovery rehearsal, production-image decoder security, manual host
chooser acceptance, notification privacy acceptance or crash causality is claimed.
No commit or publication was performed.
