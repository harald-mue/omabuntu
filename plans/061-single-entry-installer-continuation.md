# Single-entry installer continuation

## Goal and evidence

Keep install.sh as the only user-facing installation/resume entry point. The
reported published flow aborted the application when optional plugin packages
were blocked, then suggested a temporary-cache --plugins command even after the
user declined those packages. Generic profile preparation is already offered by
the same installer and must remain separately approved.

Compare published_install.py, setup.system_stage, bootstrap_packages.prepare and
the published-flow tests. Retain pinned Hyprland 0.57.0
0aa6745f705f2c4b0a5004eb019ef76e5bbdb426 and plugin
d2427d4d15b36df40468f5a58bbd67cdba19835d behavior; this changes orchestration,
not the reviewed upstream configuration. Preserve earlier uncommitted fixes in
plans 059 and 060.

## Proposed shape and gaps

Review optional plugin packages without mutation first. A blocked review can be
explicitly deferred while the prebuilt application proceeds. Never swallow a
failure after attempting package application. Recheck installed prerequisites
after the package step so declining its inner consent is not treated as success.
Do not offer a new plugin build when prerequisites were deferred; still allow a
verified existing healthy build to be reused with separate live-load consent.
Replace user-facing temporary-cache subcommands with same-installer continuation
instructions. Explicitly explain skipped profile preparation and normal Enter.

## Safety and exclusions

Keep PPA/runtime/font, deployment/restart, profile, login and live-plugin approvals
separate. Do not loosen additive-only APT policy or accept unknown key sequences
as Yes. No system upgrades, security-policy changes, automatic logout/login,
service starts, desktop edits, package installation, signing or publication in
this implementation task. Back up affected repository files under ignored work/.
A local installer-source fix cannot change an already signed public archive;
commit and a new release remain separate approval gates. No new upstream assets
or source are imported.

## Tasks

- [x] Back up affected files and implement optional package review/defer flow.
- [x] Preserve healthy build reuse and suppress unready build/subcommand advice.
- [x] Add flow regressions, including blocked/deferred and failed apply paths.
- [x] Update user-facing documentation and run full verification.
- [x] Report the sole-entry workflow and existing-release limitation.

## Result

The published flow now creates a private read-only optional package plan first,
asks before deferring blockers, applies only the reviewed saved plan and checks
whether prerequisites actually became available. Attempted apply failures remain
fatal. Deferred prerequisites suppress new builds but do not prevent verified
healthy-build reuse. Same-entry continuation replaces internal plugin subcommand
advice, and skipped profile preparation explains normal Enter input.

All 970 unit tests passed, including the earlier parser/runtime fixes and new
single-entry, private-directory, package-deferral and failed-apply regressions.
Clean-source and whitespace checks passed. No package/desktop changes or Git
publication operations were performed. End-to-end clean-VM/login acceptance and
availability in a new signed release are still outstanding.
