# Quickshell package plan

## Scope

This planner covers Quickshell source-build prerequisites, not the complete
runtime dependency set or a first-install Ubuntu wizard. In particular,
wallpaper application and WebP picker previews need the separately recorded
`hyprpaper` and `qt6-image-formats-plugins` packages. See
[installed dependencies](dependencies.md), [user deployment](user-installation.md)
and the [guided-installer roadmap](guided-installer.md). Historical package
counts below describe the development target, not a transaction to replay on
another machine.

## Reproduce without installation

```sh
python3 tools/omabuntu.py plan quickshell
```

The [manifest](../packages/quickshell-plan.json) records explicit Ubuntu package
groups, pinned upstream source candidates, and proposed build options.

The planner:
1. Validates package names.
2. Reads local APT policy with LC_ALL=C.
3. Stops if any explicit package lacks a candidate.
4. Pins each explicit request to that local candidate version.
5. Invokes apt-get with --simulate, --no-remove, and --no-install-recommends.
6. Records raw policy, exact simulated command, solver output, and change counts
   in a private report under work/package-plan/.

The package planner has no apply/install/build action. It performs no sudo,
network access, APT refresh, source modification, service activation, or session
change. A separate explicitly opted-in [workspace builder](runtime-build.md)
can fetch locked sources and build without system runtime installation.

Exit 0 means a simulation is ready for review, **not** that installation or a
source has been approved. Errors and simulated removals block the plan.
Versions for explicit requests are recorded, but transitive dependencies are
not a portable lockfile. Always repeat review if local metadata changes.

## Initial development-target result

The initially approved manifest contained 39 explicit package requests; some
were already installed. The current manifest has 40 after adding spirv-tools.
The solver proposed:

- **96 new packages**
- **0 upgrades or changes to existing packages**
- **0 removals**

The large closure is mainly Qt development/private headers, their mandatory
tools and QML dependencies, plus native development headers.
The simulated new-package origin labels all identify Ubuntu archive suites,
not a newly added repository. Existing installations, including the compositor
and wayland-protocols from an already configured third-party source, remain
pre-existing facts, not blanket approval of that source.

Raw output remains private. This summary is not a support claim for other systems.
A separate read-only metadata query matched all 96 exact transaction versions:
package archives total 28,418,960 bytes (about 27.1 MiB); their declared installed
sizes total 188,808 KiB (about 184.4 MiB). Cached archives can reduce downloads.
These figures exclude source downloads, compiler output, build/staging space,
and filesystem overhead. The CLI does not currently compute these size estimates.

## Preferred proposed source strategy

Keep the Quickshell crash handler rather than silently removing diagnostics.

1. Build cpptrace v1.0.4 at commit
   3db8da80111171c219ab5839905771386bee06b3 separately.
2. Use Ubuntu libunwind and libdwarf (plus system compression dependencies).
3. Enable external dependencies and disable CMake dependency downloading.
4. Build pinned Quickshell with VENDOR_CPPTRACE=OFF and its crash handler enabled.
5. Preserve PAM/Polkit build support, without installing or changing PAM policy.

Reviewed all 55 CMake/build-definition files listed by the pinned Quickshell
source tree. This identified additional GBM/EGL/Vulkan requirements and the
cpptrace download route. This static audit is not a verified build or a general
guarantee that upstream code cannot access the network.

cpptrace's reviewed options support external libdwarf and libunwind.
Its complete dependency behavior, license obligations, build compatibility,
and network-isolated execution remain to be tested before distribution.
Build options are in the manifest. The approved source builds have now completed
and staged with warnings; see the [build report summary](runtime-build.md).
The matching original Quickshell package recipe and QtQuick compatibility patch
are now documented in the [shell audit](shell-audit.md). That patch is
intentionally not applied to Qt 6.10.2; binary/full-shell equivalence is unproven.

## Current development-target execution state

The user approved this target's 96-package transaction and pinned workspace-only
builds. The user ran the private helper interactively. Verification confirmed all
96 expected versions, no changed pre-existing package versions, and no removals.
The pinned sources now compile and stage in Bubblewrap. An additional shader-tool
dependency was discovered, separately approved, and installed as
spirv-tools=2026.1-1. Verification against the post-initial-install snapshot found
exactly this one new package, no changed existing versions, and no removals.
A clean rebuild generated both shader outputs without optimizer failures.

The historical private helper at
work/dependency-install/install-dependencies.sh was used for the initial
96-package transaction. It refuses changed simulation output; do not reuse that
pre-install transaction on the now-installed target. Its package baseline remains
private evidence, not an installer available in a fresh clone. Other machines
need their own simulation and approval, with interactive authentication in the
user's terminal. Do not send credentials to an assistant.

Existing explicit requests may receive manual APT marks, and ordinary package
hooks/triggers can run. Preserve before/after package and mark evidence; do not
use broad autoremove as rollback.

## Approval boundaries

Before actual installation, approve the explicit manifest plus the full local
solver report. Re-check if the transaction changes. Standard package hooks and
triggers may run during a real installation; no report can guarantee otherwise.

Before compilation, approve the two upstream source candidates and isolated
build/staging plan. Do not use sudo cmake install or write into the active desktop.

Shell testing, system installation of custom artifacts, configuration application,
service activation, and lock/idle/suspend acceptance remain separate steps.
