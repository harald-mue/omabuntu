# Remove disabled feature runtime hooks

## Goal and evidence

Implement Plan 170's approved cleanup: remove the withdrawn Advanced audio live
objects and optional untyped-input bridge from the normal shell, and decouple
normal monitor controls from profile workflow code. Preserve the original-derived
normal controls and layout from Omarchy
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`, Plan 162 monitor behavior and accepted
audio/OSD geometry. This cleanup is not a proven crash fix.

## Gaps and proposed shape

Remove optional audio state/controls/untyped files from the packaged shell and
normal provider/controller/view references, retaining offline recovery/backend
sources and tests deliberately. Extract neutral monitor session, safe state,
locking, pending-recovery guard and text-size helpers so normal controls never
import the profile workflow or enumerate profile history. Keep legacy profile
code compatible with the same state/lock paths. Exclude withdrawn profile QML
from normal packaging and drop its unused helper environment variable. Preserve
private profile stores, text settings, backups and recovery receipts.

## Safety and exclusions

Back up each affected existing project file with hashes/modes before edits.
No live shell restart, debugger interruption, installation, packages, native
setters, service activation, settings migration, secret publication or commits.
The active GDB run remains on the unchanged installed release. Deployment will
require a separate explicit approval. Normal typed input/output/stream controls,
DSP routing, peak monitoring, OSD and shared pending-transaction guards remain.
Review version-matched official monitor documentation already pinned in Plan 166;
do not change compositor configuration or command semantics.

## Tasks

- [x] Back up affected source paths; confirm cleanup/dependency boundaries.
- [x] Remove optional live audio roots and packaged withdrawn QML/JS.
- [x] Extract neutral monitor helpers and decouple normal text/status/actions.
- [x] Update source derivations, provenance seals, fixtures and regressions.
- [x] Run all unit and contained audio/display/source checks.
- [x] Document exclusions, recovery retention and undeployed status; verify
      active diagnostic shell remains untouched.

## Result and verification

The ordinary panel no longer constructs optional audio state or controls, and
its provider/controller no longer merge untyped inputs or expose profile-page
hooks. Five withdrawn audio/profile QML/JS sources remain sealed in the new
`offline_authored` provenance section but are absent from normal staging and
packaging. Synthetic backend recovery tests explicitly admit only the needed
sealed offline bridge into their disposable case. The former optional-input
long-gesture case was retired with that runtime route; ordinary typed input
identity/churn/gesture guards remain covered. No new replacement panel or
upstream asset was introduced; the original view derivation is now v9.

`display_common.py` owns neutral native/session/inventory and private-state
primitives. Normal controls no longer import the profile workflow/model. Legacy
lock, pending and text paths remain shared with offline recovery. New normal
text backups record prior bytes/mode under `desktop-actions/`, without invoking
profile overview, store parsing or transaction-history enumeration. Legacy data
and backups are preserved, and no migration was performed. Normal output/scale
commands and compositor configuration semantics were not changed.

Verification passed:

- `python3 -m unittest discover -s tests -v`: 1,661 tests.
- 42 contained audio cases, including real derived normal layout, absent optional
  objects/navigation, overflow/reopen and shared-owner peak monitoring.
- Contained desktop surface construction/action routing and five clock checks.
- 39 contained frame cases and eight tooltip cases.
- Clean candidate export without original private work/images: all nine checks.
- Source seals/derivation validation and `git diff --check`.
- Hash/mode verification of backups for all 22 changed existing tracked files.
- Read-only identity check: the same installed shell, start ticks, GDB parent and
  tracer remain active; no native capture/backtrace had fired at that check.

Private backup/prestate, final unit log, check pointers and verification receipt
are under `work/disabled-feature-cleanup-171/`. Individual contained checks retain
their own private reports. Repository docs distinguish this source result from
the unchanged installed Plan 163 release.

No installation, desktop restart, native setter, settings migration, debugger
interruption or commit occurred. Recovery helpers remain packaged but inactive;
withdrawn offline QML views are not a newly accepted recovery interface. Device,
pixel, real popup, long-uptime and crash acceptance remain excluded. A native
backtrace is still needed for crash attribution; deployment needs separate
approval.
