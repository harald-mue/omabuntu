# Resume release signing after interactive timeout

## Goal and evidence

The real v0.1.0 run passed tests, committed preparation, built all native
components and produced an archive/checksums. It stopped during the second
passphrase prompt because SSH signing inherited the generic 120-second command
timeout. A retry correctly refused to overwrite the existing release workspace.

## Shape and safety

Remove timeouts only from interactive SSH key/signing prompts, keeping bounded
network/build/verification commands. Add explicit `make release-resume VERSION=...`
for a complete unsigned archive from HEAD or a verified ancestor. Require a clean
checkout; newer committed fixes can be pushed on main without falsely including
them in the original bundle. Verify archive/metadata
checksums, target/version/commit, original Git export and packaged source before
signing. The safe Tar data filter was also found to add owner-write permissions
to read-only manifest files; restore only reviewed regular-file modes after
extraction and reject paths beneath archive symlinks. Reuse no arbitrary latest
build. Preserve existing artifacts and sign in
a fresh private attempt directory. Recheck signatures and archive extraction and
require publication confirmation. Resume does not commit pending changes: explain
that they are excluded from the existing artifact. Refuse existing tags, moved
HEAD, incomplete bundles or changed evidence. Do not implement post-push/draft
recovery or change desktop/install behavior. No upstream pin comparison applies.
Back up affected paths privately before editing. No signing, publication, commit,
push, package or desktop action during this implementation.

## Tasks

- [x] Add untimed interactive key operations and explicit verified signing resume.
- [x] Document retry boundaries and add regression tests.
- [x] Validate existing unsigned artifacts read-only and run the full suite.

## Verification

811 tests passed, including archive mode preservation, symlink-parent rejection,
ancestor-commit resume without build/commit, interactive signing without timeout,
signature reuse and failed-attempt preservation. The existing unsigned v0.1.0
archive, metadata, source export and bundle were successfully checked against
the recorded commit without signing or publishing. The original build outputs
and checksums were not changed. Real signing and publication still require the
user's terminal and confirmations.

## User-selected clean restart

The user preferred a full new build rather than signing resume. Verified that no
local/remote version tag or GitHub Release existed, moved the failed workspace
to a uniquely named private archive under work/, and verified its original
artifact hashes unchanged. No build evidence was deleted. The original release
workspace path is free for a fresh `make release VERSION=0.1.0` using the fixed
source. Resume remains optional, not required for a clean rebuild.
