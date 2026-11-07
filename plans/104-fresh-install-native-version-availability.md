# Check fresh-install Hyprland and Hyprlock version availability

## Goal and evidence

Investigate the user-reported v0.2.1 fresh-install refusal for required Hyprland
0.57.0 and Hyprlock 0.9.6. Compare bootstrap native-version checks, the configured
cppiber Hyprland PPA's public Ubuntu resolute amd64 package index and official
upstream release metadata. Omarchy component pins remain v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; this is availability diagnosis,
not acceptance of newer compositor/configuration/plugin APIs.

## Gaps and proposed shape

The user log reports required versions, but not actual installed/candidate
versions. Determine whether current published candidates have moved beyond the
strict reviewed native target. Retain bounded public lookup evidence under
ignored work/ and distinguish repository availability from the remote machine's
actual APT resolution. Explain the cause and next review gate without weakening
compatibility checks.

## Safety and exclusions

Read-only source/public HTTPS investigation; reports only under ignored work/.
No apt update/install/downgrade, additional source, privilege, service activation,
lock/authentication change, desktop/session operation or package-version bypass.
Do not inspect another machine or claim its candidates from this checkout.
Do not change target pins, runtime/configuration/plugin contracts, commit or
publish. A newer upstream release alone is not Ubuntu package availability or
functional/security acceptance.

## Tasks

- [x] Inspect exact installer refusal logic and configured package source.
- [x] Check current PPA candidates and official upstream release versions.
- [x] Record findings, uncertainty and safe next steps; run tests/diff checks.

## Findings

The configured cppiber Hyprland PPA's live resolute amd64 Packages index lists
Hyprland `0.57.1-1ppa1~1resolute1` and Hyprlock `0.9.7-1ppa1~1resolute1`.
Official upstream latest-release metadata agrees: v0.57.1 and v0.9.7 respectively.
`tools/bootstrap_packages.py::NATIVE_VERSIONS` still requires exactly 0.57.0
and 0.9.6; `native_blockers()` strips Debian packaging suffixes but requires
exact upstream-version equality. On a fresh installation, the candidate rather
than an installed version is checked. This explains both reported refusals if
the VM resolves the current PPA candidates. The VM's actual policy/plan was not
collected; the public index is not proof of its local APT state or of signed APT
metadata validation in this diagnostic.

No target pins or refusal rules were changed. Supporting the new versions needs
a separately scoped compatibility review of runtime/configuration and Hyprland
plugin ABI/hyprpm policy, plus lock configuration without activating locking or
changing authentication. Do not simply use a greater-than version allowance or
recommend an unreviewed downgrade. A fixed fresh-install path requires a new
signed release; changing checkout documentation/code cannot change v0.2.1's
immutable installer source. Public lookup evidence remains privately under
ignored `work/native-versions-104/`. All 1132 tests and whitespace checks pass.
