# Complete Hyprpm installer integration for the current PPA target

## Goal and comparison

Complete the source-side installer integration started in plan 051: offer the
plugin compiler prerequisites explicitly, support the current PPA Hyprland
0.57.0 target after reviewing version-pinned official APIs, and provide a
separately approved persistent next-login plugin path without touching the
running desktop. Compare official Hyprland commits
0aa6745f705f2c4b0a5004eb019ef76e5bbdb426 (0.57.0) and
efb50993780079460b0cbed1363e2166a2de1d9f (0.56.2), official plugin commit
d2427d4d15b36df40468f5a58bbd67cdba19835d, and Omarchy reference
03ff1eff3812933f7088484533784d2f63eaf19a. Review licenses before importing
anything; source/docs evidence stays private under work/.

## Gaps

The public installer selects runtime packages but never offers manager build
prerequisites. Package/session/release target checks still require 0.56.2.
Manager preparation assumes a compatible running session, making first-install
ordering important. Next-login activation does not reconcile manager plugins;
existing users need explicit legacy handoff, not silent adoption. The current
published archive is immutable and has not passed clean-VM acceptance.

## Shape and safety

Use an explicit source-reviewed target, not unrestricted future-version support.
Preserve the legacy binary verifier and refuse unsafe target/ownership migration.
Separate runtime packages, optional manager prerequisites, source preparation,
live enable/load, and persistent login integration. Back up/journal before any
approved deployment; never load plugins, rewrite private Lua, enable services or
transition sessions during this implementation. Version mismatches must remain
visible, especially installed-versus-running compositor differences. Review APT
simulations without bypassing installed-package change/removal guards.

A running-session manager build cannot be completed automatically from GNOME.
The installer must report deferred first-login actions rather than falsely claim
complete titlebar setup. Persistent login code must be explicitly granted, inert
until installed, untimed as a component, fail closed on target/receipt mismatch,
and must not update/build repositories or invoke sudo at login.

## Exclusions

No sudo/APT installation, PPA changes, plugin-manager mutations, plugin load,
live reload, desktop deployment, service activation, logout/restart, commit,
push or publication. Real clean-VM build/login/update/rollback acceptance needs
separate operator approval and evidence; green unit tests are not that evidence.
No automatic migration of private profiles or old bundled plugin activations.

## Tasks

- [x] Review version-pinned official API/manager evidence for 0.57 and prerequisites.
- [x] Align new-build package/session/release targets with reviewed 0.57 behavior.
- [x] Integrate explicit plugin prerequisites and deferred first-login guidance.
- [x] Implement opt-in receipt-checked persistent login handling without builds/sudo.
- [x] Add regressions and update operator documentation/remaining acceptance gates.
- [x] Run full unit tests, clean-source verification and whitespace checks.

## Results and remaining gates

864 unit tests passed, clean-source verification passed, and whitespace checks
passed. An artwork-free local application bundle was prepared and checked with
a 0.57.0 native contract, only native/hyprpm.json (no native plugin library), and
the immutable login helper. No application deployment was performed.

Official 0.57 CMake configure/installheaders requires more development packages
than the previous manually generated header path, including libeis, libcanberra,
sdbus-c++, protocol data and Xcursor/render headers. The scope now requests those
explicitly. Read-only local APT review found only additive plugin prerequisites;
this is not a fresh-VM result. Installed/running compositor ABI mismatches remain
blocked. Lua 5.4 linkage of the current Ubuntu PPA backend was inspected read-only.

The official root make installheaders also copies hyprland.pc to the shared
system pkg-config directory. The plan now records/backs up its bytes and previous
owner/group/mode, plus manager cache and shared parent directory metadata before
manager mutation. The login helper refuses missing headers/state, unsafe loader
filenames, foreign plugins and unresolved transactions rather than invoking a
manager fallback that might create privileged cache paths. Persistent login
consent and immediate owned-rule application remain separate choices.

- [ ] Approve a clean-VM/system-package test separately.
- [ ] Run and accept the real pinned header/plugin build on a matching 0.57 session.
- [ ] Verify live titlebars, first/repeat login and interrupted-operation recovery.
- [ ] Verify fresh application install, repeat/update and rollback on the VM.
- [ ] Review and approve any new commit/push/release publication separately.

No package installation, manager execution, plugin load, private-profile change,
service activation, session transition, commit, push or publication was performed.
