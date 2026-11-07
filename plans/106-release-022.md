# Prepare and publish Omabuntu v0.2.2

## Goal and evidence

The user explicitly requested commit, push and release v0.2.2. Ship the native
compatibility policy and actionable diagnostics from plans 104–105 through the
existing signed, artwork-free publisher. Compare v0.2.1, the reviewed worktree,
release tooling, remote version availability and contained verification. Omarchy
components remain pinned to v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; no new upstream imports or plugin
source targets are part of this release.

## Gaps and proposed shape

v0.2.1 remains the latest published release and still contains exact native
version checks. Prepare 0.2.2 scope/status documentation, rerun tests and clean-
source checks, review intended files and commit/push after the user's explicit
approval. Use the established interactive publisher to build from that committed
export, sign locally, confirm public publication and verify tag/assets/signature.
Private key/passphrase entry stays in the user's terminal; do not capture or
work around its interactive signing/publication gates.

## Safety and exclusions

Back up affected documents under ignored work/. No package/source installation,
privilege, desktop deployment/restart, session transition, service activation,
plugin build/load, lock/authentication change, key/config change or force push.
Do not replace v0.2.1 or existing tags/assets. Keep private evidence, review
bundles, logs and artwork out of Git and public artifacts. Preserve failed build
or signing evidence. Preparation/commit/push is not publication or fresh-VM,
plugin, lock recovery, GNOME or real update-pair/security acceptance.

## Tasks

- [x] Obtain explicit commit/push/release approval and check version availability.
- [x] Prepare v0.2.2 scope documentation and review the publication candidate.
- [x] Run full tests, clean-source and whitespace checks.
- [ ] Commit approved sources and push main without force.
- [ ] Build fresh isolated artwork-free assets and sign through the publisher.
- [ ] Publish after confirmation and verify public tag, assets and signature.

## Initial preflight

Main is at the v0.2.1 documentation commit with the compatibility implementation
uncommitted. Remote main matches local HEAD. No local/remote v0.2.2 tag, GitHub
release or publication workspace was found. Publisher tools and the signing-key
path environment setting are present; no private key was read. v0.2.1 remains
public/latest until v0.2.2 publication is actually complete.

## Prepared source verification

README and release/operator documentation now identify v0.2.2 preparation without
claiming public availability. The scope explicitly preserves strict plugin ABI/
source/build/receipt checks, optional titlebar exclusions, baseline/transition
contracts and outstanding native acceptance. All 1158 unit tests, isolated clean-
source checks and whitespace checks pass. The contained packaging/import evidence
from plan 105 remains valid; this is not a full fresh build or VM acceptance.

The 28-file candidate includes implementation/tests, compatibility documentation,
plans 104–106 and release scope updates. A limited private-key/token/machine-home
pattern review found no matches; this is not comprehensive secret/history/license
acceptance. No new third-party code or assets were imported. Backups and current
review/test reports remain under ignored `work/release-022-preparation/`.
Commit/push are explicitly approved; the interactive publisher still retains the
user's signing and final publication confirmation gates.
