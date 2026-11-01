# Hyprbars repair and consolidated consent

## Goal and evidence

Add a discoverable repair path inside the normal install.sh published workflow
for the diagnosed enabled/receipted but unloaded hyprbars state. Reduce duplicate
outer review questions while keeping the actual reviewed transaction approval
and separate package, deployment, live-plugin and persistent-login grants.

Compare plan 063 findings, native_transition.manager_ready, plugin manager/login,
the pinned official hyprpm reload implementation, published_install and frontend
prompt tests. Pins: Hyprland 0.57.0
0aa6745f705f2c4b0a5004eb019ef76e5bbdb426; plugins
d2427d4d15b36df40468f5a58bbd67cdba19835d. Omarchy visual behavior is unchanged
(reference 03ff1eff3812933f7088484533784d2f63eaf19a).

## Proposed shape

A read-only repair plan verifies selected bundle policy, installed/running native
identity, immutable receipt, headers, library, exact repository and enabled state,
absence of foreign plugins and unresolved operations, and protected system hyprpm.
Only the proven enabled-but-unloaded case may offer one live repair confirmation.
After locking, verified backups and repeated drift checks, run only hyprpm reload
and verify the plugin appeared without changing the reviewed persistent state.
No build, enable/disable, unload, download, sudo, rules reload or login adoption.
Fail with retained manual-review evidence rather than automatic unload/retry.
Do not accept old failed operations by ignoring their status.

The public workflow finds this repair itself. Current identical applications
need no redundant deployment/restart; invalid/private profiles remain preserved.
Remove duplicate outer consent before inner PPA/package/font, profile, plugin
build/load and deployment transaction confirmations. Bar restart is explicit in
the final deployment confirmation. Retain independent persistent plugin and bar
login choices, typed migration/recovery phrases and publication confirmations.

## Safety and exclusions

Back up affected repository files under ignored work/. The task implements and
tests source, not live desktop repair. No actual plugin loading, package/header
mutation, service change, private Lua edit, wallpaper change, screenshot, reload,
logout or session transition is authorized. Do not reset unrelated desktop data
or treat process health as visual acceptance. Commit/push/publication remain
separate approvals. Authentication and external APT/hyprpm prompts stay intact.

## Tasks

- [x] Verify pinned reload behavior and back up affected source.
- [x] Add narrowly verified, backed-up repair planning/execution and CLI support.
- [x] Integrate repair discovery and remove duplicate public workflow questions.
- [x] Add drift/failure/foreign-state and prompt-boundary regressions.
- [x] Update documentation and run full tests/clean-source/whitespace checks.
- [ ] Present source results and request separate live-repair/Git approvals.

## Result

`tools/plugin_repair.py` plans a repair only for the verified enabled-but-unloaded
receipted hyprbars: exact selected-bundle policy/native target, installed=running
clean compositor, protected package-owned `/usr/bin/hyprpm`, headers, library,
exact repository pin, immutable receipt with header fingerprints, no foreign
plugins and no unresolved transactions. Strict native handoff still rejects the
missing plugin. One interactive live confirmation guards execution; verified
private backups and drift rechecks precede a single unforced `hyprpm reload`, and
loaded state plus unchanged persistent/native evidence is verified afterwards.
Failures keep a manual-review journal; no automatic unload/retry. JSON/digest
automation cannot bypass the live prompt; the real executor requires canonical
paths. New `--plugins-repair`/Make targets mirror the existing plugin stages.

The published flow now reuses a healthy manager build without compiler-package
installation, offers this repair itself, skips redeploy/restart for an identical
verified application, still offers profile/login setup (first-time users keep
receiving it), and removed the duplicate outer questions: PPA/runtime/font,
deployment (restart named in the final prompt), profile, plugin build and live
load each ask once in their reviewed transaction. Declined deployment performs
no follow-up desktop writes. Keyboard input accepts `skip`; current login files
repeat no grant questions.

All 996 unit tests, clean-source and whitespace checks passed. A read-only plan
on the real workstation found no blockers (`load-hyprbars`, release-0.1.3) and
executed nothing. Fixtures and this review are not native acceptance. The live
reload, any commit/push and a new signed release remain separate approvals.
