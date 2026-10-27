# Isolated runtime checks

## Result and scope

The pinned workspace runtime passed **32 sandboxed checks** on the development
target using Ubuntu Qt 6.10.2:

- Sandbox startup, ELF inspection, and ldd -r relocation/dependency resolution.
- 28 positive module probes: 19 Quickshell modules and 9 Ubuntu Qt QML modules.
- One negative control for a deliberately nonexistent import.

24 positive probes also resolve a representative type through a nullable typed
property. This is stronger than merely finding a qmldir file or importing an
optional-plugin module without using its type information. The property remains
null: it does not construct the representative object or invoke its services.
Quickshell.Wayland, Quickshell.Hyprland, Quickshell.I3, and
Quickshell.Services.Greetd remain explicitly **import-only** probes.

All positive probes completed normally with the expected marker and
Configuration Loaded. None logged a WARN/ERROR/FATAL/CRITICAL diagnostic.
The negative control exited with the expected code 255 and the specific missing
module error, without printing the success marker. A timeout, crash, unrelated
error, or successful exit is not accepted as a passing negative control.

Private final evidence: work/runtime-check/20261024T082502.926718Z/report.json.
Commands, source/log hashes, resolved types, diagnostic lines, and individual
results are recorded there. Earlier exploratory reports remain intact.

The ELF RUNPATH is $ORIGIN:$ORIGIN/../lib, not an absolute build/staging path.
ldd -r found no missing libraries or unresolved relocation symbols. This covers
the executable's linked dependencies, not every possible future dlopen path.
The complete staged artifact manifest remained unchanged after the probes.

## Reproduce after target-specific approval

```sh
# Plan only: no subprocesses, QML execution, or report directories.
python3 tools/check_runtime.py

# Choose a verified completed build in this project's ignored workspace.
python3 tools/check_runtime.py --run --build-dir work/builds/<timestamp>
```

The checker does not select the latest directory automatically. It verifies the
source lock, original successful sandbox steps, and exact staged file hashes/link
targets. If the original report has a post-build assessment failure, a matching
successful reassessment and the original report hash are required. Modified or
unrecorded artifacts and out-of-workspace build directories are refused.
These local records provide traceability, not signed supply-chain attestation.

No arbitrary QML input or user-selected import is accepted. Probe content comes
from fixed module/type allowlists in tools/check_runtime.py. Each subprocess has
a 20-second timeout. A failed preflight or baseline stops the checks without an
uncontained fallback; individual later failures remain visible in the report.

## Containment

Bubblewrap provides private network, PID, and filesystem namespaces. It exposes
installed /usr tools/libraries and a minimal loader/alternatives view read-only.
The staged runtime is mounted read-only at its logical /opt/omabuntu-runtime
prefix. This mount exists only inside the namespace; nothing is installed in the
host /opt tree. Synthetic QML and font configuration are also read-only.

The only host-backed writable bind is each case's private project-local HOME.
HOME/XDG paths and environment are replaced, not inherited. Host home/session
sockets, /run, real D-Bus endpoints, displays, compositor signatures, and GPU
devices are not exposed. Bus endpoints explicitly point to nonexistent paths to
prevent ordinary autolaunch. No private or host D-Bus daemon is started.
Qt uses the offscreen platform and software Quick backend.

A minimal nonvisual ShellRoot is instantiated, prints a completion marker, and
quits on the event loop. It is not a bar, launcher, full Omarchy shell, or window.
Quickshell creates disposable internal IPC/log/state files in the private HOME;
these are not host desktop agents or services. NotificationServer, PolkitAgent,
PamContext, Process, Window, and similar representative types are resolved only
as nullable property types, never instantiated by the probes.

QS_DISABLE_CRASH_HANDLER=1 prevents debugger/relaunch handling during these
short-lived diagnostics. It does not alter the compiled runtime or disable
existing host security features. Crash/restart behavior remains untested.
Namespace containment is not a VM or a general proof against kernel exploits.

## Interpretation of remaining build warnings

The passing imports and representative types provide bounded evidence against
immediate plugin-registration/linkage failures in these paths. They do not turn
all 21 CMake QML-link-target diagnostics into universally harmless warnings.
Import tracing includes DEBUG messages about trying dynamic-plugin paths before
other resolution paths; in these passing probes they did not prevent resolution.
They are not themselves proof that a required plugin is missing.

Compiler diagnostics (including missing returns and strict aliasing), two
Wayland XML validation warnings, and generated base-type/tooling-metadata
warnings remain unresolved. No upstream code or compiler flags were changed to
hide them. Passing type lookup does not repair generated tooling metadata or
exercise potentially unsafe C++ branches.

## Still not accepted

- Service singleton initialization, live D-Bus ownership, notifications, audio,
  network changes, Bluetooth, tray behavior, authentication, or Polkit flows.
- Real Wayland/Hyprland/I3/X11 connections, global shortcuts, layers, or protocols.
- Rendering, shader visual correctness, GPU behavior, or full shell API coverage.
- PAM conversations, lockscreen, idle/suspend, recovery, or security acceptance.
- Original binary equivalence and full shell local/dynamic import/Color behavior.
  The matching package recipe and marker semantics are now documented in the
  [shell/packaging audit](shell-audit.md); its QtQuick 6.11 patch is not applied.
- Runtime-only packaging, license/source compliance, system deployment, or release.

The [original shell/helper audit](shell-audit.md) now identifies automatic
services, privileged routes, and the matching Quickshell patch. Next, resolve
original-shell license/revision evidence and implement/test fail-closed loading
before planning an explicitly approved graphical trial. Keep active configuration,
service ownership, session changes, and authentication tests separately gated.
