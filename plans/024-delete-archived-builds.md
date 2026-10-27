# Delete the two superseded archived builds

## Goal and approval

Permanently delete only the two superseded generated builds archived by plan
023. The user explicitly approved deleting these old builds after the prior
reply identified their scope and approximate size. Do not create another copy
of the build contents: permanent removal, not further archival, is requested.

## Evidence and safety

Use the private archive inventory from plan 023 to validate the exact two paths,
original directory inodes and device. Recheck visible process arguments and
verify both retained runtime stages before and after deletion. Upstream behavior
is not changing; no new source import or upstream comparison is needed.

Keep metadata and deletion evidence privately under ignored work/. Back up the
existing worklog and archive metadata before updating them. Preserve all other
builds, release bundles, image assets, source/document backups, diagnostic logs
and recovery evidence. Refuse unexpected paths, symlinked parents, mount points
or visible process references. Use symlink-resistant deletion only on the two
validated archive roots. No desktop/service, package, Git index, commit or
publication changes are authorized.

## Tasks

- [x] Validate the bounded archive inventory and retained runtime stages.
- [x] Record private before-state and delete only the two approved archive roots.
- [x] Verify retained stages, update the worklog and run the full unit suite.

## Results

Both approved archive roots were removed (approximately 2.42 GiB of logical build
data). Both retained runtime stages verify before and after deletion. The full
suite passes all 542 tests, and git diff --check is clean. Private metadata and
worklog before-state are retained; no additional build-content backup was made.
No other artifacts or host configuration were removed or changed.

Deletion is irreversible; the inventory records what was removed but cannot
restore the deleted build contents. The separate retained verified builds remain
available. Process-argument checks are not proof of all possible open file uses.
