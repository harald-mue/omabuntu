# Implement Update > Omabuntu with a packaged application-only runner

## Goal and evidence

Implement the first proposal in plan 098: original Update root placement/icon
and Update > Omabuntu, opening an independent interactive terminal. Omarchy
v4.5.0 menu behavior is pinned to
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Reuse publisher signature/archive
verification and the existing reviewed application transaction, not upstream
update scripts or the broader first-install workflow.

## Gaps and shape

Add a closed menu action and fixed-argv terminal launcher, a signed-metadata
check/download API, public-version/local-provenance refusal rules and a packaged
Python runner with its full reviewed dependency/resource closure and trusted
public key. Checking runs only after activation. Separate metadata checking,
candidate download and exact-plan apply confirmations. Use the existing
transaction with a wallpaper-preserving Installation subclass and relocate
preflight reports to private cache, never the immutable installed bundle.
Preserve session lifetime and refuse prerequisites, incompatible/native/state
migration, mixed sessions, unresolved updates and stale running selections.

## Safety and exclusions

Back up affected repository files before edits. Implementation and contained/
temporary-home tests only: no real update download/check, package/source action,
real preference mutation, terminal launch, desktop deployment/restart, binding
edit, compositor reload, commit or publication. Existing Super+Space stays;
Ctrl+Space was not approved as a binding change. No Status/Rollback/Process
rows in this first batch; no Ubuntu upgrades, channel/kernel/firmware/config
reset/authentication/boot controls. No source builds, automatic approval,
background polling, new service, expiry wrapper or trust-key replacement.
Local releases are reported but never automatically replaced by public latest.

## Tasks

- [x] Back up sources and implement signed check/download plus safe version policy.
- [x] Add packaged interactive runner, report relocation and dependency closure.
- [x] Add original menu rows and closed independent terminal action.
- [x] Add regression/contained packaging tests and documentation.
- [x] Run full unit suite, clean-source and relevant contained UI checks.
- [x] Deploy after explicit approval and verify startup, menu and unchanged state.
- [x] Obtain user confirmation of native terminal invocation and pre-network cancellation.
- [x] Verify signed online metadata and local-derivative refusal after separate approval.
- [ ] Obtain separately approved real update-switch acceptance.

## Repository result and verification

Implemented Update > Omabuntu before System with a fixed-argv independent
terminal launcher, three terminal confirmations, signed metadata/archive checks,
public semantic comparison and refusal of local adaptations/downgrades. The
runner reuses the existing application review/apply transaction and always
suppresses wallpaper restoration, including failure recovery. Preflight reports
can be relocated outside the immutable payload. Packaging now includes the
runner's transitive Python import closure and reviewed trust/policy/runtime data.

1130 unit tests passed, including temporary-home transaction/recovery tests and
standalone payload imports. Existing signature tests verify disposable real
OpenSSH signatures. The contained menu fixture passed with the new root row;
a private local review bundle was prepared and verified but not installed.
Clean-source export/check passed. All source backups, synthetic test failures,
logs and generated artifacts remain under ignored work/.

The repository work performed no release-service request, real terminal launch,
package/source operation, user-state mutation, desktop restart, binding edit,
commit or publication. Ctrl+Space remains unmodified; configured Super+Space is
retained. Native terminal focus/lifetime, real update-pair self-restart and
visual/GNOME/fresh-machine acceptance remain unverified.

## Subsequent deployment approval

The user explicitly approved local deployment of the menu feature and a
bar-only restart, not launching the terminal, an online check or a public update.
Back up the current deployment and preferences, clone the verified installed
release, and replace only menu definitions, the menu dispatcher/new launcher,
updater dependency/resource payload and provenance. Preserve runtime, assets,
other shell components and manager bytes. Use the reviewed application-only
transaction with wallpaper restore disabled and previous-selection/startup
recovery on failure. Verify manifest/startup, independent menu registration,
new definitions and exact preference preservation without activating the action.

## Approved deployment result

Prepared a verified private derivative of the running release, changing menu
definitions, dispatcher/new launcher, 23 updater dependency/resource files and
provenance only. Existing runtime/assets/QML components and manager bytes were
retained. The reviewed update completed with a bar-only restart, no user-state
migration/native transition and wallpaper restoration disabled. The previous
application remains available as the rollback selection.

Startup and manifest integrity passed. Installed definitions expose Update before
System and the closed Omabuntu review action; the packaged trust key matches the
reviewed public key. All three bars and the independent menu registration are
present, with no shell error markers. Relevant preference presence, bytes and
modes match their pre-deployment backups. Private prestate, update evidence and
verification are under ignored `work/update-menu-099/deployment/`.

No terminal was launched, release service contacted, public update downloaded,
preference changed, binding edited, compositor reloaded, package/service changed,
commit made or artifact published during deployment.

## Subsequent user terminal feedback

The user confirmed that the proposed terminal invocation and cancellation before
network access work. This is user-reported acceptance of that limited interaction,
not an independently observed network trace or full focus/lifetime test.
No online check, archive download or application switch was run by the agent.
That feedback did not establish signed online checking, a real public-version
update pair/self-restart, GNOME/fresh-machine or shell-parent-exit behavior.

## Subsequent approved metadata-only check

Under plan 101, the user separately approved signed online metadata checking
without a bundle download or application switch. A bounded private diagnostic
verified the selected/running bundle and deployed updater/resource identity,
then exercised the same review logic against the actual release service with
the installed trust key. The public v0.2.0 signature/metadata verified, and the
local derivative returned `local-release-blocked` as intended. Only four
metadata/discovery requests occurred; archive/apply callbacks were forbidden.
Selection, previous selection, bundle integrity and running identity remained
unchanged. This was not a second native terminal/focus test or a real application
switch; update-pair/self-restart, GNOME/fresh-machine and shell-parent-exit gates
remain open. Evidence is private under ignored `work/update-menu-101/`.
