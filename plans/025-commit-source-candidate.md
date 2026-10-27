# Commit the reviewed source candidate

## Goal and approval

The user requested a commit of the changes for the named GitHub repository with
an explicitly supplied author email. Create one local Conventional Commit using
the authenticated account's display name and the requested address, without
persistently changing Git configuration. A push, remote creation, history rewrite
and public release remain outside this local commit step.

## Evidence and gaps

- The authenticated GitHub account matches the repository owner and has push
  permission. The target repository currently reports private visibility.
- The local repository has one existing commit, six tracked files and the
  reviewed source candidate still largely untracked; ordinary git diff is not
  a complete inventory.
- Plan 023 excludes images and private work data. Its clean-source build and
  package verification passed; plan 024 removed only two approved old builds.
- Omarchy source provenance remains pinned to
  `03ff1eff3812933f7088484533784d2f63eaf19a`. No upstream behavior or imports change.
- The complete candidate and existing history still need a bounded local
  secrets/privacy check. No dedicated secret scanner is installed; disclose the
  limits of standard-library pattern checks rather than claim security clearance.

## Safety and proposed shape

Record Git/index state and validation evidence privately under ignored work/.
Review an explicit list of regular non-ignored source files; reject private
paths, local images, generated binaries and symlinks before staging. Do not
blindly stage the workspace or print potential secret values. Stop for actual
secret/private-data findings instead of committing them or rewriting history.
Preserve licenses, all prior work, hooks and existing history. Use command-local
identity settings for the requested commit, not global/local config edits.
No desktop, service, package, dependency or remote changes.

## Tasks

- [x] Verify GitHub account/repository access read-only and existing Git state.
- [x] Inventory and scan current source candidate and existing Git history.
- [x] Run tests, clean-source checks and inspect the exact staged file list.
- [x] Validate command-local author/committer identity and commit verification contract.

## Commit execution and verification contract

After preparation, create the authorized local Conventional Commit. Verify its
parent is the preserved existing HEAD, author and committer match the requested
identity, committed files equal the reviewed staged seal, private paths/images
are absent and no source changes remain unstaged. Record the resulting commit
ID and outcome privately and report them to the user. The final commit ID cannot
be embedded in its own contents. Do not push or configure a remote in this step.

The local pattern check found only English UI text, systemd template-unit names
and authored sandbox HOME paths; all were reviewed. It is not an exhaustive
secret scan. Runtime/native checks from plan 023 remain separate from this
commit's source-only unit and clean-source verification.

The staged source candidate contains 295 files and no binary/image/private-work
files. Removed three pre-existing authored whitespace defects during staging;
the QR generator's original upstream whitespace and license remain byte-for-byte
unchanged. Whitespace validation excludes only that preserved third-party file,
not hooks or content verification. Both author and committer resolve to the
user-requested identity through process-local settings.
