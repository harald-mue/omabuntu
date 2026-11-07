# Validate the signed online metadata check without downloading an application

## Goal and evidence

The user approved a metadata-only online check after confirming terminal launch
and pre-network cancellation. Exercise the deployed Update > Omabuntu review
logic against the real public release service. The menu placement remains based
on Omarchy v4.5.0 commit `ac2690cd7be4f47e4a255f5e2e78d904d436b068`; upstream
scripts are not executed. Trust the verified installed publisher public key and
signed checksums/metadata, not the GitHub discovery hint alone.

## Gaps and proposed shape

Native terminal invocation has user confirmation; real signed-service discovery
and the local-derivative refusal still require evidence. Use a private diagnostic
under ignored work/ to verify the installed bundle and updater source/resource
identity, then invoke the same review function with permission limited to the
first metadata question. Allow only the four discovery/metadata fetches. Block
archive download/apply callbacks unconditionally. Retain partial failures and
compare selected/running identity before and after.

## Safety and exclusions

Read the installed application/state needed for this explicitly approved check;
write diagnostic reports only under private ignored work/. No existing desktop
configuration is edited, so no configuration backup/restore transaction applies.
Keep downloader/signature timeouts and record failures. Do not start a terminal,
fetch an application archive, extract a candidate, invoke installation/preflight,
change preferences/selectors, restart/reload processes, install packages, activate
services, commit or publish. No unattended mode is added to the production runner.
This diagnostic does not establish actual update-pair/recovery, shell-parent-exit,
GNOME, fresh-machine or full security acceptance.

## Tasks

- [x] Verify selected/running bundle, installed updater identity and trust key.
- [x] Check live signed metadata with strict metadata-only network boundaries.
- [x] Confirm expected local-release refusal and unchanged selection/process.
- [x] Update acceptance documentation and run unit tests/diff checks.

## Result and remaining boundaries

The installed updater/resource closure matched the reviewed sources and the
selected bundle verified intact. The real public v0.2.0 signature and metadata
verified against the installed publisher public key. The review function returned
`local-release-blocked` for the private derivative, preserving unpublished fixes.
Exactly four metadata/discovery fetches completed, with no application archive
request, candidate extraction, preflight, apply or restart. Current/previous
selectors, verified bundle metadata and running process identity were unchanged.

The diagnostic exercised reviewed code matching the deployed payload; it did
not launch the native terminal or add a production unattended option. Private
request records, verified metadata and before/after evidence are retained under
ignored `work/update-menu-101/`. Documentation backups are retained there too.
All 1130 unit tests and `git diff --check` passed. A real public-version update
pair/self-restart and failure recovery still require separate approval and
acceptance. No desktop mutation, commit or publication was performed.
