# Publication cleanup and clean-source reproducibility

## Goal

Prepare a smaller, understandable public source candidate without publishing,
committing, changing the running desktop or deleting local wallpapers. Explain
the existing local Git history separately from any GitHub publication.

## Evidence and gaps

- Git already has one local commit tracking six files and no configured remote.
  This request does not authorize deleting `.git`, resetting history or commits.
- Private `work/` contains superseded runtime builds, reports, releases and
  recovery backups. Retain the current verified runtime stage and recovery
  evidence; identify a bounded disposable set before deleting anything.
- Local theme wallpapers/previews have unresolved per-image redistribution
  rights. Keep the files locally but exclude both directories from Git. Their
  pinned origin metadata remains useful; Omarchy source is pinned to
  `03ff1eff3812933f7088484533784d2f63eaf19a` and must not be altered.
- Packaging currently requires those local image directories and installer
  preflight requires an imported WebP. Public source must work without private
  images, not silently redownload them. Use an authored tiny codec probe instead.
- Several tools and Make hard-code an old local build timestamp. Require an
  explicit verified `--build-dir`/`BUILD_DIR` for operations needing a runtime;
  retain harmless plan/help modes. Never pick an arbitrary latest directory.
- The public worklog is a machine-operation diary and README contains outdated
  login/asset status. Archive the full worklog privately before a concise rewrite.
- Third-party source and bundled-runtime obligations need a central notice.

## Safety and proposed shape

Back up every changed existing source/document before edits and retain an
ignored cleanup report. No package installation, desktop/config changes, services, runtime deployment,
reference-package edits, Git writes or publication. A one-time native clean-source
build may fetch only the already reviewed checksum-pinned runtime archives through
the existing builder; no new dependencies or unreviewed upstream imports.
Keep local image bytes and provenance, vendor source/licenses, current verified
build and repair/rollback evidence. Reversibly archive only identified superseded
builds after checking visible process arguments; preserve every original byte
and record original paths/inodes. This is organization, not disk-space recovery
or complete open-file reference proof. Permanent deletion of old builds/logs
requires separate approval. Do not use git clean.

Add focused regression tests for missing image assets, codec probe independence,
explicit build selection and ignored image paths. Run all unit tests and repeat
in a clean source export containing no Git-ignored images, caches or old work
contents. Check documented read-only commands and clear missing-build refusal;
this does not promise a full dependency installation or fresh OS desktop test.
Also exercise the native builder, stage checks, asset-free packaging and preflight
inside the new export using only that export's newly generated work contents;
never copy or reuse the original build/cache inputs.

## Tasks

- [x] Record baseline/backups and bounded local cleanup inventory.
- [x] Ignore local wallpapers/previews and make packaging/preflight asset-optional.
- [x] Remove fixed local build defaults and test explicit selection consistently.
- [x] Add Third-Party Notices and refresh README/public worklog and relevant docs.
- [x] Run local and clean-source-export verification without existing work inputs.
- [x] Reversibly archive superseded builds while retaining recovery material.
- [x] Summarize results, remaining publication gates and unchanged Git history.

## Results and limits

- Public candidate is approximately 293 files / 2.44 MiB, excluding 120 local
  image files. Every retained image still matches its recorded upstream Git blob
  checksum. The original operational worklog is preserved in a private backup.
- 542 unit tests pass locally and in an asset-free export with no old work
  contents. The repeatable source checker also passes its fixed CLI/refusal
  checks, including refusing missing-build development updates before live steps.
- A new contained native build used only newly fetched checksum-pinned archives.
  It passed the 32 isolated runtime checks and desktop, command-menu and picker
  fixtures. The documented Make release/preflight/plan commands and relocated
  release check pass with an asset-free bundle. No bundle was installed or started.
- Native preflight caught Qt rejection of a valid 38-byte 1x1 WebP fixture.
  Replaced it with an authored 16x16 lossless gradient; decode and preflight now
  pass. A private runtime directory supplied version-probe environment without
  exposing a live display/session. Original warnings and failed intermediate
  evidence are retained; no check was weakened.
- Two superseded generated build directories were moved to a private archive,
  recording original paths, inodes, sizes and absent visible argv references.
  This is reversible organization, not space recovery or proof of no open file
  descriptors. The retained original runtime stage still verifies. Large logs,
  release bundles, backups and repair/rollback evidence were not deleted.
- No Git staging, commit, history rewrite, remote or upload was performed. The
  existing local commit still contains the older tracked worklog. Full candidate
  and history privacy/secret review, unresolved image rights, exact Nayuki import
  revision reconciliation and any binary redistribution obligations remain
  explicit publication review items. A full fresh-OS test was not performed.
- Permanent pruning of archived build bytes or diagnostic logs requires a
  separate explicit deletion approval. No host configuration or service changes
  were part of this cleanup.
