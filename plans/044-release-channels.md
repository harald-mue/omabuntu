# Release channels

> **SUPERSEDED — not valid for current implementation.** The local dev/stable
> mechanism, files and CLI options have been removed by
> [plan 048](048-remove-release-channels.md). Development uses source checkouts;
> published distribution uses signed GitHub Releases under
> [plan 045](045-github-release-distribution.md). The design and checked tasks
> below are historical records only, not supported usage instructions.

## Goal

Let a later update select `stable` or `dev` without tracking a moving branch.
The user asked for channels so other people can update simply. This plan adds
the local channel format and resolver only. It does not publish a remote,
create a GitHub release, or redistribute artwork.

## Evidence

Current releases are immutable directories checked by `user_install.verify_bundle`.
`release_update.review` already requires an explicit bundle path and approval
digest. `guided.digest` of the release metadata is the existing content pin.
A checksum is not a publisher signature. Private bundles may contain images
that are not cleared for redistribution.

## Shape

A channel file names only `stable` and/or `dev`. Each entry stores the release
version and the SHA-256 of its verified metadata. It stores no URL, local path,
image, or signature claim. A resolver finds `RELEASE_DIR/<version>`, verifies
the bundle, and refuses a digest mismatch. The existing update review then uses
that directory. Writing a channel file is explicit and does not install or start
anything.

## Exclusions

No network fetch, no remote publication, no artwork bundling, no APT changes,
and no claim that the channel file is signed. Rollback remains the previous
installed release, not an implicit older channel tip.

## Tasks

- [x] Add the channel file schema, resolver, and explicit writer.
- [x] Let `--update --channel` review the resolved local release without applying
  unless `--apply` is also present.
- [x] Test mismatch, symlink, unknown channel, and no-network behavior.
- [x] Document that publication is still a separate approval.
