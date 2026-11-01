# Installed-runtime-compatible plugin headers

## Goal and evidence

Make the single install.sh workflow resolve the reported plugin prerequisite
conflict instead of merely deferring it. The supplied APT simulation upgraded a
systemd/udev family when adding plugin development packages. The plugin manifest
requests libudev-dev, whose exact runtime dependency can select a newer libudev1
than the installed baseline. Candidate-only pinning ignores an available Ubuntu
header package matching that existing runtime.

Compare bootstrap_packages.request_manifest/apply, install.package_review/apply,
the private package-plan format, published installer and fixture tests. Preserve
Hyprland 0.57.0 pin 0aa6745f705f2c4b0a5004eb019ef76e5bbdb426 and plugin pin
d2427d4d15b36df40468f5a58bbd67cdba19835d. No upstream configuration behavior or
third-party code/assets change.

## Proposed shape

Only the plugin prerequisite scope may retry a blocked candidate simulation with
a narrowly mapped libudev-dev version matching the already installed libudev1.
Use bounded read-only APT metadata queries to prove package/version/architecture
and the exact runtime dependency. Do not invent a version or add a repository.
Retain the original simulation and metadata in the private plan, show the older
header selection explicitly, and ask for the exact final package transaction.
Re-simulate and accept only additions; repeat all evidence/state checks on apply.
If unavailable, malformed, held, or still requiring installed-package changes,
keep the blocker; never silently permit upgrades or install from another source.

Session/profile/login and live plugin grants stay independent within install.sh.
A first Hyprland login may still require a later invocation of that same entry
point; no internal commands or automatic logout/session switch are introduced.

## Safety and exclusions

Back up affected source under ignored work/. No package installation, root/header
mutation, service action, desktop deployment, security/PAM/boot changes, commit,
push, signing or publication in this task. No general solver search, installed
package downgrade, arbitrary old headers or blanket OS upgrade. Do not claim a
VM-native build was accepted based on fixtures or the development host.

## Tasks

- [x] Back up source and add narrowly scoped matching-header review support.
- [x] Display compatibility evidence and preserve exact apply-time rechecks.
- [x] Add additive-success, unavailable/malformed, residual-upgrade and drift tests.
- [x] Explain same-entry continuation and verify tests/clean-source/whitespace.
- [x] Report local-only status and remaining real-VM validation.

## Result and limitations

Plugin package review now retries only the reviewed header/runtime pair, proves
its exact dependency using APT metadata and retains both simulation attempts.
The UI explicitly names the candidate, selected header and preserved runtime;
apply rechecks the entire snapshot and exact simulation before installation.
Other scopes, held packages and residual installed-package changes are not
implicitly accepted. No additional source or apt update is introduced.

A bounded read-only HTTPS comparison of public Ubuntu indexes found matching
headers in the security pocket even though updates advertises a newer candidate.
That observation is not signature-verified installation authority: the affected
machine's configured APT metadata, final simulation and normal authenticated APT
installation remain authoritative. Raw observations are private under work/.

All 979 unit tests passed, including successful additions-only application with
unchanged existing versions, explicit UI disclosure, unavailable/malformed data,
failed/residual-upgrade simulations and apply-time evidence drift. Clean-source
and whitespace checks passed. No VM package/header build was performed; actual
VM completion, login and titlebar acceptance remain outstanding. Existing signed
archives are unchanged; commit/push and a new signed release require approval.
