# Rebase admitted desktop components onto Omarchy 4.5.0 stable

## Goal and evidence

Use only Omarchy v4.5.0, commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`, as the new admitted-component
baseline. The prior baseline is v4.5.0-rc1,
`03ff1eff3812933f7088484533784d2f63eaf19a`. Plan 077 and
`docs/omarchy-upstream-analysis.md` record the immutable tree comparison: 22
changed parents among the 71 currently mapped sources. Development/quattro
changes are explicitly not selected. Network and weather extraction witnesses
need reviewed changes; shared motion/popout APIs and the new WallClock dependency
need closure checks, not just updated hashes.

The upstream MIT notice was checked unchanged before importing. Existing
per-component notices and dataset restrictions remain. Review new imports in
full. Retain narrowly adapted Ubuntu backends and original visible component
source; do not replace the original layout with new authored panels.

## Shape and current gaps

Back up existing source paths privately before editing. Import hash-checked
stable vendor parents, register required new dependencies, update transformations
without weakening their command/security guards, regenerate checked mirrors,
and update provenance together. Preserve historical reference-package evidence
and independently pinned artwork/runtime inputs rather than falsely relabeling
them. Inspect and document menu/backend deltas and every deferred upstream
feature. Add deterministic regression tests and run the full suite plus available
non-live source/closure checks. Record missing native validation explicitly.

## Safety and exclusions

The user approved the stable source update, not deployment. Do not edit installed
configuration, rebuild/install packages, start/restart services, reload Hyprland,
change session state, or modify the separate reference package. No upstream
helpers/installers/migrations are executed. No new location/network endpoints,
DNS/VPN changes, corporate browser policies, security/authentication policy,
lock/idle/suspend activation or monitor-layout writes. Keep the accepted
`render.cm_auto_hdr = 0`. Keep runtime and plugin ABI pins unchanged unless a
separate source-reviewed requirement is established. No commit or publication
without a new explicit request.

Full upstream root/service-registry activation, widget drag-layout persistence,
notification ownership, agents/AI assets, full audio parity and other previously
excluded capabilities are not silently admitted by this rebase. The report will
separate source alignment from visual/live acceptance and full-shell parity.

## Tasks

- [x] Back up candidate files and verify stable source/license hashes.
- [x] Review and import stable parents and required dependency closure.
- [x] Adapt network/weather and shared UI contracts while preserving Ubuntu safety boundaries.
- [x] Regenerate mirrors and update coherent per-component provenance/checkers.
- [x] Add regression coverage, run unit and available contained/clean-source checks.
- [x] Document retained deviations, deferred features, validation and deployment boundary.

## Outcome

The admitted profile maps 76 targets to 72 original stable source parents,
including WallClock. Auto-hide/peek tracking is explicitly removed from the
fixed top-only frame rather than leaving a missing BarModel dependency.
Legacy style-provider aliases retain image-picker listing and apply behavior.

All 1079 unit tests and the clean-source export check pass. Contained clock,
clock-math, tray, tooltip (eight cases), frame, network, Wi-Fi, audio,
applications, keyboard-layout, desktop-panel, spacer, menu and image-picker
checks pass using the existing verified runtime stage. Fixture-only window
substitutions and missing native acceptance are documented in
`docs/omarchy-450-update.md`. No deployment, package rebuild/install, reload,
service/session transition, commit or publication was performed.
