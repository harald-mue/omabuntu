# Original notification native pointer and focus checkpoint (Plan 179)

## Bounded evidence

`tools/check_native_input.py` runs the sealed original Omarchy notification
closure at `ac2690cd7be4f47e4a255f5e2e78d904d436b068` on the verified exclusive
Quickshell runtime, with Plan 177's private Labwc/Pixman/SHM and Qt OpenGL/llvmpipe
lab. It retains every staged notification byte, including native surfaces,
input regions, hover handlers, cards and shaders. No production source was edited.

A separate test root adds an owned fullscreen **native FloatingWindow**, which
counts real click and A-key events. That window and the original notification
surfaces are separate native windows in the same fixture Quickshell process,
not a real external application. The one output is verified as 1280 × 720.

Six checks pass:

1. With original overlay surfaces mapped but idle, a click inside the overlay's
   transparent right strip reaches the background. A native A key also arrives.
2. With a card present, another click in that strip **outside the deck** reaches
   the background. Moving onto the original low-urgency card expands it and
   holds it past its normal 5-second lifetime. Moving away collapses it and
   automatic expiry resumes without an IPC dismissal.
3. Moving onto a two-card original grouped deck expands it; leaving collapses it.
4. A native right click inside a card dismisses it without a background click.
5. A native left click invokes exactly one matching standard `default` action
   signal on the private bus, without leaking the click to the background.
   A private observer receives the signal; no application/URL is launched.
6. After native background focus, original exclusive keyboard mode prevents an
   injected A from reaching that window. Native Escape exits original mode;
   the next native A reaches the background **without any refocus click or direct
   handler call**. Final background focus is true; the expected A count is two,
   with three background clicks and no card-click leakage.

The earlier Plan 178 device-free native card/keyboard evidence remains separate
and its checker is unchanged. This probe reuses its exact test-driver bootstrap
with an explicit marker check and records that dependency's hash; it does not
transform the actual Service/Toast. All evidence is fixture-specific, not a broad
input/focus or original-desktop acceptance verdict.

## Pointer transport and containment

`tools/native_pointer_fixture.py` is an independent Python standard-library
implementation of the required Wayland wire requests: registry, sync, v1 virtual
pointer binding, absolute motion, button, frame and destroy. No protocol XML,
generated upstream code or new dependency was imported. A persistent owned socket
keeps the virtual device alive through hover and key tests. Its address is fixed
to the disposable `/home/probe/runtime/wayland-N` namespace; ordinary host runtime
paths, symlinked/missing socket endpoints, multi-output mode and out-of-range
coordinates refuse. This guard is not a security boundary against arbitrary
same-user code; the runner's isolated namespace is the host-exclusion boundary.

The first native attempt failed before any input checks: a skipped Wayland client
object ID produced `not a valid new object id (4)`. Correcting allocation to start
at the next contiguous ID fixed the test-only transport. The failed report,
original helper bytes and compositor logs remain private. No original service,
input region, shader, compositor policy or containment setting was weakened.

The runner is plan-only by default:

```sh
python3 tools/check_native_input.py
python3 tools/check_native_input.py --run \
  --lab-dir work/<verified-private-lab> \
  --candidate work/notification-runtime-builds/<verified-variant>
```

It rechecks the private package tree, runtime eligibility and sealed source
closure. No downloads, build, system installation or release selection occur.
The reviewed Bubblewrap graphics namespace excludes host buses, sockets, homes,
GPU/input devices and inherited display/Hyprland identity. The fresh private bus
has no activation directories. Activation helpers/Xwayland remain guarded.
Synthetic notices and input are fixed; no clipboard, live DND or user contents
are collected. The pointer connection is closed and all owned processes reaped.
Inputs stay unchanged, renderer/allocator checks pass, and only the exact
absent-Hyprland warning is accepted. Three synthetic native captures plus hashes,
commands, failures and final event counters remain only under ignored work/.

Bounds apply to disposable diagnostics only: a 35-second fixture watchdog,
55-second outer deadline and bounded command/socket readiness. Normal desktop
components gain no timeout, autostart or crash-supervision policy.

## Verification and exclusions

Fourteen new synthetic wire/guard/fixture regressions run without real sockets,
compositors or input. The full unit suite passes 1,746 tests. All nine clean-source export checks pass; no original private
lab/runtime/images are required for those source tests. Four existing document
backups verify by hash/mode, and the final native checker/pointer/unchanged
bootstrap hashes match their successful receipts.

Plan 180's subsequent [cross-process fixture](notification-native-processes.md)
now verifies separate native application focus handoff and persistent sender
callbacks, replacement and sender exit with the original service unchanged.
Its synthetic sender explicitly filters foreign broadcast action IDs; this is
not confidential delivery or acceptance of production applications.

Still not accepted:

- Multi-output input, scaling/hotplug, scrolling/dragging, rounded-corner input
  precision and every possible original action/hover/deck interaction.
- Cross-process real-application callbacks, focus/launch, or application lifecycle.
- Hyprland focused-output/window/fullscreen/direct-scanout or focus policy.
- Clipboard/code-copy secrecy, locked-session privacy, native security/recovery
  acceptance, pixel identity and crash causality.
- Artifact-bound live host admission and reviewed reversible SwayNC migration.

SwayNC, the installed shell, live compositor and debug capture were neither
inspected nor changed. Current debugger liveness is not inferred. No commit or
publication occurred; any live provider/shell change still needs separate approval.
