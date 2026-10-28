# Remove the screen-lock lifetime limit

## Goal and evidence

Keep an explicitly requested screen lock alive until authentication or process failure, with no artificial lifetime limit. The user approved the source fix, regression test and backed-up local deployment, but not a live lock test.

The project helper and active installed helper are identical and pass `timeout=1800` to Python's subprocess runner. Python terminates the child when that timeout expires. Two historical lock records lack completion reports, consistent with this exception path, but do not independently prove the cause of each incident. No Omarchy source change or upstream behavior comparison is needed for this Python orchestration defect; the existing source baseline remains pinned at 03ff1eff.

## Gap and proposed shape

Remove only the timeout on the actual locker process. Preserve bounded preflight probes, session and version checks, static config checks and authentication behavior. Add mocked process tests for session lifetime and completion reporting. Deploy a narrow, backed-up helper correction to the active local release and update its file-integrity entry; preserve selectors, other release files and the running shell. Record deployment details privately, not in Git.

## Safety and exclusions

No lock activation, authentication test, PAM, permissions, security-policy, idle timer, service, package, compositor reload, logout or reboot changes. No new timeout, retry loop, supervisor or automatic unlock. No commit. Local installation verification does not establish functional authentication acceptance.

## Tasks

- [x] Add a regression test and demonstrate failure with the old timer.
- [x] Remove the locker lifetime limit while preserving bounded probes.
- [x] Run the full unit suite (566 tests pass).
- [x] Back up affected installed files and record their prior state.
- [x] Deploy the helper and matching manifest entry; verify installed integrity.
- [x] Update documentation and work log, without activating a lock.
