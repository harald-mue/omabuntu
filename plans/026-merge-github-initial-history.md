# Preserve both histories and push main

## Goal and approval

The user explicitly approved merging the local project history with GitHub's
independent initial commit, preserving both copyright notices and then pushing
main without force. Continue using the requested author and committer identity
only in the commit process; do not persistently change Git identity settings.

## Evidence

The local source commit is cf12b53 and the fetched remote initial commit is
59b56e9. They have no shared ancestor. The remote tree contains only an MIT
LICENSE naming Harald Müller; the local MIT LICENSE names Omabuntu contributors.
The permission and disclaimer text is the same. Preserve both notices and all
existing commits rather than rebasing or replacing either root history.

No upstream behavior or imported source changes; the Omarchy pin and third-party
licenses remain unchanged. Prior source-only review excludes images, work data
and binaries, and its bounded scanner limitations remain documented in plan 025.

## Safety and proposed shape

Record both tips, the index and affected file before-state privately under work/.
Start an explicit no-commit unrelated-history merge. Resolve only the expected
LICENSE add/add conflict by retaining both copyrights under the MIT text.
Unexpected conflicts, concurrent remote changes or failed checks require a stop,
not a force push, hook bypass or history rewrite. Add only the license resolution,
this plan and the worklog to the merge result. Run unit and clean-source checks.

Create one Conventional merge commit, verify its two parents and the complete
source-only tree, then push normally and confirm the remote tip matches locally.
Do not change repository visibility, create a release, deploy anything or alter
images, desktop/services, packages, backups or runtime stages.

## Preparation tasks

- [x] Record and validate both tips, clean source state and private backups.
- [x] Merge without committing and resolve only the expected license conflict.
- [x] Run tests and clean-source verification; inspect staged source-only changes.
- [x] Validate the commit/push execution contract and requested identity.

## Execution contract

After preparation, commit with local and fetched remote tips as unchanged
parents. Preserve the original MIT permission/disclaimer and both copyright
notices. A plain push must fast-forward the remote; never use force. Verify the
actual remote commit, working tree and excluded private paths afterward. Record
commit and push outcomes privately and report them to the user; do not claim a
push before Git and the remote confirm it. No extra follow-up commit is needed
to embed a commit's own ID or its later push outcome in these source files.
