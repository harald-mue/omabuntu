# Document v0.2.4 publication

## Goal and evidence

Update the README and current release/capability documentation after the user's
publication of v0.2.4, then commit and push the documentation-only changes.
Compare GitHub release metadata and asset digests, the peeled local release tag,
the retained publication artifacts, signed checksums and source/bundle integrity.
Compare release scope with commits since v0.2.3 and plans 111-121. Original
component behavior remains pinned to Omarchy v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`.

## Gaps and proposed shape

README/current release status still name v0.2.3, the future-version example now
names an already published version, and several capability pages retain earlier
source-only/deployment checkpoints. Record the actual published artifact hashes,
not those of the separately prepared local build. Describe workspace opt-in and
migration boundaries, positive user feedback and remaining native acceptance
without treating publication as installation or comprehensive validation.
Preserve historical release records while clarifying their point-in-time status.

## Safety and exclusions

The user explicitly approves documentation edits, commit and push. Do not change
published assets, tags, release visibility, source code, licensing, installed
configuration, packages, services or the running desktop. Do not force-push or
skip hooks. Keep raw metadata, logs, validation reports and backups under ignored
work/. No credentials or private inventory may enter the documentation.

## Tasks

- [x] Verify published v0.2.4 metadata, source commit and signed retained artifacts.
- [x] Back up affected documents and update current/historical status consistently.
- [x] Review documentation links, scope and remaining acceptance limitations.
- [x] Run the complete unit suite and working-tree whitespace checks.
- [ ] Commit and push only the reviewed documentation changes.

## Verification checkpoint

GitHub identifies v0.2.4 as latest, public and non-prerelease. Local and remote
peeled tags match `7fa27607f65f6c2ee54998756a8531e805056123`. All four retained
publication artifacts match GitHub's sizes/digests; signature, source export,
packaged source, extraction, bundle and artwork-exclusion checks pass. This is
the maintainer's fresh publication build, not the separately signed local build.
The README now names v0.2.4 and uses v0.2.5 only as a future-version example.

Relative documentation files/anchors and all 1,279 unit tests pass. Workspace
opt-in, positive tried-operation feedback and remaining physical hotplug/login,
Network, stock-machine and security acceptance boundaries remain explicit.
Publication artifacts/tags and the running installation are unchanged.
