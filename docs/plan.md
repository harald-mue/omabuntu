# Implementation plan

## Current status and next deployment milestone

The numbered stages below describe the original sequencing, not live process
status. Since then, a selected-shell trial and versioned user deployment have
been implemented; the latest recorded deployment is release `.23` (see
[user installation](user-installation.md)). Theme/background application and
WebP picker decoding required separate hyprpaper and Qt image-plugin package
installs, now recorded in [dependencies](dependencies.md).

A [guided local-bundle installer](guided-installer.md) now implements
feature-oriented preflight, separate runtime/build dependencies, reviewed APT
transactions and reuse of the existing release installer. Configuration and
keybinding integration, wallpaper process management and clean-target acceptance
remain pending. The CLI is not approval to change a desktop or a universal
fresh-desktop provisioner. Autostart, supervision and authentication/recovery
remain separate gates.

## 0. Foundation

- Create a standalone English-only repository.
- Add private diagnostic reporting, simulated package planning, isolated profile
  parsing, and synthetic tests.
- Keep the source reference separate and unchanged.
- Record compatibility gaps and publication requirements.

## 1. Resolve compatibility

- Inspect the installed Hyprland package/build and configuration format.
- Check version-appropriate official documentation.
- Collect runtime evidence from Hyprland only after agreeing on session timing.
- Investigate Quickshell packaging, required Qt APIs, PAM, and Polkit features.
- Agree on package/build sources, required features, and security constraints.

Progress: capability matrix and native-Lua direction recorded. Candidate package
manifest and APT simulation completed. The explicitly approved target dependency
transactions and pinned workspace builds are complete; runtime diagnostics pass
within their documented limits. New transactions, other machines, deployment,
and desktop/session activation still need separate approval.
Deliverables: capability matrix, approved package map, and explicit API decision.

## 2. Minimal window-manager port

Back up affected target paths and record rollback first.
Implement terminal launch, German input, core bindings, dwindle, workspaces,
geometry, and target-specific monitor fallback.
No new shell or lock/idle dependency in the first application.
A staged minimal profile now parses successfully with the native verifier; it is
not installed and omits documented features. Target backups and application
approval still precede any real desktop change.
Reload and inspect config errors only after approval; test actual bindings.

## 3. Original shell and theme

Review upstream licenses before importing files. Add a selected, traceable
Quickshell runtime and a strict helper allowlist. Block Arch management routes.
Validate single-instance ownership of notifications and agents.
Keep optional networking and new lock/idle activation off initially.

Progress: the [source/license pin and independent fail-closed host](shell-gate.md)
now have contained nonvisual fixture evidence. Its catalog remains empty. Next,
the [widget review](widget-candidates.md) records pinned lexical closures and an
individually reviewed original pure-model import with contained Qt math tests.
The [passive spacer contract](passive-spacer.md) verifies atomic inputs and a
sealed non-rendering original leaf/base closure. The [clock preview](clock-preview.md)
now adds a derived read-only label and one private software image. Subsequent approved live trials and user deployment are recorded in WORKLOG
and [user installation](user-installation.md). Any new trial or session
transition still needs a named session, socket, stop command and recovery
approval. Diagnostic success does not approve stock plugins or desktop activation.

## 4. Workday integrations and security

Test audio, Bluetooth, brightness, clipboard, capture, portals, meetings, and docks.
Treat authentication and lock/idle/suspend as a separate acceptance gate.
Preserve a validated existing security mechanism until the replacement passes.

## 5. Reproducible deployment and release

Implement reviewed plan/backup/apply/verify/rollback tooling from proven steps,
with explicit opt-in and error handling. Test idempotency and partial rollback.
The release packager, integrity checks, user installation, owned-process
session control and release rollback/recovery now exist. Complete the missing
first-install steps and clean-target tests in the
[guided-installer roadmap](guided-installer.md); do not describe release
rollback as package or desktop-configuration rollback.
Complete license/provenance/privacy review before publishing.
