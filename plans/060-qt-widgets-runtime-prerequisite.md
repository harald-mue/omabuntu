# Qt Widgets runtime prerequisite

## Goal and evidence

Correct the published runtime inventory after the supplied clean-target preflight
reported `libQt6Widgets.so.6 => not found` and Quickshell exited before loading QML.
Bubblewrap itself and the other reported target checks succeeded. The existing
runtime manifest does not request Qt Widgets; application-build dependencies can
mask that omission on the development host. A retained private package snapshot
identifies the Ubuntu provider as `libqt6widgets6`.

No Omarchy configuration/behavior changes are proposed; its pinned reference is
not needed for this package-inventory correction. No new third-party code/assets
are imported.

## Shape and boundaries

Add the runtime library package, not Qt development tools, to the shared runtime
inventory. Regress the runtime-only scope and rejection of missing libraries even
when ldd returns zero. Preserve isolated preflight, exact native versions and
additive-only package policy. Keep the earlier APT-parser work intact.

Back up affected files under ignored work/. Do not install packages, alter
services/security settings, deploy/reload a desktop, or commit/sign/publish.
A read-only APT simulation on the affected VM must precede any separately approved
package operation. Do not claim clean-VM acceptance based on the build host.

## Tasks

- [x] Back up and correct the runtime manifest and package-scope regression.
- [x] Regress missing Qt Widgets linkage despite a successful ldd exit.
- [x] Run the full tests, clean-source and whitespace checks.
- [x] Explain the exact missing dependency and read-only VM verification step.

## Result

The runtime scope now requests `libqt6widgets6` without adding development tools.
The missing-library regression confirms that a zero ldd exit does not bypass
preflight, even with successful simulated QML markers. All 963 unit tests,
clean-source and whitespace checks passed, including the earlier parser fixes.

The affected VM still needs a read-only package simulation before any approved
installation; no such installation was executed here. This local source change
has not been committed, signed or published and does not change existing release
archives. Passing a later VM preflight still will not establish login or visual
acceptance.
