# PPA system headers and explicit interrupted-migration recovery

## Goal and evidence

Correct the cache-only header assumption exposed by the real migration. The
Ubuntu PPA Hyprland 0.57.0 package owns its pkg-config file and headers under
/usr/include/hyprland; the version header matches official commit
0aa6745f705f2c4b0a5004eb019ef76e5bbdb426. Compare the package-owned binary,
metadata and system headers with pinned official hyprpm behavior from plans
051–053. Omarchy reference remains 03ff1eff3812933f7088484533784d2f63eaf19a.
Keep machine-specific journals/inventories and downloaded evidence private.

The failed migration stopped after verified disable/removal and an isolated
header refresh. No new repository, build receipt or live plugin was established.
Do not rerun normal migration, restore enablement, erase the failed journal or
invent an ownership receipt.

## Shape and safety

Validate either complete manager-cache headers or package-owned PPA system
headers, including commit, ABI dependency versions and pkg-config identity.
Never silently fall back from corrupt/incomplete cache headers. Seal the chosen
header inputs in review/receipts and recheck before/after manager operations;
login validation remains read-only and cannot initialize a manager store.

Add an explicit read-only recovery plan for only the precise failed checkpoint:
verified original backup, verified disable/removal, failed header verification,
unchanged native/package/backend identity, no repositories/loaded plugins and
fresh valid headers/global ABI. Require separate interactive recovery approval.
Back up the current checkpoint before executing only the missing pinned add/build.
Leave new plugins disabled and verify output before creating an inactive receipt.

Keep the original failed journal immutable. After successful recovery, write a
separate hash-bound resolution linking it to the completed recovery journal.
Normal manager/login guards accept only that verified resolution, never a plain
status edit. Interrupted/invalid recovery stays blocked and requires review.

## Exclusions

No actual manager/APT/sudo action, package source changes, plugin loading,
configuration reload, private-profile change, session transition, commit, push
or publication. Do not perform privileged restoration or execute pasted manager
commands. Native build/live acceptance remains a separate user-approved gate.

## Tasks

- [x] Establish/read-only verify package-owned header evidence and current checkpoint.
- [x] Correct shared migration/login header verification without weakening cache checks.
- [x] Add explicit checkpoint recovery, backups and hash-bound resolution guards.
- [x] Add regressions and document exact operator/recovery commands.
- [x] Run full unit tests, clean-source verification and whitespace checks.

## Evidence and verification

The published Debian source archive for the exact PPA package confirms patch
`99-hyprpm-global-headers`: global pkg-config existence bypasses the upstream
cache check; header update records the installed ABI and returns without cloning.
Omabuntu independently checks protected package-owned system inputs, commit/clean
state, pkg-config version/prefix and available dependency version macros rather
than trusting the patch's existence-only check. Source review material remains
under ignored work/; no third-party implementation was imported.

The real read-only recovery review succeeds: the original backup hash and
unchanged shared metadata match, the manager contains only the empty header
cache/current-ABI global state, and the plan contains only pinned repository
add/build. No actual manager command was invoked during this request.

917 unit tests passed, including checkpoint/backup/header drift, failed or enabled
build output, exact continuation consent, isolated fixture execution, immutable
original journals, hash-bound resolutions and standard activation guard behavior.
Clean-source verification and whitespace checks passed.

- [ ] Obtain separate approval and execute the real interactive recovery/build.
- [ ] Establish native titlebar acceptance and separately approved activation.
- [ ] Deploy any updated immutable helper/login integration under separate consent.

No packages, manager cache, original journal, loaded plugins, private profile,
services or session state were changed during implementation. No commit, push or
publication was performed.
