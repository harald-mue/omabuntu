# Workspace runtime build

## Status and boundaries

The development target has the approved 96 dependency packages installed at their
expected versions. No pre-existing package version changed and none was removed.
The user subsequently approved and installed spirv-tools=2026.1-1. Verification
against the first post-install snapshot found exactly this one additional new
package, no changed existing versions, and no removals.
Before/after package and automatic/manual/held-mark evidence is private under
work/dependency-install/. APT added 36 manual marks, including explicit requests
that were previously automatic. Do not reset marks or remove packages broadly.

The pinned cpptrace and Quickshell sources compile and stage with Ubuntu
Qt 6.10.2. The current result is **staged with warnings**, not an installed or
desktop-accepted runtime.

## Reproduce after target-specific approval

```sh
# Plan only: no downloads, directories, or builds.
python3 tools/build_runtime.py

# Explicitly fetch verified sources if needed, build, and stage under work/.
python3 tools/build_runtime.py --build --jobs 4
```

Prerequisites include the approved compiler/Qt/native dependencies and an existing
working Bubblewrap installation, plus spirv-tools for spirv-opt. The builder
checks for the optimizer before allocating a build workspace. It never installs missing dependencies
and has no less-isolated fallback if Bubblewrap fails.

## Source provenance

[Source lock](../upstream/source-lock.json) pins full commits, archive URLs,
archive sizes, SHA-256 hashes, and source-root names. The initial root CMake files
matched previously inspected upstream sources. These hashes are recorded review
evidence, not upstream digital signatures or proof of distributor patch equivalence.

Source downloads happen outside the build sandbox and only from locked HTTPS URLs.
Cached bytes must match the lock. Archives are bounded, extracted with Python's
data filter, and rejected if they contain traversal, links, or special files.
This implementation requires Python 3.12 or later; Ubuntu 26.04 supplies a suitable
Python. No source snapshot scripts are executed.

## Build isolation and layout

Each explicit run creates a new private work/builds/<timestamp>/ directory.
Bubblewrap creates private namespaces, including network and PID namespaces.
It exposes installed tools/libraries read-only, a narrow /etc view, sources
read-only, and only project-local build/stage/home writable binds. Temporary
storage is private. Host home directories and session sockets are not mounted.

The build process cannot fetch missing CMake dependencies over the network.
FETCHCONTENT_FULLY_DISCONNECTED is also supplied, but is reported unused on
the no-vendoring paths; it is not the network isolation boundary.
This is namespace/filesystem containment, not a VM or a general proof against
host-kernel vulnerabilities in malicious native code.

The logical install prefix is /opt/omabuntu-runtime **inside the build layout**.
All CMake installation steps use DESTDIR=/stage in the sandbox. On the host,
everything is below the run's stage/ directory. No host /opt installation occurs.

cpptrace is staged first, then found by Quickshell from that staged prefix.
Quickshell QML metadata is explicitly staged using INSTALL_QML_PREFIX=lib/qt6/qml.
The qs alias retains its logical-prefix link; do not treat it as an active host
launcher or rewrite it into a user PATH.

Commands, logs, selected manifest, source lock, artifact hashes, and link targets
are recorded in the private report. This is a traceable repeatable build recipe,
not a claim of bit-identical binary reproducibility.
No distributable Debian package or release artifact has been produced.

## What passed

- Source archive checksums, safe extraction, and sandbox startup.
- cpptrace configure/build/staging using system libunwind and libdwarf.
- Quickshell's cpptrace signal-safe-unwind configure probe.
- Quickshell configure/build/staging with PAM, Polkit, session-lock, Hyprland,
  networking, Bluetooth, audio, notification, and other configured features enabled.
- Presence of 13 required staged QML module metadata files.
- A sandboxed --version probe: Quickshell 0.3.2 at the pinned revision.
- A clean rebuild with spirv-tools 2026.1: both expected shader files are nonempty,
  hashed, and generated with zero logged optimizer failures.

Metadata presence and enabled build flags do not prove services work.

## Clean shader rebuild and remaining diagnostics

The initial plan omitted spirv-tools. It was subsequently approved and installed
from the existing Ubuntu source, not silently added or replaced by disabling
optimization. A fresh workspace regenerated both shaders; no old outputs were
reused. All nine sandboxed steps, including optimizer/version probes, passed.

The first post-build assessment mistook a .qsb directory for a file and failed
after compilation/staging. The scanner now hashes regular shader files only,
with regression tests. The unchanged artifacts were reassessed separately;
the original report remains intact rather than rewriting away the failure.
Private evidence is recorded under the exact build directory printed by the
builder: `work/builds/<build-id>/report.json` and `assessment.json` in the same
directory. Consumers now require that explicit verified directory; see
[clean-source verification](clean-source.md). The assessment records the original
report hash, shader hashes, and 95 staged file/link artifacts.

Known diagnostic counts in this clean build:

| Category | Occurrences | Assessment |
|---|---:|---|
| Shader optimizer failures | 0 | Previous missing-tool failure resolved; graphical correctness still untested |
| Qt QML link-target diagnostics | 21 | Isolated linkage and representative imports/types pass; untested paths remain |
| Wayland XML validation | 2 | Generated protocol code compiled; protocol compatibility remains untested |
| Compiler warnings | 210 | Repeated diagnostics, not 210 distinct defects; includes strict aliasing and missing-return warnings |
| QML base-type metadata warnings | 2 | Representative runtime types resolve; generated tooling metadata is not thereby repaired |
| Unused CMake option notices | 2 | No-vendoring paths do not consume the FetchContent flag; Bubblewrap enforces no network |

These pattern counts retain known diagnostics; they are not a comprehensive
static analysis. Full raw logs remain available. Compiler warnings about missing
returns and strict aliasing are not automatically harmless or repaired by
installing the shader tool. No upstream source changes were made to hide them.

Other logs include Qt static-import/link-target warnings, upstream compiler
warnings, and Wayland XML validation warnings. They are not suppressed or assumed
harmless. Isolated linkage/import tests now pass within their bounded scope;
see [runtime checks](runtime-check.md). Remaining paths still require assessment
and later graphical testing. No complete Omarchy shell, desktop agent, PAM session,
lockscreen, or idle/suspend behavior has been exercised.

The matching original Quickshell package recipe and OmarchyLoadPatch semantics
are now identified in the [shell/packaging audit](shell-audit.md). The QtQuick
6.11 workaround is intentionally not applied to this Qt 6.10.2 build; full shell
compatibility and original binary equivalence remain unproven. License notices/source obligations and runtime-only packaging still
need review before distribution. Nothing in the current build authorizes
system installation, service activation, a session switch, or public release.
