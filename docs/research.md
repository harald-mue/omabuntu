# Compatibility research

## Evidence hierarchy

1. Installed binary output and installed package-owned configuration/stubs.
2. Exact upstream tag/commit source.
3. Current upstream documentation, used only with explicit freshness limits.
4. Local APT metadata, which may be stale and does not approve a repository.

Raw downloads and local probe output stay under ignored `work/`.
Only selected public facts and upstream URLs belong in these documents.

## Hyprland: native Lua is the preferred route

The installed binary's `--version-json` output reports:

- Version: 0.56.2, tag v0.56.2, clean.
- Commit: `efb50993780079460b0cbed1363e2166a2de1d9f`.

This is the same upstream commit recorded by the private source reference.
The installed package includes a Lua default and the Lua API metadata stubs.

Reviewed official tagged sources:

- [Default Lua configuration](https://github.com/hyprwm/Hyprland/blob/v0.56.2/example/hyprland.lua)
- [Command-line implementation](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/main.cpp)

The default demonstrates hl.config, hl.monitor, hl.on, hl.bind, dispatcher
factories, workspace selection, and pointer bindings. The installed metadata also
contains misc.allow_session_lock_restore.

The tagged main implementation confirms that --version-json exits before
compositor startup. Doctor can therefore capture the installed build in GNOME,
while leaving running-session probes skipped when there is no instance context.

The guessed versioned wiki URL for 0.56.2 returned HTTP 404. The current
[configuration entry point](https://wiki.hypr.land/Configuring/Start/) was reachable,
but is not treated as a frozen 0.56.2 reference. Exact tagged examples and installed
API stubs provide the version-specific evidence for this investigation.

**Decision:** do not translate to legacy syntax or upgrade the compositor by default.
Review individual configuration options and helper semantics, then test against
the actual target session. Native plugin compatibility remains a separate gate.

## Quickshell: pinned runtime candidate, not yet validated

The source package suffix resolves to upstream commit
`2b4501a282689792b62e94f3fb30d8f512324fe6`.

Reviewed pinned sources:

- [Root build options and Qt requirements](https://github.com/quickshell-mirror/quickshell/blob/2b4501a282689792b62e94f3fb30d8f512324fe6/CMakeLists.txt)
- [Crash handler and dependency fetching](https://github.com/quickshell-mirror/quickshell/blob/2b4501a282689792b62e94f3fb30d8f512324fe6/src/crash/CMakeLists.txt)
- [PAM module](https://github.com/quickshell-mirror/quickshell/blob/2b4501a282689792b62e94f3fb30d8f512324fe6/src/services/pam/CMakeLists.txt)
- [Polkit module](https://github.com/quickshell-mirror/quickshell/blob/2b4501a282689792b62e94f3fb30d8f512324fe6/src/services/polkit/CMakeLists.txt)
- [Wayland requirements](https://github.com/quickshell-mirror/quickshell/blob/2b4501a282689792b62e94f3fb30d8f512324fe6/src/wayland/CMakeLists.txt)
- [Upstream license](https://github.com/quickshell-mirror/quickshell/blob/2b4501a282689792b62e94f3fb30d8f512324fe6/LICENSE)

The official generic installation guide redirected to a v0.1.0 documentation
page during this investigation; it is not used as proof of 0.3.2 build requirements.
See the [runtime investigation](../packages/quickshell.md) for proposals and blockers.

## Remaining provenance questions

The Omarchy shell includes an OmarchyLoadPatch marker. The reference package
metadata does not by itself prove which packaging patches affect shell loading.
Before treating the upstream commit as equivalent, investigate the original
package recipe and test shell load behavior. Do not remove the marker or assume
that an upstream version string proves identical behavior.

Follow-up evidence now pins the original source tree and complete root MIT
notice. Selected source imports now include the unchanged pure clock model, the
spacer/base pair, and the clock label's presentation files. See the [widget dependency review](widget-candidates.md),
the [passive spacer profile](passive-spacer.md), and the [derived clock preview](clock-preview.md).
None admits stock startup, the original calendar/IPC clock, or a host session. The exact Quickshell recipe and
patch are identified in the [shell audit](shell-audit.md), but full-shell loading
is still untested. Moving-branch research does not clear assets or future imports.
