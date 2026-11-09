# Persist World Clock settings

## Goal and evidence

Persist Elsewhen cities and preferences across bar restarts. Compare the staged
panel with the vendored Omarchy 4.5.0 stable source pinned at
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Upstream writes its inline shell.json
entry; Omabuntu deliberately removed that hook in plan 038. This request replaces
that earlier process-only restriction, not the other exclusions.

## Gaps and proposed shape

The current persistSettings function updates only an instance-local object.
Add a shared QML settings owner, loaded before the first zone probe, and a Python
standard-library backend for settings/elsewhen.json under OMABUNTU_STATE_HOME.
Share updates across outputs; serialize writes and retain the newest pending
snapshot. Preserve city order, empty lists, people, home selection and preferences.
Validate bounded input, reject unsafe paths, back up previous bytes and record
prior absence before atomic private writes. Failed reads must not overwrite data.
Keep the upstream-derived panel and provenance checks reproducible.

## Safety and exclusions

No installation, deployment, bar restart, desktop changes or commit. No network,
system timezone changes, upstream shell.json writes, weather/profile fetching or
autostart changes. Do not import new upstream code or assets. Existing in-memory
cities cannot be recovered from a running process by this source-only change.
No Hyprland configuration changes are needed.

## Tasks

- [x] Implement and test the bounded settings backend and rollback records.
- [x] Integrate shared settings, startup ordering and serialized writes in QML.
- [x] Update packaging, derivation metadata and current capability documentation.
- [x] Run the complete unit suite and review the diff; leave deployment separate.

## Verification

- All 1196 unit tests passed, including 11 new persistence/adapter checks.
- Verified source derivation and staged metadata against the unchanged vendor.
- An isolated Bubblewrap/offscreen Quickshell check loaded the actual singleton,
  saved a city and preference through Python, then loaded both in a fresh process.
  No host display, buses or network were exposed. This is not native desktop
  acceptance or deployment.
- Reviewed the diff and checked whitespace. No installation, bar restart or commit.
