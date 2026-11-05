# Deploy the Omarchy 4.5.0 stable component candidate

## Goal and evidence

Execute the user's explicit approval for local packaging, installation,
configuration reload and shell restart. Use the candidate from plan 078,
pinned to Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`, not development/quattro.
Compare the current installed release contract and owned process with the
candidate, reviewed runtime stages, source seals and native preflight.
Follow docs/installer.md and the transactional release updater; do not use the
broader dev-update target, which additionally changes managed config/autostart.

## Current gap and proposed shape

The stable source candidate passed 1079 unit tests and isolated component checks
but has not been deployed. Prepare a distinct private application release using
verified existing runtime/screenshot stages and preserved dependency pins.
Review native compatibility and the exact update plan. Back up launcher and
selector prestate through the existing transactional updater before changing
selection; retain the previous immutable release. Reload existing Hyprland
configuration with bounded error checks and restart only the recorded owned
Omabuntu shell using its explicit session-lifetime grant. Record private evidence
and validate selected release, process ownership, startup diagnostics and HDR.

## Safety and exclusions

The approval covers application packaging/install, live config reload and
Omabuntu shell restart, not a computer reboot, compositor restart or logout.
Do not install APT packages, rebuild/load plugins, change services/autostart,
write personal monitor/configuration or wallpaper settings, change lock/idle/
authentication, or touch GNOME/corporate integrations. Preserve
`render.cm_auto_hdr = 0`, existing user state and private artwork cache.
Do not commit, publish, execute upstream helpers or modify the reference package.
Stop on incompatible targets, failed checks, ambiguous process ownership or
unsettled transactions; use the reviewed updater's restoration path on failure.
Native startup is not visual, device-action or full-shell acceptance.

## Tasks

- [x] Inspect installed/native state and prepare the exact private build plan.
- [x] Package and preflight a distinct stable component release.
- [x] Review and apply the backed-up transactional application update and owned shell restart.
- [x] Reload existing configuration and verify errors, release, process and HDR state.
- [x] Run the full unit suite and record outcome and remaining acceptance limits.

## Outcome

The source-build pipeline reused verified runtime/screenshot stages and prepared
an artwork-free local stable component bundle with the existing pinned font and
plugin-manager policy. Native preflight passed without installing system packages.
The transaction completed as `updated-and-started`; the preceding application
release remains the previous selector and launcher/selector prestate is journaled.
For both start and failure restoration, an operation-local Installation subclass
calls the existing `start(restore_background=False)` API so no wallpaper restore
or configuration write is introduced; all process/native/transaction gates remain.

Hyprland configuration reload and config-error checks passed. Post-start
verification confirms the exact stable provenance, a new owned shell PID with
session lifetime, unchanged hashes for the existing Hyprland entry/managed
snippet, and automatic HDR still disabled. The full suite passes 1079 tests.
Private plans, build/update results, prestate and verification are recorded under
ignored `work/deployment-079/`; transaction backups remain in the manager's
private state directory.

Startup has no ERROR/FATAL/CRITICAL diagnostics. Five warnings cover two types:
portal application-ID registration and unresolved `system-reboot-symbolic` icon
requests. These remain documented rather than changing portal policy or icon
assets during deployment. Native visual, popup/focus, multi-output and real
device/action acceptance still require user interaction. No computer reboot,
compositor restart, logout, service/autostart change, commit or publication occurred.
