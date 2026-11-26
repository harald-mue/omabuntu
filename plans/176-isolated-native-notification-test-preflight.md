# Isolated native notification test preflight

## Goal and compared evidence

Identify the smallest suitable isolated environment for the original notification
surfaces, without installing dependencies or connecting to the live desktop.
Compare Plans 165–167's offscreen and Hyprland/Aquamarine allocator findings,
Plan 174's actual native private-bus evidence, current locally available package
metadata, and version-appropriate official compositor/renderer/protocol sources.
Original UI remains Omarchy `ac2690cd7be4f47e4a255f5e2e78d904d436b068`;
Quickshell remains `2b4501a282689792b62e94f3fb30d8f512324fe6` with the separately
verified exclusive-registration patch. Native rendering/input acceptance remains
unproved until an actual isolated run is separately authorized and succeeds.

## Current gaps and proposed shape

Offscreen has no PanelWindow backend. The installed Hyprland/Aquamarine path
requires a DRM/GBM allocator even for its headless outputs. No host compositor
socket or GPU exposure may be used as a workaround. Recheck installed candidates,
inspect cached Labwc/wlroots package candidates and simulate dependencies without
APT updates, then verify headless/Pixman, layer-shell and relevant input/output
protocol support against exact official upstream versions. Distinguish basic
surface rendering from Hyprland-specific window routing and input acceptance.
Record a concrete isolated launch design and remaining approval/dependency gates;
do not start the compositor or tests in this preflight.

## Safety and exclusions

Read-only executable/package inspection and official source/documentation research;
private reports/downloaded research only under ignored work/. No package/source
installation, APT update, privileged action, host bus/Wayland/Hyprland sockets,
GPU/input devices, notification generation/history reads, DND setters, service or
desktop changes, crash-capture interruption, shell restart, configuration apply,
commit or publication. Do not execute downloaded code, change pinned runtime/UI
sources, patch away original surfaces or claim software rendering implies pixel,
input, security or native Hyprland acceptance. Source/reference material remains
outside tracked files; record hashes and origin for evidence only.

## Tasks

- [x] Record current candidates and prior isolation/backend constraints.
- [x] Inspect cached candidate/dependency simulation without installation or updates.
- [x] Verify version-matched official renderer/protocol and native UI requirements.
- [x] Specify bounded isolated probe design, exclusions and explicit approval gates.
- [x] Record recommendation and verify repository tests/whitespace.

## Findings and recommendation

The reviewed test candidate is Labwc 0.9.3 (upstream commit
`a98fd8f9742ef7621c8b479353409fd06b82cf75`) with wlroots 0.19.2. Official release
witnesses match the Ubuntu original sources for renderer/allocator/headless,
backend build, layer-shell, seat and activation-environment handling. Explicit
headless + Pixman can select shared-memory buffers without a DRM allocator;
layer-shell, screencopy and virtual input exist in source. The distro wlroots
layer-shell validation revert is recorded as a fidelity difference, not hidden.
Actual binary protocol advertisement, rendering and event delivery remain untested.

Five packages suffice for the minimal compositor according to cached dependency
simulation; adding protocol inspection/capture makes seven, and virtual pointer/
explicit keyboard tools makes nine. No upgrades/removals are proposed by that
simulation. The --no-download simulation initially refused uncached archives;
--simulate-only then resolved dependencies without downloading or installing.
Source-index lookup returned warnings despite exit zero; exact source archives/
overlays were researched via official Ubuntu HTTPS DSC metadata instead. Source
SHA-256/size checks and upstream witness comparisons passed; DSC signatures were
not independently verified. Labwc GPL-2 and wlroots MIT notices are retained only
as private research; no upstream compositor code/assets are added to Git.

Important fidelity gate: original Toast uses MultiEffect. Qt's 2D software
adaptation ignores ShaderEffect, so it is not the visual acceptance renderer.
Keep the compositor on Pixman but separately prove a Qt OpenGL context using
Mesa software EGL/llvmpipe on the private Wayland shared-memory path. Exact Qt
6.10.2 MultiEffect source and Mesa 26.0.8 Wayland source support this proposed
path; an actual graphics-context/effect smoke test is still required. Do not
patch out effects or expose a render node to make it pass.

Recommend separate approval to download hash-verified Ubuntu package files,
extract only into a private ignored work prefix (no dpkg registration or scripts),
and execute bounded device-free compositor/graphics smoke tests. No system
installation is necessary as the preferred first attempt; extracted binary/library
resolution must still be verified. Explicit empty configuration/search paths and
LABWC_UPDATE_ACTIVATION_ENV=0 must prevent autostart/shutdown/session side effects.
The existing test sandbox's forced Qt software override must not carry into the
shader acceptance case. Full containment/test order and official source links
are documented in docs/notification-native-preflight.md.

Labwc cannot prove Hyprland focused-output, fullscreen/direct-scanout or window-
address routing behavior. Keep the actual service's absent-Hyprland fallback,
with an explicitly expected missing-IPC warning, rather than fake native Hyprland
acceptance. No private compositor/native notification was started in this request;
no live bus/device/clipboard/DND/history, desktop/provider, installed shell,
service, package, crash-capture, commit or publication change was performed.

Verification: all 1,704 unit tests and nine clean-source export checks pass.
Nine selected upstream/distro original source/license witnesses match. Backup
hash/mode for the affected existing document and tracked/new-file whitespace
checks pass. Private evidence, exact commands and partial failures remain under
work/notification-preflight-176/.
