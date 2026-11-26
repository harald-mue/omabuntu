# Native notification test environment: preflight and graphics checkpoint

## Original native notification checkpoint (Plan 178)

The subsequent [original-service native fixture](notification-native-probe.md)
passes on one and two outputs using this unchanged private lab. It retains the
sealed Service/Toast/native surfaces, real NotificationServer and original IPC;
synthetic Notify, grouping/replacement/expiry, private DND, original photo masking,
symbolic/raw icon controls, actual virtual-keyboard Escape/Return and the native
standard action signal pass. Plan 179's subsequent
[single-output pointer/focus fixture](notification-native-input.md) additionally
proves native hover/hold, click-through, card clicks and handoff to an owned native
background window. Multi-output pointer behavior, real external application focus,
Hyprland policy, clipboard/locked privacy and live migration remain open.
No additional dependencies or host-session operations were needed. Earlier
graphics-only evidence and original read-only preflight are retained below.

## Isolated graphics checkpoint (Plan 177)

The owner separately approved download/hash verification of the nine exact Ubuntu
packages, private extraction under ignored work/ and a disposable graphics smoke
test. That checkpoint now **passes on one and two headless outputs**:

- All nine package files match their exact cached Ubuntu package metadata hashes
  and sizes. Archive paths/types, internal symlinks, nonprivileged file modes and
  all package copyright notices were checked. No dpkg registration, maintainer
  script, system package transaction, update or additional package source ran.
- Contained linkage checks resolve the intended private wlroots/liftoff/sfdo/XCB
  libraries, with no missing dependency for the five diagnostic executables.
- Actual Labwc logs confirm headless, Pixman and the shared-memory allocator.
  Private wayland-info confirms the expected one/two HEADLESS outputs and
  layer-shell, screencopy, virtual-pointer, virtual-keyboard and wl_shm globals.
- Actual Qt logs confirm OpenGL 4.5 and Mesa llvmpipe, not the Qt 2D software
  adaptation. Native PanelWindow instances map through layer-shell on both outputs.
- Six native compositor screenshots pass positive/negative controls for original-
  style brightness-plus-colorization, a raw color control and a rounded alpha mask.
  Original Toast uses these MultiEffect operations; this fixture is a graphics
  control, **not** a substitute notification UI or an original-toast acceptance test.
- Namespace assertions exclude host runtime/config/device paths and inherited
  display/Hyprland state. Activation-environment updates are disabled. Private
  execution sentinels for Xwayland/systemctl/D-Bus activation were not triggered.
  Inputs stayed unchanged and every owned child was reaped.

The first package-preparation attempt rejected Ubuntu's legitimate `libl` pool
subdirectory before any download; the corrected path validator accepts bounded
pool prefixes. The first rendering attempt proved native graphics but failed its
pixel expectation: pure colorization preserves source luminance (red became dark
green), rather than producing full-intensity green. Its logs/captures are retained.
The subsequent positive control uses brightness=1 and colorization=1, like the
original monochrome Toast path; the negative control sets both to zero. Missing
colorization, raw painting or missing masking cannot satisfy the sampled controls.

`tools/check_native_graphics.py` is plan-only by default. Explicit --run requires
the prepared private lab and the current verified exclusive runtime artifact.
It never downloads dependencies, installs/selects a release, starts notifications,
connects to a host bus or changes the desktop. The approved disposable diagnostic
has bounded readiness/action/overall deadlines; normal components gain no timeout.
Exact manifests, commands, checker hashes, library/renderer logs, failures and
synthetic captures remain private under work/native-graphics-177/ and
work/native-graphics-probes/. Eleven new fixture/guard/pixel-refusal regressions,
all 1,715 unit tests and all nine clean-source checks pass. Before-state document
backup hashes/modes and whitespace checks verify.

