# Assess installer/update readiness and prepare 0.1.1

## Goal and evidence

Assess whether the current source can be built as 0.1.1 and distinguish tested
installer/update logic from actual acceptance. Compare current source/tests,
contracts of the selected local application, activation/manager receipts, and
the existing exact-commit release publication workflow. Upstream Omarchy reference
remains 03ff1eff3812933f7088484533784d2f63eaf19a; compositor/plugin mapping is
Hyprland 0.57.0 / 0aa6745f705f2c4b0a5004eb019ef76e5bbdb426 and plugins
d2427d4d15b36df40468f5a58bbd67cdba19835d. No private inventories in this plan.

## Current gaps and safety

The working tree contains substantial uncommitted installer/plugin changes.
The publisher builds only a reviewed commit, refuses untracked files and asks
separately before commit and publication. Do not invoke its commit/tag/push path
under a build-only request. Existing archives remain immutable.

Known update guards intentionally reject native-target changes and activation
receipts that load the legacy bundled plugin. Manager migration alone does not
migrate application contracts or private Lua loaders. Verify the actual local
state read-only; do not bypass these guards or claim clean-VM/live acceptance.
Normal package installations, desktop deployment/reloads, service/login changes,
plugin loading, session transitions and private-profile changes remain separate
approval gates. No package/manager mutation or signing-key access is needed here.

## Proposed shape and exclusions

Review actual contracts and resolved manager state; run tests and packaging/build
readiness checks. If feasible, prepare an artwork-free local 0.1.1 candidate only,
clearly distinguished from a signed exact-commit distributable release. Record
remaining first-install/update/rollback/login acceptance and required approvals.
No commit/staging/tag/push/publication, privileged action, desktop deployment or
private configuration mutation. Use a fresh output and retain build evidence.

## Tasks

- [x] Inspect installer/update/publication code and local contract/receipt facts.
- [x] Verify current tests and local artwork-free build prerequisites.
- [x] Prepare/check an isolated local 0.1.1 candidate if prerequisites permit.
- [x] Report remaining update/migration and acceptance gates before publication.

## Results

925 unit tests passed; clean-source and whitespace checks passed. The artwork-free
local candidate was prepared and checked successfully. Its native directory
contains only hyprpm policy, not a bundled plugin. It is an uncommitted-source
candidate, not a signed exact-commit distributable release.

The actual read-only update review refuses the native-target transition from
0.56.2 to 0.57.0 as designed. The successful manager migration/activation does not
change the selected application's contract. An explicit, backed-up application/
session transition is still needed; do not bypass the updater guard or merely
rewrite its contract. Same-target fixture success is not real update acceptance.

Remaining release gates: explicit native-transition implementation/review, fresh
VM installation, real same-target repeat update/rollback and login acceptance,
source/provenance review, then separate commit/signing/publication consent.
No packages, manager state, installed application, private configuration, live
components, services, Git index/history, tags or remote release were changed.
