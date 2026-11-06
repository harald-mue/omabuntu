# Create the private bootstrap work root before nested directories

## Goal and evidence

Fix the v0.2.0 isolated release build failure before runtime compilation. Compare
`bootstrap_build.apply`, `user_install.private_directory`, the strict runtime
builder check and the failed exported tree's directory modes. The failed tree
has an owned non-symlink work directory with mode 0775, while work/bootstrap is
0700. Path.mkdir(parents=True, mode=0700) protects only the final directory;
implicitly created ancestors use the process umask. Existing cached checkout
builds hid this fresh-export ordering bug. No Omarchy behavior or pin changes.

## Shape and safety

Explicitly create/validate root/work as an owned private directory before
root/work/bootstrap. Preserve refusal of existing public/group-accessible or
symlinked paths; do not chmod them into acceptance or weaken runtime checks.
Test a truly fresh root under a permissive umask and refusal before build/font
operations for unsafe existing roots. Correct the misleading artwork message
when artwork=False. Back up affected repository paths before edits.

No edits to the failed release tree/artifacts, key handling, package changes,
privileged commands, desktop changes, service actions or publication. Preserve
failed evidence and require a reviewed new commit and fresh build; signing-only
resume cannot recover incomplete build artifacts. Ask before committing the fix.
Any same-version retry must first verify no publisher process/tag/release exists
and preserve the old workspace at a fresh private backup path, not delete it.

## Tasks

- [x] Diagnose fresh-export directory modes and parent creation ordering.
- [x] Implement private-root initialization and honest artwork-free logging.
- [x] Add regression coverage for fresh permissive-umask and unsafe existing roots.
- [x] Run full tests, isolated clean-source checks and diff checks.
- [ ] Obtain fix commit approval and document safe fresh-build recovery.

## Verification and recovery status

The original-source control fails the new fresh-root regression under both
umask 0002 and 0022, confirming the test covers the observed ordering bug.
The fixed source passes all 1086 unit tests, isolated clean-source checks and
`git diff --check`. Existing nonprivate roots are refused without changing their
modes, and symlinked roots are refused before font/runtime operations. Source
backups and logs remain privately under ignored `work/private-build-root-091/`.

No v0.2.0 local/remote tag or GitHub Release was found. On the user's cleanup
request, verified that no publisher/build process was active and archived the
incomplete workspace into a unique private directory under ignored
`work/release-build-archives/`. A private transaction records the original path,
mode/owner and archive destination. Nothing was deleted or chmodded; the
`work/publish/v0.2.0` path is now free.

The fix still requires commit approval before a fresh
`make release VERSION=0.2.0`. Do not use signing-only resume or edit/chmod the old
exported source to bypass checks; the new source commit must be included in the
release archive.
