# Publication checklist

Intended to be public does not mean ready to publish.

Before creating a remote or publishing:

- Local wallpapers/previews are ignored and must remain excluded. An existing
  private bundle can still contain them; source exclusion does not clear binary
  redistribution rights.
- Use the [third-party inventory](../THIRD_PARTY_NOTICES.md) and run the
  [clean-source workflow](clean-source.md) without existing work inputs.
- Editing a tracked document does not remove its older versions from Git history.
  The existing local commit must be reviewed separately; cleanup does not
  authorize history deletion, index changes, commits or a push.

- Project license: MIT (approved). Preserve copyright and attribution notices.
- Review every imported upstream file and asset for redistribution rights.
  The pinned Omarchy root MIT notice is retained, but Omapager-derived code,
  component authors, branded SVGs, datasets and fonts still need their own review;
  see [source/license evidence](shell-gate.md).
- Record source URLs, exact revisions, licenses, modifications, and notices.
- Exclude private snapshots, inventories, backups, local configuration, and logs.
- Inspect the complete candidate file set and Git history for secrets, personal
  paths, hostnames, corporate endpoints, and other private information.
- Review generated reports manually before sharing excerpts.
- Confirm all repository documentation and authored files are in English.
- Document actual support and test boundaries; do not advertise untested safety.
- Obtain approval for hosting, remote URL, and publication.

.gitignore reduces accidental inclusion but is not a security boundary.
No automatic upload, remote creation, secret-scanning service, or release is
part of diagnostic tooling.
