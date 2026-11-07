# Native compatibility policy and installer diagnostics

## Delivery status

This change is shipped in public **[v0.2.2](releases.md#v022-release-scope)**.
It is not applied retroactively to v0.2.1, whose immutable installer still uses
exact native package checks. A new public installer run can fetch v0.2.2;
publication alone does not update an installed application, native packages or
the desktop. See the release scope for verification and acceptance limits.

## Build baseline versus compatible host

`packages/installer-runtime.json` and the application update contract retain the
reviewed Ubuntu 26.04 / Hyprland 0.57.0 / Qt 6.10.2 baseline. This identifies the
application's API/build contract; it is not an exact lock of every host package.
`tools/native_compatibility.py` centrally admits stable patch families to further
checks:

| Component | Minimum upstream version | Exclusive upper bound |
| --- | --- | --- |
| Hyprland | 0.57.0 | 0.58.0 |
| Qt | 6.10.2 | 6.11.0 |
| Hyprlock | 0.9.6 | 0.10.0 |

Version comparison is numeric. Ordinary Debian epochs, numeric packaging
revisions and recognized `+ds`/`+dfsg` repacks do not require a new Omabuntu release
for every package rebuild. Missing, malformed, prerelease/development versions,
dirty/invalid compositor metadata, versions below the minimum and other API
families remain blocked with an explanation. Known bad upstream patches can be
excluded explicitly in the shared policy. This policy is embedded in the signed
application/source payload: no moving compatibility file, background polling,
new network dependency or automatic trust-policy download is introduced.

Admission is conditional, not certification of every future patch. The review
covers the official 0.57.0→0.57.1 compositor changes, version-appropriate Lua
example/exit-only CLI, and 0.9.6→0.9.7 lock configuration/CLI changes. Hyprlock's
patch also changes authentication internals; source compatibility does not prove
successful unlock or recovery. We do not activate locking to test this.

Relevant official evidence:

- [Hyprland v0.57.0…v0.57.1](https://github.com/hyprwm/Hyprland/compare/v0.57.0...v0.57.1).
- [v0.57.1 Lua example](https://github.com/hyprwm/Hyprland/blob/v0.57.1/example/hyprland.lua)
  and [exit-only version CLI](https://github.com/hyprwm/Hyprland/blob/v0.57.1/src/main.cpp).
- [Hyprlock v0.9.6…v0.9.7](https://github.com/hyprwm/hyprlock/compare/v0.9.6...v0.9.7)
  and [v0.9.7 configuration example](https://github.com/hyprwm/hyprlock/blob/v0.9.7/assets/example.conf).

## Where checks run

- **Package planning:** use the installed package if present, otherwise the APT
  candidate. Show both values in structured evidence and identify which one was
  assessed. Do not upgrade an installed package to its newer candidate.
- **Application preflight:** query `Hyprland --version-json` with a timeout,
  validate clean source identity and family, assess the installed Qt package,
  and retain the isolated runtime linkage/QML-import/WebP checks. A compatible
  version does not override a failed/missing/timed-out runtime probe.
- **Source build planning:** use the same family policy; retain exact build
  input/dependency recording and drift checks, not a silent change of artifacts.
- **Generic session preparation:** admit a clean supported compositor without
  requiring optional plugin source approval. Existing profile/ownership,
  stopped-session and exact conditional-rollback rules remain intact. The
  historical source-reviewed 0.56.2 session path is preserved separately; it is
  not admitted as the new application's host target.
- **Lock-version preflight:** use the same Hyprlock family and keep all existing
  session, socket, duplicate-locker, static-config and explicit-apply gates.
  No PAM/authentication setting, idle policy or lock activation is changed.

The effective policy is included in package/build inputs and application
preflight/deployment review digests. Saved approvals cannot silently survive a
changed family/exclusion policy.

The exact legacy 0.56.2→0.57.0 native-application handoff is not generalized by
these patch-family rules. Other native-contract transitions require their own
explicit review.

## Plugin ABI remains a separate acceptance gate

Shell family admission does not authorize a plugin compiled for another
compositor. Pinned plugin source targets, installed/running compositor identity,
header versions/fingerprints, manager ABI state, successful build evidence,
library hashes, ownership receipts and separate activation/login consent remain
strict. Matching version labels or a claimed ABI string alone are not sufficient.
An existing verified manager build for the exact running target remains reusable;
unrelated/live plugin state is not adopted, unloaded or rewritten.

If the compositor has no reviewed plugin source/build target, the published
installer explains the detected version/commit and offers explicit continuation
**without optional hyprbars titlebar integration**. Declining stops before
application deployment. Accepting avoids an unnecessary compiler/header package
review, still permits the compatible application and generic session stages,
and does not offer a new plugin-login grant. Existing grants/state are preserved.
The source policy has not been widened to guess plugin compatibility with every
0.57.x compositor. This is a documented exclusion, not a replacement titlebar.

## Human-readable errors

Package review shows a separate native compatibility section, including admitted
patch versions. Unsupported versions produce component, origin, detected value,
supported range, reason and next step, for example:

```text
hyprland: APT candidate detected "0.58.0-1"; supported >=0.57.0, <0.58.0.
Outside the supported API family or below its minimum version.
Next: Check the detected package/probe and use a supported stable family.
New families need compatibility review; do not force an install or downgrade.
```

An application deployment refusal includes concrete failed preflight checks as
well as the private report location, rather than just "preflight blocked".
Probe failures remain failures with their timeout/missing/error status. The
installer never suggests disabling validation, blindly downgrading or upgrading
system packages to make a message disappear. Reports remain private; successful
collection/runtime probes are not native, graphical or security acceptance.

## Verification boundary

Tests cover fresh APT candidates 0.57.1/0.9.7, later numeric patches, package
revisions, missing/prerelease/new-family/dirty evidence, policy drift/exclusions,
version/probe diagnostics, runtime failures, session/plugin decoupling, explicit
plugin deferral/cancellation and unchanged ABI/receipt/activation safeguards.
They also exercise the packaged updater dependency closure and lock helper's
preflight without starting authentication.

Fresh-VM installation, native rendering, actual plugin activation, verified
unlock/recovery, first/repeat login, GNOME coexistence and a real application
update/recovery pair remain separate approval and acceptance gates.
