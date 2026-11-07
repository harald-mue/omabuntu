# Replace exact native package pins with scoped compatibility checks

## Goal and evidence

Implement the user-approved compatibility policy and actionable installer errors.
Compare bootstrap package selection, application preflight, session-file planning,
optional hyprbars preparation/login and lock helper checks with the fresh-install
PPA evidence from plan 104. Review official Hyprland v0.57.0/v0.57.1 and Hyprlock
v0.9.6/v0.9.7 release/configuration sources before implementation. The admitted
Omarchy component pin remains v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; no upstream provisioning is imported.

## Gaps and proposed shape

Bootstrap and application preflight require exact package versions; generic
session planning is unnecessarily coupled to plugin source approval. Hyprlock's
helper has its own exact version check. Existing plugin checks correctly require
matching installed/running compositor, headers, receipts and source policy.

Introduce a shared standard-library compatibility module for stable upstream
families and minimum versions: Hyprland >=0.57.0,<0.58.0; Qt >=6.10.2,<6.11.0;
Hyprlock >=0.9.6,<0.10.0. Reject malformed/prerelease/dirty evidence and reserve
explicit exclusions. Retain the older reviewed 0.56.2 generic-session path for
existing supported installations, not as the new application target. Keep build
baseline/native-transition contracts distinct from host patch admission.

Use the policy in bootstrap, binary/Qt application preflight, session planning
and packaged lock-version preflight; preserve ELF/QML checks and authentication/
recovery gates. Ship the shared helper in ordinary and standalone updater payloads.
Report component, installed/candidate/probe origin, detected version, accepted
range, reason and safe next step. Show successful native checks in package review
and concrete failed checks rather than only a report path on deployment refusal.

Keep plugin source/ABI/build/receipt safety strict. Unsupported plugin preparation
must be explained and optionally deferred without blocking application/session
setup or implying native titlebars are available. Do not reinterpret matching
version strings as an ABI proof or automatically reuse an old plugin binary.

## Safety and exclusions

Repository changes, private backups/public source references, and contained/
temporary-home tests only. No package/source install/update/downgrade, privilege,
plugin build/load/unload/reload, wallpaper/preference mutation, desktop/session
change, lock/idle/suspend activation, PAM/authentication change, service action,
commit, push or release publication. The installed immutable release remains
unchanged. A future signed release is required to ship the fix; this request is
not approval to publish v0.2.2 or modify existing artifacts. Preserve GNOME and
existing private profiles. No timeout wrappers on normal desktop components.

## Tasks

- [x] Review official version-appropriate sources and compatibility boundaries.
- [x] Back up affected paths and implement shared policy/structured diagnostics.
- [x] Integrate bootstrap/preflight/session/lock packaging and optional-plugin feedback.
- [x] Add regression coverage for fresh newer patches, unsupported families, failures,
      drift and unchanged strict plugin guards/optional deferral.
- [x] Update documentation and run full tests, clean-source and relevant checks.

## Acceptance limits

Family admission is a policy with runtime checks, not proof that every future
patch is behaviorally equivalent. Native fresh-VM installation, lock recovery,
plugin activation, actual update pair and GNOME/session behavior remain separate
acceptance gates; no live acceptance is claimed from source/test success.

## Source review and implemented result

Official comparison bases are Hyprland `0aa6745f705f2c4b0a5004eb019ef76e5bbdb426`
to v0.57.1 `acc1aa0bfd4bd575dcb0f76c35ccf12b660a1ab9`, and Hyprlock
`b222d9b1f87e980cac379371df57913a53b99d7f` to v0.9.7
`74efcdc96ee6d08480815064dab5112e0101eb1a`. Reviewed changes, version-specific
examples and CLI source support the bounded family policy, not a plugin ABI
claim. Hyprlock authentication-internal changes remain outside live acceptance;
no authentication policy or lock configuration was changed. References remain
private, and no upstream implementation/assets were imported into the product.

The shared module now drives package/source-build admission, binary JSON/Qt
preflight, generic-session and lock-version checks. Strict runtime linkage/QML/
WebP checks remain and report their failure categories, including timeouts.
Package review shows actual installed/candidate origin, detected version and
range; deployment refusal includes the failed checks and private report path.
Effective policy digests bind package/build/deployment review inputs, preserving
drift refusal. Build baseline/update-contract and the explicit legacy native
handoff are unchanged.

Generic session planning is independent of optional plugin approval. Existing
plugin source pins, installed/running identity, header/ABI/build/receipt checks,
and live/login consent are unchanged. A missing reviewed plugin target offers
explicit continuation without hyprbars, skips compiler-package review and does
not offer a new plugin-login grant. Declining stops before application deployment;
existing plugins, grants and private profiles are preserved. This does not add
unreviewed plugin source targets or guarantee titlebars on every admitted patch.

All 1158 tests pass. The fresh 0.57.1/0.9.7 candidate fixture fails as intended
against the backed-up original exact-version logic, and passes with the shared
policy. Clean-source checks pass. A contained review bundle verifies intact and
both packaged helper/updater copies import in isolated Python without this
checkout or bytecode/report writes into the release. It was not installed or
started, and is not a complete fresh bootstrap build or native acceptance test.
Backups, previous-state records, source evidence, negative control and check/
packaging logs remain under ignored `work/native-compatibility-105/`.

Documentation marks this as an unpublished source follow-up: v0.2.1 remains
immutable and still contains its old exact-version checks. No commit, push,
release publication, package/source change, privilege, desktop/session operation,
plugin activation or lock/authentication action was performed.
