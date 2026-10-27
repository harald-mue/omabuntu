# Implement the guided local-bundle installer

## Goal and compared evidence

Implement a usable, fail-closed CLI entry point for supported Ubuntu targets,
reusing the existing release installer rather than creating another deployment
format. Evidence: docs/guided-installer.md, docs/user-installation.md,
tools/omabuntu.py, tools/package_plan.py, tools/check_runtime.py and
tools/user_install.py. Omarchy remains pinned at
`03ff1eff3812933f7088484533784d2f63eaf19a`; this work does not change its
layout or configuration behavior.

Current gaps: only build-package planning exists; package prerequisites and
feature behavior are not checked before user deployment. A fresh target has
no guided transaction linking runtime dependencies, isolated decoding/import
checks and the existing backed-up installation. There is no safely reviewed
automatic configuration adapter or wallpaper process supervisor yet.

## Proposed implementation

Python-standard-library CLI with preflight, package-plan, packages, plan,
install and start stages. A feature manifest separates runtime and wallpaper
packages from build dependencies. Save private reports in ignored work/.
Package apply needs an explicit reviewed-plan digest, repeats the complete
simulation and package/mark snapshot, records prestate, uses interactive sudo
in the user's terminal and verifies package versions/poststate. No automatic
APT refresh, repository addition, removals, downgrades or unrelated upgrades.
A package transaction is never triggered by shell deployment.

Preflight verifies bundle integrity, target versions and native runtime
linkage/imports plus an actual WebP decode in Bubblewrap. Missing commands,
timeouts and unsupported targets block deployment. File-existence checks are
not decode acceptance. Deployment and session start have separate approvals;
existing Installation owns backup/selection/recovery and process identity.
A running shell blocks replacement rather than being stopped implicitly.

## Safety and exclusions

Implementation and isolated tests only in this request: no real package
installation, desktop/configuration changes, deployments, service starts,
reloads, session transitions, commits or publication. Never execute test
commands against live wallpaper or theme configuration. Tests inject runners
and temporary installation paths.

No automatic compositor installation, source addition, config/keybinding
merge, lock/idle/suspend, package purge, release pruning, autostart or crash
supervision. The CLI clearly reports manual configuration and separately
approved wallpaper startup as remaining steps; it is a supported-target
local-bundle installer, not a universal fresh-desktop provisioner. Those
adapters remain gated follow-up work, not silent fallback behavior.

## Tasks

- [x] Add runtime/feature dependency manifest and validated loading.
- [x] Implement bounded preflight and isolated runtime/WebP verification.
- [x] Implement reviewable pinned package planning, drift detection,
      interactive explicit apply and transaction evidence.
- [x] Add reviewed deployment and separate session-start entry points using
      the existing installer.
- [x] Add fixture-only tests for success, errors, changed plans, unsafe
      transactions and no-apply safety (31 new tests).
- [x] Update installation guides and roadmap with actual scope and commands.
- [x] Run verbose unit tests, CLI smoke checks and update WORKLOG (458 pass;
      real isolated preflight and missing-package simulation pass, no host apply).
