# Prepare v0.2.3 and review old GitHub release retirement

## Goal and evidence

The user explicitly requests commit, push and release v0.2.3, followed by deleting
old GitHub releases. Ship the normal-action/wallpaper repair from plan 109 and
retained v0.2.2 publication documentation. Compare current main, GitHub releases,
publication tooling, private review bundle and tests. Omarchy remains pinned to
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; no new upstream imports are needed.

## Gaps and proposed shape

v0.2.2 is currently latest. No v0.2.3 remote tag or private publication workspace
exists. Prepare honest scope documentation, review all intended changes and
stage/commit/push normally after tests. Use the established interactive publisher
for a fresh artwork-free committed export. Signing-key/passphrase and final
publication prompts remain in the user's own terminal, never captured or bypassed.
Verify publication/tag/signature/assets after the publisher has completed.

GitHub currently lists v0.1.8, v0.1.9, v0.2.0, v0.2.1 and v0.2.2. "Old releases"
needs an exact deletion list and clarification whether Git tags are included.
Ask before irreversible deletion. Do not remove the current fallback before a
verified v0.2.3 is public. Deleting public assets breaks old download links and
removes a way to recover older versions; local installed rollback is separate.
Retirement metadata/assets must be backed up privately before approved deletion.

## Safety and exclusions

Private document pre-edit backups and evidence under
`work/release-023-preparation/`. No private keys/passphrases in tools, Git or
artifacts. No force push, hook bypass, Git config changes, package/native build
prerequisite installation, service/desktop/session/plugin/lock/VM changes.
Publication is not deployment, guest wallpaper rendering or native acceptance.
Never overwrite an existing tag/asset. Source/publication and approved release
retirement are separate checkpoints; do not infer tag deletion approval.

## Tasks

- [x] Obtain commit/push/release request and inventory versions/remote/main.
- [x] Back up scope documents, prepare v0.2.3 notes and review intended files.
- [x] Run tests, clean-source and whitespace/publication-scope checks.
- [ ] Commit and push approved main without force or hook bypass.
- [ ] Build/sign/publish through the interactive publisher and verify public assets.
- [ ] Confirm exact old-release/tag deletion scope and retain private backups.
- [ ] Delete only confirmed releases after verified v0.2.3 publication and verify remaining state.

## Prepared candidate

All 1185 tests and clean-source verification pass. Private report:
`work/clean-source/20261107T220507.430233Z/report.json`. Scope includes the
reviewed source/fixtures from plan 109 plus pending v0.2.2 publication follow-up
from plans 106–107 and analysis 108. The release notes retain v0.2.2 as current
until actual publication. No signing operation or old-release deletion has run.
The configured publisher key path is present; no private key was read. Native
pins, plugin ABI policy, public key and artwork exclusions are unchanged.
