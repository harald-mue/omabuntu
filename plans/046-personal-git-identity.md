# Personal Git identity correction

## Goal and evidence

Replace the corporate author and committer identity in this repository's history
with the user-approved personal identity. A read-only audit found 16 reachable
commits: 13 use the corporate identity for both roles; three author identities
are already personal and one committer identity is GitHub. Only main exists;
there are no tags. Local main and remote main agreed before the operation.
No upstream desktop behavior changes; an Omarchy pin comparison is not relevant.

## Shape and safety

The user explicitly approved history rewriting, repository-local Git identity
configuration, and force-push with lease. Back up history, refs, Git config/index,
patches and uncommitted files privately under ignored work/. Rewrite commit
objects in an isolated mirror, changing only the selected identity and dependent
parent IDs. Preserve trees, messages, dates and other identities; remove invalidated
commit signatures. Verify every rewritten commit before moving main. Use an exact
remote-object lease for publication and verify remote main afterwards.

Do not commit the pending installer work, change global Git configuration, delete
backups, expose private inventories or reset the working tree. Existing clones
and cached old GitHub objects are not automatically cleaned by a history rewrite.

## Tasks

- [x] Audit identities/refs and create a private pre-change backup.
- [x] Rewrite and verify isolated history.
- [x] Set only repository-local author defaults and move main without checkout/reset.
- [x] Publish with exact force-with-lease and verify the remote.
- [x] Verify pending file preservation, run tests, and update the work log.

## Result

All 16 trees, commit messages and identity timestamps were verified unchanged;
13 corporate author/committer identities were replaced. The GitHub committer
identity was retained. No commit signatures needed removal. Remote main was
verified after publication. All 23 pending files other than the deliberately
extended WORKLOG.md remained byte-for-byte unchanged; the staged patch was also
preserved. 800 tests and whitespace checks passed. No pending project changes
were committed. Private backups retain the original identity for recovery only.
