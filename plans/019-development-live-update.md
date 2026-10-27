# Development live update through Make

## Goal and evidence

Provide one explicit Make target to package current source, verify and deploy a
fresh immutable release, refresh managed Hyprland settings and autostart files,
reload compositor configuration and restart only the owned Omabuntu shell.
Existing update reuses bundles and ignores stop failures. Plan 018's deployer
can partially write before refusing config and does not reject symlinked parents.
Fix those defects before using it in the combined workflow.

Hyprland target is 0.56.2 (efb50993780079460b0cbed1363e2166a2de1d9f).
Use the existing documented hyprctl reload interface; this is not a compositor
restart. Attempts to refresh official wiki/source references via GitHub returned
HTTP 404 in this session. No new Hyprland configuration syntax was introduced;
0.56.2 live acceptance remains a separate check, not established by mock tests.
Omarchy source is not changed or imported by this orchestration request.

## Shape and constraints

- Add explicit plan/apply/remove, reload, restart and development targets to Make.
- dev-update always prepares a fresh version (timestamp default), verifies before
  stopping, deploys via current checkout manager, refreshes managed settings and
  the autostart unit/helper, reloads configuration and starts the owned shell.
- Sequential recursive Make calls must remain ordered even under make -j.
- Fail closed on stop/install/deploy/reload errors. No automatic rollback of a
  partly completed multi-step operation; report that limitation.
- Reject unsafe config paths before writes, show unified diffs, back up changed
  and removed files. No unsupported claims about a confirmed renderer bug.
- Do not run these host-changing targets during implementation. No sudo, package
  installs, plugin rebuild/load/unload, logout, compositor restart or Git actions.
- Runtime build uses the explicitly selected verified build stage; this does not
  rebuild Quickshell/C++ dependencies or replace arbitrary user config.

## Tasks

- [x] Harden settings deployer and add refusal/rollback regression tests.
- [x] Add checked live reload helper and tests.
- [x] Add sequential Make workflows and tests, including fresh release behavior.
- [x] Update user documentation and worklog with scope and failure behavior.
- [x] Run python3 -m unittest discover -s tests -v (505 tests passed).

## Result

Managed templates are also recorded in newly packaged releases. Development
orchestration tests use stub tools, including parallel Make ordering and failed
reload short-circuiting. No live deployment, service change or reload was run.
The earlier claim that some 0.56.x start paths ignore the splash flag is not
proven; corrected the managed template and current user documentation accordingly.
