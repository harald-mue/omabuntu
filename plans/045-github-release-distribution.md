# GitHub release distribution

> **PARTIALLY SUPERSEDED.** The statements below retaining deprecated local
> channel compatibility are no longer valid. [Plan 048](048-remove-release-channels.md)
> removes that implementation entirely. The signed GitHub Release workflow
> remains current; the original implementation record below is retained.

## Goal and evidence

Replace channel-based distribution with development checkouts and versioned
GitHub Releases. Compare the current Makefile, install.sh, setup guide,
bootstrap builder and release coordinator. Desktop sources remain pinned to
Omarchy 03ff1eff3812933f7088484533784d2f63eaf19a; no desktop adaptation changes.
The current bundle has no remote distribution or publisher verification.

## Shape and safety

Use Python standard library for release orchestration and safe archive handling.
`make release VERSION=x.y.z` reviews tracked/untracked changes, requires explicit
commit consent, tests and builds an isolated committed tree without artwork,
then requires separate publication consent. Never automatically stage untracked
files, force-push, skip hooks, or change Git configuration. Build before push.
Archive source tools with the bundle so installation requires no checkout.
Sign checksums with an explicitly configured SSH publisher key. Fail closed if
no trusted public key is configured. No key generation or credentials in Git.
Use a draft GitHub Release until uploads complete. Retain failures for diagnosis.
The network bootstrap verifies before extraction and preserves installer approval
gates. Source checkout remains the development entry point. Existing channels
are deprecated compatibility only, not used or modified by the new flow.

## Exclusions

No publication, commit, push, package install, live desktop changes or key setup
in this implementation session. No artwork redistribution, claim of stock-VM
acceptance, automatic native ABI repair or unattended desktop activation.

## Tasks

- [x] Implement reviewed release packaging, signing and GitHub draft publication.
- [x] Implement bounded download, checksum/signature verification and safe extraction.
- [x] Connect checkout/bootstrap entry points and remove automatic stable promotion.
- [x] Update Makefile and operator documentation.
- [x] Add regression tests and run the full suite.

## Verification and remaining gates

800 unit tests passed; clean-source verification and shell syntax/whitespace checks
passed. Tests include real temporary SSH signature verification and fixture-only
publication ordering, unsafe archives and refusal paths. No real release build,
upload, downloaded first installation or stock-VM acceptance was performed.
The user-approved publisher public key is now configured. Private-key access
and the first real release remain required. Existing
local channels are retained only as deprecated compatibility; new entry points
neither consume nor promote them. Generic session/login setup remains opt-in.
