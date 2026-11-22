# Original shared bar peek ownership (source only)

## Goal and compared evidence

Restore the original shared hover tally, 120ms leave hysteresis, frozen per-output
center-box edge and public center reveal/suppression API in the admitted horizontal
bar frame. This is an ownership prerequisite, not new authored indicator visuals.
Compare unchanged MIT Omarchy v4.5.0 commit
ac2690cd7be4f47e4a255f5e2e78d904d436b068 Bar.qml, BarModel.js, and the admitted
clock/weather panel callbacks. License and existing origin records were checked
before derivation. No new upstream package or asset is imported.

## Current gap and shape

Plan 142 restored fullscreen input suppression. The frame still strips the
original center edge synchronization and ancestor HoverHandler; the shared bar
API lacks the original center peek state and suppression callback. Derive a
nonvisual shared BarPeekState from original properties/functions/Timer. Restore
original center-box synchronization into the per-output frame, and the original
ancestor HoverHandler with narrow hidden/fullscreen suppression and idempotent
owner handoff/teardown. Expose shared state/callback on the existing trusted API.
Do not apply the suppression flag to the upstream hover tally: it is a separate
consumer-facing value. No current admitted indicator consumes the reveal flag;
this checkpoint must not claim visual indicator expansion or completed peek.

## Safety and exclusions

Source and fake-service/offscreen checks only; preserve the dirty tree and vendor
parents/reference package. Back up every affected path with prior existence,
mode and hash. No host compositor/audio query, configuration, native pointer or
fullscreen experiment, installed-path/PID probe, deployment/reload/restart,
package/source/privilege/service/agent/security/session action, commit or publish.
Keep geometry, 26px reservation, input masks, focus policy, layout persistence,
media/audio/native backends and defaults unchanged. No new panel, command,
polling, visual fade, popup close/grab policy, vertical/notch variant or arbitrary
plugin registry. The original 120ms input hysteresis does not expire components;
normal approved runtime remains session-lifetime. No native hover/input/focus/
click-through/pixel/security acceptance is established here.

## Tasks

- [x] Back up affected paths and preserve existing changes.
- [x] Extract original shared state and restore the closed frame hover/edge seams.
- [x] Bind shared owner/API and hide/fullscreen suppression on real bar outputs.
- [x] Cover tally ordering, handoff, teardown, edge freeze and actual leave delay.
- [x] Synchronize mirrors, seals, provenance, source-copy tests and documentation.
- [x] Pass full units, contained suites, clean-source and backup/whitespace checks.
- [x] Record completion and remaining visual/native/deployment gates.

## Completed checkpoint

BarPeekState.qml is derived/sealed as bar-peek-owner-v1; BarFrame advances to
original-horizontal-peek-v5. Its original center sections now synchronize the
per-output edge and its ancestor handler reports owned hover into one shared
state. Idempotent handoff covers late attachment, suppression, replacement,
actual deferred peer destruction and shared-owner destruction/replacement. The
source-derived 120ms Timer closes reveal state after final leave, and stops on
quick reentry. Clock/weather callbacks reach the independent original API flag.
No indicator expansion is claimed: none of the admitted indicators consumes
reveal state yet. No new UI panel, geometry, reservation, masks, focus policy,
settings or persistence was added. Vendor parents/model/notices/module maps and
unrelated source records are unchanged.

Verification: 1,490 units including six new contracts, 31 isolated frame cases
including three new ownership/edge/delay cases, audio 32, tray 5, network 7,
tooltip 8, clock 5 and desktop compile all passed. Full unit log:
work/plan-143-units-final.log. Contained report set dated 20261122T131811;
frame work/frame-port/20261122T131811.417933Z/report.json;
clean-source work/clean-source/20261122T131811.410842Z/report.json passed.
All 137 sealed runtime sources, generated mirrors, whitespace and twelve
prestate records verified. Backups:
work/backups/plan-143-20261122T131028302394Z/.
Private source hashes/report summary: work/bar-peek-143/verification.json.

Initial source-only unit diagnostics are retained in work/plan-143-bar-units.log:
the synchronization script initially used the wrong review-list key and did not
write metadata; it was corrected to the existing review field. An extraction
mutation test duplicated a shorter non-witness prefix rather than the complete
closed witness; it now duplicates the actual witness and verifies rejection.
No source admission rule was weakened. Both isolated frame runs passed; the
final run additionally verifies actual shared-owner destruction/replacement.

No host compositor/audio query or mutation, installed-path/PID probe, native
pointer/fullscreen experiment, deployment/reload/restart, configuration, package,
service/agent/security/session action, commit or publication occurred. Plan 135
remains the last verified installation; Plans 136–143 are source-only. Native
hover/input/focus/click-through/pixel/security acceptance, real indicator
consumers, full fullscreen/peek/popup policy and remaining A–E work stay open.