**Scope at this checkpoint:** generic graphics only, not actual original
notification cards or input. Plan 178 above subsequently closes a bounded subset
using the unchanged service and genuine keyboard dispatch, not protocol
advertisement alone. Pointer/hover/click-through were excluded from that
checkpoint; Plan 179's bounded follow-up is linked above. Hyprland routing/focus/
fullscreen, clipboard/locked-session privacy, live migration and crash causality
remain excluded. No SwayNC, installed shell, live compositor or GDB was touched.

## Read-only decision and limits at Plan 176

Plan 176 identifies **Labwc 0.9.3 with wlroots 0.19.2**, explicitly selecting its
headless backend and Pixman compositor renderer, as the smallest reviewed
candidate path. This is a source/dependency preflight, **not a successful native
compositor run or notification acceptance**. No packages or binaries were
installed, no compositor/client was launched, and no host session, device,
notification bus or crash capture was accessed or changed.

The existing alternatives do not close this gap: offscreen cannot construct a
PanelWindow backend, and the reviewed Hyprland 0.57.0/Aquamarine 0.15.1 headless
path still needs a DRM/GBM allocator. Exposing a render node or the live Wayland
socket is not an allowed fallback. Labwc is a test compositor, not a replacement
for the user's desktop or the project's Hyprland target.

## Version-matched evidence

- Labwc release 0.9.3 resolves to upstream commit
  `a98fd8f9742ef7621c8b479353409fd06b82cf75`. Its server, layer-shell, seat,
  session-environment and license witnesses match the corresponding Ubuntu
  original source archive byte-for-byte.
- wlroots 0.19.2's renderer selection, allocator, headless backend and backend
  build witnesses match the official upstream release sources byte-for-byte.
  Headless advertises shared-memory/data-pointer buffer support. Explicit
  `WLR_RENDERER=pixman` avoids the GLES/Vulkan DRM-fd branches, and allocator
  autocreation can select the shared-memory allocator without a DRM fd.
- The distro's `backends=drm,libinput,x11` build option does **not** remove headless:
  `backend/meson.build` includes headless/Wayland/multi unconditionally. This is
  different from runtime backend selection, which must be explicitly headless.
- Labwc creates layer-shell, screencopy and virtual pointer/keyboard globals.
  Its security-context filter is relevant: actual advertised globals must be
  checked on the future private socket. Do not alter host or compositor security
  policy to bypass a missing protocol. Only owned fixture clients may connect to
  this new test compositor; it has no host clients, devices or session access.
- The Ubuntu wlroots source overlay contains a layer-shell validation revert
  concerning zero dimensions without anchors. The original notification surface
  anchors top/bottom/right and has explicit width; nevertheless this distro patch
  must stay visible in test provenance. Labwc's source overlay has no patch series.
- Source archives and distro overlays were fetched from the official Ubuntu
  archive and checked against SHA-256/size in their HTTPS-fetched DSC files.
  DSC signatures were **not independently verified** in this preflight. This is
  research evidence, not authorization to execute a downloaded binary. Labwc is
  GPL-2; wlroots is MIT with per-file notices. No compositor code is imported into
  the MIT project or its existing release.

Primary references:

