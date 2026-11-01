# Explicit 0.56.2 to 0.57.0 application transition

## Goal and evidence

Finish the application handoff after a separately completed compositor/plugin
upgrade, exercise transition/update/rollback with isolated fixtures, and prepare
the real read-only deployment review before asking to switch the recorded bar.
Compare the existing transactional updater, current application contracts and
manager/session ownership guards. Pins: Hyprland 0.57.0 commit
0aa6745f705f2c4b0a5004eb019ef76e5bbdb426, plugins
d2427d4d15b36df40468f5a58bbd67cdba19835d; legacy 0.56.2 mapping and Omarchy
03ff1eff3812933f7088484533784d2f63eaf19a remain provenance references.
No machine-specific inventories or private configuration in this plan.

## Gap and proposed shape

Normal updates correctly reject native-target differences. Add a distinct
--migrate-native approval only for an existing 0.56.2 application to reviewed
0.57.0 manager-policy application, with identical Ubuntu/Qt and user-state schema.
Do not rewrite old contracts or silently change the normal update rule.

Require the new compositor already installed/running clean with matching ABI,
verified manager policy/build receipt, regular matching library, verified headers,
consistent enable/load state and no foreign/unresolved plugin operations. No
compositor upgrade, build, load/unload or session transition is performed here.
Capture private profile fingerprints for drift/preservation, not adoption or
compatibility acceptance; do not parse arbitrary Lua includes. Owned sessions
must already match the current reviewed renderer. Existing next-login activation
requires its own handoff rather than silently inheriting a grant or replacing an
old loader. Document this exclusion explicitly.

Use existing locked staging/preflight/selector/launcher backups and journals.
Recheck all transition evidence after preflight and staging, before any bar stop.
Failed application start restores the recorded application/bar prestate, not
packages, compositor, plugins or private profiles. Old-target rollback remains
refused; ordinary same-target update/rollback continues through existing guards.
Published installer offers this distinct transition only on the supported pair,
with its own review/consent, not an automatic exception.

## Safety and exclusions

Back up edited repository files. No actual package/manager/config changes,
compositor/service/login action, bar restart, desktop deployment, Git staging,
commit, signing, push or publication during implementation. Ask separately before
real deployment; commit and publication remain later explicit gates. No generic
native bypass, unversioned adoption, arbitrary profile conversion or old bundled
activation migration. No claim of VM, visual or login acceptance from unit tests.

## Tasks

- [x] Back up affected source and review existing transactional behavior.
- [x] Implement narrow read-only native evidence and separately approved handoff.
- [x] Integrate checkout and published-installer consent without weakening defaults.
- [x] Test transition, drift/failure, same-target update/rollback and exclusions.
- [x] Build a fresh artwork-free candidate, run full verification and real read-only review.
- [x] Request separate real bar-switch approval, then verify only approved operations.
- [ ] Review changes and request commit/publication consent before v0.1.1 publication.

## Verification so far

949 unit tests passed; clean-source verification and whitespace checks passed.
A fresh artwork-free candidate was built and preflighted. Read-only review of
the real application/profile/manager state succeeds without suppressing native
guards. Existing healthy manager activation is preserved by the published flow.

An isolated rehearsal copied the real old and new application payloads under
ignored work/, then completed native handoff, same-target update and same-target
rollback with fixture process/native-evidence callbacks. Real selectors/bar and
fixture profile remained unchanged. This is actual payload/file transaction
coverage, not a live desktop, native visual or clean-VM acceptance claim.

Interruption review now also accepts the actual structured recorded process
identity (or absent process), not just legacy boolean fixture values. Native
handoff starts/restores its bar without writing wallpaper state. The original
contracts are never rewritten, and old-target rollback remains blocked.

After a separate explicit user grant, the real application handoff completed
with status updated-and-started. The selected application now carries the 0.57.0
contract and the recorded bar is running. Before/after profile and complete
manager evidence match; no package/compositor/plugin/profile/service/login
mutation was performed. The previous immutable application remains retained.
An ordinary update review now passes without the migration flag; against the
same candidate it correctly reports a no-op. This is not a second live update
or a live old-target rollback acceptance test.

Visual confirmation, clean-VM/first-login acceptance, source review, commit,
signing, tag/push and release publication remain separate outstanding gates.
