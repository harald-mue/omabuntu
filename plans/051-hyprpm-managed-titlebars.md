# Hyprpm-managed titlebars and separate package scopes

## Goal and evidence

Stop shipping a compositor-ABI-bound hyprbars library in new source/release
bundles. Use explicitly pinned official hyprland-plugins sources through hyprpm,
with separate build and live-activation approvals. Separate published runtime
packages from the full Quickshell/Omasnap source-build inventory.

Evidence: current pipeline, bundle/plugin verifier, activation template, package
planner and published installer. Official Hyprland hyprpm sources were reviewed
at efb50993780079460b0cbed1363e2166a2de1d9f (0.56.2) and
0aa6745f705f2c4b0a5004eb019ef76e5bbdb426 (0.57.0). Both use the root-managed
/var/cache/hyprpm/<user> store. `update` and `enable` reconcile live load state;
they are not intrinsically build-only. Official plugin pins are
7644cecdb947060682891a0db2a0cdc5c0b9e704 and
d2427d4d15b36df40468f5a58bbd67cdba19835d respectively. Current desktop source
fidelity remains compared to Omarchy 03ff1eff3812933f7088484533784d2f63eaf19a.
The wiki was unavailable (HTTP 403); version-pinned official source/help and
manager state code are the primary behavioral evidence, retained privately.

## Shape and safety

New bundles carry a hyprpm policy, not native/hyprbars.so. Keep legacy immutable
bundles/verifiers valid and refuse switching away from an installed activation
that still references a bundled library. Prepare/activation are explicit CLI
stages, never part of download/build/install. Refuse unmanaged manager repositories,
enabled plugins during preparation, and installed/running compositor mismatch.
Snapshot affected manager state and journal before approved manager mutations;
never automatically purge/remove repositories, unload plugins or edit internal
manager TOML. Run as normal user; warn that hyprpm may request sudo internally.
Use the existing process-scoped Lua include workaround. No live commands here.

Published-runtime scope excludes compiler/header/source-build groups. Plugin build
dependencies have their own reviewed package scope. Keep upgrades/removals refused.
Do not pretend this work validates Hyprland 0.57 Lua/session/runtime compatibility:
record its official plugin pin, but keep it unavailable for apply until reviewed.
The old VM failure is not solved merely by dropping the library; exact runtime
and session target gates stay until separately adapted and tested.

## Exclusions

No package installation, sudo, manager invocation, plugin loading, restart,
configuration reload, desktop mutation, commit, push or release publication.
No automatic next-login hyprpm reload: loading/titlebar reconciliation remains an
explicit user action, not a new autostart grant. No automatic source upgrades.

## Tasks

- [x] Add reviewed hyprpm policy and separate management/activation stages.
- [x] Stop bundling native plugins in the default pipeline; guard legacy activation.
- [x] Split runtime, full-build and plugin-build package scopes.
- [x] Update operator documentation and version/acceptance limitations.
- [x] Add regressions, run the full suite and clean-source verification.

## Verification and remaining acceptance

833 unit tests passed; clean-source verification and `git diff --check` passed.
Tests use private fixtures, not the real manager or compositor. Read-only ELF
inspection confirmed direct runtime dependencies for LayerShellQt, libdeflate,
jemalloc, libdwarf and libunwind; non-development package requests are explicit.
The public release list confirms v0.1.0 exists, but its artifacts were not changed.

No packages, manager state, live plugins, desktop/session files or services were
changed. No commit, push or publication was performed. Real pinned-manager build,
activation, native titlebars, clean-VM dependency closure, 0.57 adaptation and
recovery acceptance remain outstanding. Automatic login loading is excluded.
