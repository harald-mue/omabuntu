# Device-free headless backend diagnosis

## Goal and evidence

Explain the failed disposable compositor startup before attempting any further
popup reproduction. Compare the Plan 166 crash report, official Hyprland 0.57.0
source at `0aa6745f705f2c4b0a5004eb019ef76e5bbdb426` and Aquamarine 0.15.1 backend
allocator selection. Popup provenance remains Omarchy
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; this request does not modify it.

## Gap and proposed shape

The prior launcher assumed HYPRLAND_HEADLESS_ONLY and Mesa software rendering
were sufficient. Trace actual environment handling and the missing allocator.
Check whether an existing device-free path is supported; otherwise identify a
suitable alternative compositor without installing it or weakening isolation.

## Safety and exclusions

Read-only installed package metadata/source diagnosis and private upstream
research under ignored work/. No GPU/input-device exposure, live sockets, bus,
packages, additional compositor launch, desktop/service/configuration changes,
popup fix or commit. Do not mistake a compositor abort for the Quickshell fault.

## Tasks

- [x] Trace the crash-report backend failure and pinned source selection.
- [x] Determine device-free support and document a bounded alternative.
- [x] Record findings and run repository unit tests.

## Findings and decision

The retained crash report contains the missing detailed backend log: DRM found
no GPUs, the nested Wayland backend could not connect, and startup ended with
`Cannot open backend: no allocator available`. This is expected given the
intentional absence of both devices and host compositor sockets.

Official Aquamarine v0.15.1 `src/backend/Backend.cpp` lines 162–178 constructs its
primary allocator only from a backend supplying a DRM fd, using CGBMAllocator.
Its headless backend supplies -1 for both DRM fd methods and reuses the primary
allocator for output swapchains. The only startup exception is AQ_BACKEND_NULL;
Hyprland 0.57.0 does not select that backend and it would not establish the
required graphical popup test. This is not a missing Lua monitor setting or
something LIBGL_ALWAYS_SOFTWARE/GALLIUM_DRIVER can supply.

Pinned Hyprland initialization always requests mandatory headless, optional DRM
and fallback Wayland backends. HYPRLAND_HEADLESS_ONLY is present in the upstream
tester launcher but is not handled by the reviewed initialization/main code;
the string is also absent from the installed Hyprland/Aquamarine binaries.
The earlier assumption that this variable enabled a device-free renderer was
incorrect. Do not retry by exposing render nodes or live session sockets.

Labwc is a candidate alternative based on wlroots, with a headless/Pixman test
path to verify against the selected package's source and protocols before use.
Cached Ubuntu metadata lists Labwc 0.9.3-1 and wlroots 0.19.2-1 as not installed.
Versioned official Labwc documentation is retained privately. Actual renderer,
layer-shell, virtual-pointer and package dependency suitability remain gated
preflight work, not established functional acceptance. Recommend a read-only
package dependency simulation followed by explicit approval before any package
installation. Do not assume Weston is a drop-in layer-shell test compositor.

All 1,640 unit tests pass. Private source evidence and test output are under
`work/headless-backend-167/`; original compositor logs remain under the Plan 166
private evidence directory. No further compositor was launched. No device,
socket, settings, services, runtime code or installed packages were changed.
The original Quickshell fault remains unreproduced and unattributed.
