# Original fullscreen bar input ownership

## Goal and evidence

Continue A with the original per-output fullscreen observation and empty input
region, not another panel or an unreviewed whole-shell startup. Keep source-only.
Baseline: Omarchy v4.5.0 ac2690cd7be4f47e4a255f5e2e78d904d436b068, unchanged
MIT Bar.qml and already-admitted BarModel.js. Preserve complete notices and
vendor bytes; derive the original underFullscreen binding and raw fullscreen
read-refresh handler through unique extraction witnesses.

Official pinned Quickshell 2b4501a282689792b62e94f3fb30d8f512324fe6
wayland/hyprland/ipc/qml.hpp and hyprland_toplevel.hpp document monitorFor,
refreshToplevels, per-output active workspaces and lastIpcObject's explicit refresh
requirement. Reviewed local official Hyprland 0.57 source pin
efb50993780079460b0cbed1363e2166a2de1d9f: HyprCtl.cpp publishes internal
fullscreen mode; FullscreenController.hpp distinguishes maximized (1) and real
fullscreen (2). No Hyprland configuration or dispatch is needed or authorized.

## Current gap and proposed shape

TrialPanel currently always exposes its 26px idle input strip, even while the
compositor suppresses its visual top layer for fullscreen. A remap/layer-order
change can leave invisible input over a fullscreen client's top edge.

Add a source-derived nonvisual BarFullscreenState owner, per output, using the
unchanged original fullscreenOn model and active workspace binding. Missing
screen/monitor/workspace does not borrow the focused output. One separate instance
in the shared Variants owner enables the original event-driven read refresh;
output observers do not multiply queries. No startup dispatch, polling or timer.

Wire original empty/strip input Regions into the existing stable surface.
Explicit hide and fullscreen suppression dominate full-screen drag input. Cancel
an owned drag on suppression, without layout writes, to avoid a hidden full-screen
grab; this precedence/cancellation is a narrow reviewed Ubuntu adaptation from
upstream's drag-first expression. Keep exclusive zone, surface size/namespace,
keyboard policy, compositor-owned visual fullscreen behavior and user preferences
unchanged. No manual opacity/fade, popup closing or reveal/peek policy is added.

## Safety and exclusions

Back up affected paths with existence/hash/mode under ignored work/ before edits,
preserve existing changes, and leave vendor/reference sources unchanged.
Only pure model and fake-Hyprland/offscreen checks run: no host compositor/audio
query/dispatch, installed-path/PID check, native fullscreen transition, deployment,
reload/restart, packages, privilege, services/agents/radio/security/session changes,
commit or publication. No expiry, autostart or supervision.

This is not native click-through, pointer/grab/focus, remap, pixel, authentication
or security acceptance. Full visual fullscreen/peek/reveal, popup fullscreen
policy, vertical/notch/edge relocation, theme ownership and remaining A–E stay open.

## Tasks

- [x] Diagnose original/native contracts and current surface gap.
- [x] Back up affected paths and preserve prior changes.
- [x] Derive the original fullscreen observer/event refresh with closed witnesses.
- [x] Bind empty input regions and no-write drag cancellation to the real surface.
- [x] Add per-output/reactive/multiowner/drag/refresh fake-service checks.
- [x] Synchronize source mirrors, provenance/seals, tests and current docs.
- [x] Pass full units, contained regressions, clean-source and backup checks.
- [x] Record source-only completion and explicit remaining acceptance gates.

## Completed source checkpoint

Added source-derived BarFullscreenState.qml (bar-fullscreen-input-v1), a
nonvisual QtObject, and bound the real surface to its output-local observation
and mask selection. One shared instance enables read refresh; passive output
instances own no repeated query. Vendor parents/model/notices and unrelated seals
remain unchanged; only TrialPanel's authored seal changes and one new original
Bar.qml derivation is admitted. Existing bar/input geometry and reservation stay.

Six new source/model contracts and four actual-owner fake-service cases pass.
Full units: 1,484, work/plan-142-units-final.log. Contained suites: frame 28,
audio 32, tray 5, network 7, tooltip 8, clock 5 and desktop compile all passed.
Final reports dated 20261122T130059; clean-source passed at
work/clean-source/20261122T130059.921312Z/report.json. All 136 sealed runtime
sources, generated mirrors, whitespace and thirteen prestate records verified.
Backups: work/backups/plan-142-20261122T125116329132Z/.
Private summary: work/fullscreen-bar-input-142/verification.json.

Retained initial failures: isolated source-copy tests lacked the new derived
mirror; their source list was extended without weakening integrity assertions.
A stale drag-mask assertion was updated to the stronger suppression-first route.
The first Qt case exposed a graphical Item outside a scene; the genuinely
nonvisual owner is now a QtObject instead of allowing the warning. A fixture's
immediate post-destroy assertion incorrectly assumed synchronous QML destruction;
it now explicitly disables refresh before deferred destruction and tests disabled
ownership, not a fabricated destruction-timing guarantee. Failed reports remain
at work/frame-port/20261122T125611.942199Z/report.json and
work/frame-port/20261122T125826.509900Z/report.json.

No host compositor/audio query/dispatch, native fullscreen transition,
installed-path/PID check, deployment/reload/restart, configuration, package,
service/agent/security/session action, commit or publication occurred. Plan 135
remains the last verified installation, with Plans 136–142 source-only. Native
click-through/remap/pointer/grab/focus/pixel/security acceptance, full visual
fullscreen/peek/reveal, popup policy and remaining A–E work remain open.
