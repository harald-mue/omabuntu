# Isolated compositor and shader smoke test

## Goal and evidence

Execute the explicitly approved Plan 176 next step: download nine exact Ubuntu
package files, verify/extract them only under ignored work/, then test a disposable
Labwc/headless/Pixman compositor with native Quickshell PanelWindow and Qt
OpenGL/llvmpipe shader controls. Compare Labwc 0.9.3 upstream commit
`a98fd8f9742ef7621c8b479353409fd06b82cf75`, wlroots 0.19.2 and the official
version-matched source witnesses already reviewed in Plan 176. Use the existing
artifact-verified exclusive Quickshell at
`2b4501a282689792b62e94f3fb30d8f512324fe6`. Original notification provenance
remains Omarchy `ac2690cd7be4f47e4a255f5e2e78d904d436b068`.

## Current gaps and proposed shape

The source/dependency preflight is positive, but neither native compositor nor
Qt software-EGL context/effects have run in the device-free namespace. Stage
only the nine exact packages resolved previously, verifying metadata, SHA-256,
archive paths/types, license notices and dynamic library resolution. Do not
register packages or execute maintainer scripts. Run bounded one/two-output
smoke probes in network/PID/user isolation with fresh home/config/runtime/state,
private compositor sockets, no host buses/devices and explicitly disabled
activation-environment updates. Test the native layer surface and MultiEffect
with positive/negative pixel controls; never count Qt's 2D software adaptation as
shader acceptance. Preserve failure logs rather than weakening containment.

## Safety and explicit exclusions

Only package extraction/downloads and disposable diagnostics are approved. No
system installation/update/source changes, privilege/security changes, host
/run/user or /tmp sockets, compositor/GPU/input nodes, live notification traffic,
clipboard/history/DND access, service activation, live shell/SwayNC/GDB restart,
installed release selection, commit or publication. Keep all third-party payloads
and synthetic captures private under work/. Back up changed existing project
files with hashes/modes. Bound diagnostics and reap only owned children; no timer
is added to normal desktop components. Prevent Xwayland and autostart/shutdown
scripts from starting. This is not original-notification behavior, Hyprland
routing/fullscreen, pixel identity, privacy, security or crash acceptance.

## Tasks

- [x] Verify exact package metadata; download, inspect and privately extract all nine packages.
- [x] Check licenses, contained dynamic-library resolution and immutable input manifests.
- [x] Prove isolated headless/Pixman readiness and actual protocol/output advertisement.
- [x] Exercise native PanelWindow and Qt OpenGL/llvmpipe MultiEffect controls.
- [x] Record failures/results, cleanup and remaining native notification gates.
- [x] Run unit/whitespace/backup checks and update documentation.

## Completed diagnostic scope

All nine exact package archives were verified against cached Ubuntu metadata,
inspected for paths/types/privileged modes, privately extracted without package
registration/scripts, and sealed with retained copyright notices. Contained
linkage resolves the intended private wlroots/liftoff/sfdo/XCB libraries and all
five diagnostic executables have no missing shared dependencies.

One- and two-output smoke cases pass. Actual logs show headless + Pixman + SHM
and Qt OpenGL 4.5 through Mesa llvmpipe. Protocol inspection confirms outputs,
layer-shell, screencopy, virtual input and wl_shm. Native PanelWindow instances
render six compositor screenshots with positive and negative controls for
brightness/colorization, a raw-color control and rounded alpha masking. These
are generic graphics controls, not replacement toasts or original notification
UI acceptance. Virtual protocol advertisement is not input dispatch acceptance.

The first preparation path validator rejected Ubuntu's valid four-character pool
prefix before download. The corrected validator retains bounded pool/path/hash
checks. The first rendering case exposed an incorrect expected color: pure
colorization preserves luminance. Its failure, screenshot and original checker
are retained. The corrected fixture uses the original Toast's monochrome
brightness=1 plus colorization=1 operation, with both disabled in the negative
control; expected full tint and mask samples now pass. A later completed run also
checks namespace exclusions, actual compositor allocator/renderer logs, exact
private library paths and bounded nonsymlink input witnesses.

Every owned child was reaped. Read-only input manifests remain unchanged;
Xwayland/systemctl/activation sentinels never triggered. No host bus/device/session,
notification traffic/history/clipboard/DND, installed shell/provider/GDB, package
installation, autostart or publication was touched. Private package preparation,
logs/manifests, failed attempts and synthetic captures remain under
work/native-graphics-177/ and work/native-graphics-probes/.

The actual original Service/Toast/native surfaces on a private synthetic bus,
input interactions, Hyprland policy, privacy and reversible live host admission
remain separate gates. See docs/notification-native-preflight.md.

Verification: eleven new fixture/guard/pixel-refusal tests, all 1,715 unit tests
and nine clean-source export checks pass. Tracked/new-file whitespace and the
hashes/modes of all three affected existing document backups verify. Final private
lab inputs and checker digest still match the successful run. None of the nine
lab packages is registered as installed in the host package database.