- [Labwc 0.9.3 server](https://github.com/labwc/labwc/blob/a98fd8f9742ef7621c8b479353409fd06b82cf75/src/server.c),
  [layers](https://github.com/labwc/labwc/blob/a98fd8f9742ef7621c8b479353409fd06b82cf75/src/layers.c),
  [seat](https://github.com/labwc/labwc/blob/a98fd8f9742ef7621c8b479353409fd06b82cf75/src/seat.c),
  [session handling](https://github.com/labwc/labwc/blob/a98fd8f9742ef7621c8b479353409fd06b82cf75/src/config/session.c).
- [wlroots 0.19.2 renderer](https://gitlab.freedesktop.org/wlroots/wlroots/-/blob/0.19.2/render/wlr_renderer.c),
  [allocator](https://gitlab.freedesktop.org/wlroots/wlroots/-/blob/0.19.2/render/allocator/allocator.c),
  [headless](https://gitlab.freedesktop.org/wlroots/wlroots/-/blob/0.19.2/backend/headless/backend.c),
  [backend build](https://gitlab.freedesktop.org/wlroots/wlroots/-/blob/0.19.2/backend/meson.build).

Private source origins, hashes, downloaded research, dependency simulations and
partial failures are retained under ignored `work/notification-preflight-176/`.
The initial missing COPYING/Qt source paths and unavailable cached source-index
entries are recorded, not treated as successful collection. Correct LICENSE/source
paths and official binary-package metadata were used instead.

## Two separate rendering decisions

Pixman is the **compositor** renderer. It does not require selecting Qt Quick's
software adaptation for the **client**.

The original Toast uses MultiEffect for icon tinting and photo masking. Qt Quick's
software adaptation cannot render ShaderEffect; ignoring those effects or only
testing text-only cards would not establish original visual fidelity. The Qt
6.10 documentation currently describes patch release 6.10.3; the version-pinned
Qt 6.10.2 MultiEffect source also explicitly uses ShaderEffect/ShaderEffectSource.
The former offscreen checks remain model/card checks with this rendering limit.

For the meaningful native rendering trial, propose the existing Mesa 26.0.8
Wayland software-EGL path with llvmpipe, while Labwc stays on Pixman. Mesa's
version-matched `dri2_initialize_wayland_swrast` uses the private Wayland `wl_shm`
path and is selected by ForceSoftware. A candidate client environment is:

- `QT_QPA_PLATFORM=wayland`, using **only** the new private socket.
- Remove the existing sandbox's `QT_QUICK_BACKEND=software` override.
- `QSG_RHI_BACKEND=opengl`, `QT_WAYLAND_CLIENT_BUFFER_INTEGRATION=wayland-egl`.
- `LIBGL_ALWAYS_SOFTWARE=1`, `GALLIUM_DRIVER=llvmpipe`.

These are design inputs, **not applied configuration or a proven graphics
context**. First prove the actual Qt OpenGL/software-driver context and an
unmodified MultiEffect/icon-mask control in the future device-free namespace.
Fail if that path needs a render node, cannot initialize or omits effects; do not
fall back silently to Qt's 2D software adaptation and label the image accepted.

References:

- [Qt 6.10 software adaptation](https://doc.qt.io/qt-6.10/qtquick-visualcanvas-adaptations-software.html).
- [Qt 6.10 MultiEffect](https://doc.qt.io/qt-6.10/qml-qtquick-effects-multieffect.html),
  [exact Qt 6.10.2 implementation](https://github.com/qt/qtdeclarative/blob/v6.10.2/src/effects/qquickmultieffect.cpp).
- [Mesa 26.0.8 Wayland EGL](https://gitlab.freedesktop.org/mesa/mesa/-/blob/mesa-26.0.8/src/egl/drivers/dri2/platform_wayland.c).

## Dependency choices, not installation approval

Cached binary-package metadata gives Labwc 0.9.3-1 and libwlroots-0.19 0.19.2-1.
There is no installed suitable alternative compositor in the inspected command
set. The existing Qt Wayland/Mesa libraries are present, but that is not proof of
native initialization in containment.

A no-recommends APT **simulation** resolves:

| Purpose | Additional packages |
| --- | --- |
| Minimal compositor | labwc, libwlroots-0.19, libliftoff0, libsfdo0, libxcb-ewmh2 (5 total) |
| Output/protocol inspection and native capture | wayland-utils, grim (7 total) |
| Virtual pointer plus explicit keyboard sequences | wlrctl, wtype (9 total) |

The cached simulation proposes no upgrades or removals. This is not a current
installation guarantee and is not approval to install. Suggested desktop
components such as panels, another notifier, idle handling or wallpaper helpers
are not required or admitted. No autoremove or APT update is proposed. The first
simulation with --no-download exited 100 because archives were not cached; the
subsequent --simulate-only solver completed without downloading anything.

**Preferred next request:** approve download of the exact reviewed Ubuntu package
files, hash verification against package metadata and extraction only into a
private ignored work prefix, followed by the disposable isolated smoke tests.
Do not register them with dpkg, run maintainer scripts, add sources or touch the
system installation. Validate extraction paths and dynamic-library resolution
before execution. This avoids a privileged system package transaction; it is
still an explicit dependency-preparation/test-execution approval gate.

The helpers are candidates, not proven input automation: persistent virtual
pointer/keyboard ownership and actual event delivery must be verified before
claiming hover, drag or keyboard behavior. A long-lived fixture input client may
be needed. Readiness/screenshot tools alone do not prove input dispatch.

## Proposed disposable test order and containment

After separate approval, not during this preflight:

1. Verify the downloaded package hashes/licenses, private extracted tree and
   exclusive runtime's existing build/bus eligibility. Mount all such inputs
   read-only; keep only new test output/home writable.
2. Use Bubblewrap user/PID/network isolation with a fresh private /tmp, minimal
   /dev (no GPU/input/DRM nodes), private runtime/config/data/cache/state directories
   and synthetic passwd/group. No /run/user, host /tmp, session sockets, homes,
   system/session buses or host Hyprland signature enter the namespace. No X11
   clients/session are used. Ensure Xwayland cannot start as a side effect.
3. Clear inherited environment, use an explicit empty Labwc config/script search
   path, and set `LABWC_UPDATE_ACTIVATION_ENV=0` to avoid D-Bus/systemd activation
   environment commands on startup **and shutdown**. Set `WLR_BACKENDS=headless`,
   `WLR_RENDERER=pixman`, initially one and then two `WLR_HEADLESS_OUTPUTS`.
   Do not read host autostart/environment/shutdown/menu scripts or themes.
4. First prove compositor startup, output/global advertisement, a native
   PanelWindow and the Qt llvmpipe shader control, all on the private socket. Give
   each readiness/action a bounded diagnostic deadline; no normal desktop
   component gets a timer-based lifetime or autostart policy.
5. Start a separate private D-Bus with no service-activation directories and no
   system bus. Run the existing verified exclusive runtime against the actual
   staged original Service/Toast and test-only state. Do not remove the Variants,
   PanelWindow, input region, masks or shader blocks. Original native surfaces
   must be the ones rendered, not an authored replacement toast. Only fixture
   notifications are sent on this private bus.
6. Capture synthetic-only output; validate icons/photo masks, grouped decks,
   replacement/expiry, native input-region click-through to an owned background
   fixture, hover pause and explicit keyboard focus/release. Exercise standard
   sender-action callbacks without launching real apps or URLs. Clipboard/privacy
   and locked-session tests need their own reviewed fixtures; do not invoke host
   clipboard tools or session locks.
7. Reap only owned test children and verify inputs stayed unchanged. Keep logs,
   failures and synthetic captures private. Never signal the live shell, GDB,
   SwayNC, compositor or user services. Do not install or select the review release.

## Acceptance exclusions that Labwc cannot close

The unmodified notification service imports Quickshell.Hyprland. In the pinned
runtime, an unset Hyprland signature yields an explicit unavailable-IPC warning
and no host connection. Original source falls back to the first actual output
and returns no fullscreen step-aside when there is no Hyprland workspace.
Treat only that exact absent-IPC warning as expected, not general QML/runtime
errors; do not fake live Hyprland state to claim native acceptance.

Labwc cannot establish Hyprland focused-monitor selection, real window-address
routing, fullscreen/direct-scanout transitions or Hyprland-specific focus policy.
Those require a suitable separately approved Hyprland test environment or later
explicit live acceptance with recovery. Multiple Labwc output surfaces are not
proof of Hyprland focus routing. Even a successful native Labwc run would not
establish pixel identity to upstream screenshots, locked-session secrecy, broad
security acceptance, crash causality or readiness for an automatic provider swap.
SwayNC migration/rollback and artifact-bound live host admission remain separate.
