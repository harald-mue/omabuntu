# Quickshell runtime investigation

## Decision status

**Built and staged with warnings; not installed or desktop-accepted.**
The development target's approved 96 dependencies are verified installed, and
both pinned source builds completed in Bubblewrap. The separately approved
spirv-tools dependency is installed, and a clean rebuild produced both shader
outputs without optimizer failures. See the [current build state](../docs/runtime-build.md).
Isolated linkage and 28 module probes (24 representative nullable types) now pass;
see [runtime-check limits](../docs/runtime-check.md). This is not a full shell or
live service test. Other targets still require independent approval.
The [machine-readable plan](quickshell-plan.json) and
[simulation summary](../docs/package-plan.md) define the current candidate.
No additional package source was added. Prefer existing Ubuntu Qt over a
parallel Qt installation.
Do not treat a generic upstream binary as proven equivalent to the source package.

## Reproducible source candidate

- Upstream: https://github.com/quickshell-mirror/quickshell
- Source-reference package: 0.3.2.r7.g2b4501a-1
- Resolved upstream commit: `2b4501a282689792b62e94f3fb30d8f512324fe6`
- Upstream release observed during investigation: v0.3.2, with no attached binaries.
- License: LGPL-3.0-only according to the source package metadata and upstream
  license text. Distribution requires separate license/source compliance.
- The matching original package recipe, patch, hook and build flags are now
  recorded in [packaging metadata](../upstream/quickshell-packaging.json) and the
  [shell audit](../docs/shell-audit.md). The QtQuick 6.11 patch is intentionally
  not applied to Ubuntu Qt 6.10.2; no original-binary equivalence is claimed.

Do not build from a moving branch. The candidate commit matches the package's
version suffix, but that alone does not establish equivalence to its packaged build.

## Qt compatibility

The pinned root CMake file declares a Qt 6.6 baseline. It explicitly handles
private dependency discovery for Qt 6.9 and later. The target has Qt Core/QML/
Quick 6.10.2 runtime packages installed.

This removes the assumption that Qt 6.12 must be installed just because the
reference machine used it. It does **not** prove that the entire Omarchy QML
shell uses only APIs available in Qt 6.10, or that every shell feature will work. The pinned runtime now builds with Qt
6.10.2, but the complete Omarchy shell has not been loaded.

Required build components include Qt Gui/Qml/Quick/QuickControls2/Widgets/
ShaderTools, Qt Quick private headers, and Wayland client/private headers.
Additional runtime QML modules must be derived from actual shell loading paths.

## Feature requirements

Build capability and runtime activation are separate. The runtime must support:

- Wayland layer shell and Hyprland IPC/global shortcuts.
- System tray, PipeWire, MPRIS, UPower, notifications.
- Network and Bluetooth.
- PAM and Polkit for eventual reviewed integrations.
- Session lock only for later approved security acceptance.

Do not start the full shell inside GNOME just to test whether it loads.
Do not enable lock/idle timers as part of a build test.

## Candidate Ubuntu build dependencies

Locally available candidates were observed for:

- `qt6-base-dev`, `qt6-base-private-dev`
- `qt6-declarative-dev`, `qt6-declarative-private-dev`
- `qt6-wayland-dev`, `qt6-wayland-private-dev`
- `qt6-shadertools-dev`, `spirv-tools` (required for the shader optimizer)
- GBM/EGL/Vulkan and GLib development requirements identified in the full CMake audit
- `libcli11-dev`, `libjemalloc-dev`, `libpipewire-0.3-dev`
- `libpam0g-dev`, `libpolkit-agent-1-dev`
- `libdrm-dev`, `libwayland-dev`, `wayland-protocols`
- `cmake`, `ninja-build`, `g++`, `pkgconf`

This is an investigation list, **not an installation command or a complete
dependency closure**. Some items are already installed. Development packages
for PAM do not authorize changing PAM configuration.
Candidate names such as `qt6-wayland-dev-tools` and `libqt6svg6-dev` had no
candidate; do not assume cross-release package names. The Ubuntu SVG development
package is `qt6-svg-dev`, available in local metadata. Upstream Quickshell does
not directly require its development headers in the reviewed CMake files;
SVG runtime support is requested through `qt6-svg-plugins`. QML candidates are
mapped explicitly in the manifest; optional Owe/SDDM paths are not included.
Existing package sources and transitive dependency changes still need review.

## Important build blocker: crash handler

The default crash handler requires cpptrace. No `libcpptrace-dev` package entry
was returned by the local APT query. The pinned source can vendor cpptrace
v1.0.4 using CMake FetchContent, which may download code during configuration.

An approved recipe must choose explicitly between:

1. Separately packaged, pinned cpptrace with required libunwind support.
2. An approved, pre-fetched pinned dependency with network fetching disabled.
3. Explicitly disabling the optional crash handler for a limited evaluation,
   documenting lost diagnostics and re-evaluating crash/restart behavior.

The current preferred proposal is a separately built pinned cpptrace using
Ubuntu libunwind/libdwarf, with external dependencies and no implicit fetching.
It preserves the crash handler. This strategy was approved and compiled on the
development target, including Quickshell's signal-safe-unwind configure probe.
Do not silently enable downloads, skip the cpptrace usability check, or claim
a crash-handler-disabled build is safety-accepted.

## Proposed build process after approval

1. Finalize dependency closure and simulate APT changes without applying them.
2. Approve exact sources, packages, optional build flags, and maintenance policy.
3. Fetch pinned source/dependencies into a private build workspace.
4. Package/stage files without writing into system or active user configuration.
5. Verify linkage, Qt modules, feature flags, and harmless isolated QML probes.
6. Test an audited shell profile only in an agreed Hyprland context.
7. Keep package installation and desktop activation as separate approved actions.

A project build should produce a managed artifact with provenance, update, and
uninstall instructions, not an unmanaged sudo cmake install.
