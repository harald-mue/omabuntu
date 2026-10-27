# Login integrity and workspace persistence

## Goal

Fix the repeated login startup failure and persist/restore floating, tiling
(dwindle) and scrolling per workspace, following the pinned Omarchy behavior.

## Evidence compared

- Read-only user-service journal: the latest login fails with `Release identity,
  scope or integrity differs`; ExecStartPre succeeds. This is not the previous
  instance-lock readiness race. A subsequently approved read-only comparison
  confirms exactly three extra Python cache files, with no missing or changed
  manifested files. The installed manifest matches the original packaged one;
  the previous release is intact. No host files have been changed.
- `Installation.restore_wallpaper` invokes a packaged Python helper without
  disabling bytecode generation. That helper imports sibling modules and can
  add `__pycache__` files to the sealed release. The regular shell and lock
  paths already disable bytecode, but this new startup path does not. Reproduce
  this mechanism inside workspace fixtures before calling it fixed. The later
  approved installed comparison confirms this precise mechanism on the host.
- `workspace_modes.EVAL` uses an ordinary Python string with Lua `"\n"`
  literals: Python emits literal newlines inside short Lua strings, invalidating
  the whole eval before any mode or file change. Existing tests check substrings
  rather than executing Lua.
- Omarchy commit `03ff1eff3812933f7088484533784d2f63eaf19a`, reviewed toggle
  in `vendor/omarchy/bin/omarchy-hyprland-workspace-layout-toggle`, saves only
  applied modes, removes the default override and reports save failures.
- Target compositor is Hyprland 0.56.2. Retain existing documented Lua APIs;
  check versioned official source/docs before any configuration changes.

## Gaps and proposed shape

- Prevent bytecode writes on wallpaper restore, pass the actual state root,
  retain strict manifest verification, and report bounded manifest differences
  without printing contents. Do not silently ignore unexpected files.
- Execute generated Lua in isolated tests with stubbed compositor bindings;
  correct escaping and make save failures explicit. Use atomic file replacement
  so a partial write cannot destroy previously saved modes.
- Align shell state-file lookup with the manager's actual state root and XDG
  fallback; synchronize the in-memory saved map immediately after success.
- Restore floating for already mapped windows as well as future open events,
  and keep the active glyph responsive when saved state finishes loading.
- Update documentation and worklog, retaining earlier uncommitted work.

## Safety constraints and exclusions

No packages, privileged actions, service activation/reload, Hyprland config
changes, logout or commit. The user explicitly approved the backed-up cache
cleanup, corrected local release installation, Omabuntu-only start and workspace
verification. Other desktop changes remain excluded. Tests and reports stay in
ignored workspace fixtures. No upstream imports, installer execution, boot/security or
corporate-agent changes. A repair deployment needs explicit user approval,
backups and recorded previous state. Do not reseal a changed installed release
or weaken its integrity checks. Session lifetime stays untimed and unsupervised.

## Tasks

- [x] Add red regression coverage for wallpaper integrity and executable Lua.
- [x] Correct startup helper environment and integrity diagnostics.
- [x] Correct persistence and asynchronous restore/state handling.
- [x] Run full unit suite and document results and remaining host acceptance.
- [x] Obtain approval and perform targeted read-only installed-manifest diagnostics.
- [x] Obtain separate approval for a backed-up repair deployment.
- [x] Execute the approved repair with backups and manifest/process rechecks.
- [x] Verify installed start/restart, integrity and workspace persistence.
- [x] Verify a real login only with user involvement (user confirmed it works;
      read-only service status also reports a successful login hand-off).

## Result

The isolated regression first reproduced the next-start integrity failure after
wallpaper restore and Lua's `unfinished string` parse error. Both pass with the
fixes; manifest verification still rejects any extra files. Full unit suite:
524 tests passed. The existing sandboxed offscreen desktop checker now tests
late state-file delivery, active glyph synchronization and two queued existing
windows with a stub compositor; it reports `isolated-compile-passed`. Its first
run caught an ordering bug (the saved-map change preceded the floating-grant
change); restoration now listens to the grant change. Timeout output is retained
in private reports instead of being lost to a traceback. No host files or
services were changed. The approved installed comparison confirms three extra
cache files only, an intact previous release, no pending deployment transaction,
a stale process record and no saved workspace-layout file. It also confirms the
installed switcher carries the Lua syntax error. Private machine details are in
`work/plan-021-installed-audit.json`, not this plan. Real-login acceptance and
repair deployment remain pending at the end of the read-only phase.

### Deployment compatibility finding

The approved first deployment restored integrity and installed successfully,
but its startup guard rejected the legacy `current/` directory's inherited
permissions. The state parent is already owned and private, so the compatibility
fix preserves existing child-directory modes and contents, rejects symlinks and
foreign ownership, and creates new child directories with mode 0700. A new
regression test reproduced the failure before this fix. Repackage as a fresh
immutable version; do not patch the installed manager or chmod host preferences.

## Approved repair sequence

1. Prepare and preflight a fresh corrected local bundle inside `work/`.
2. Recheck the exact manifest delta and process identity immediately before any
   host writes; stop if anything besides the three audited cache files differs.
3. Back up the extra cache files and their modes plus affected selectors,
   launcher and state preconditions. Remove only those three extra files and
   require the old selected release to pass the unchanged integrity check.
   Do not rewrite the manifest or modify any manifested release file.
4. Install the fresh release through the checkout manager and its normal
   transaction/backup flow. Keep the independently verified older release as
   an explicit recovery option; the formerly selected development release still
   contains the old startup defect and is not a preferred runtime rollback.
5. With explicit live-start approval, start only Omabuntu through the existing
   session-lifetime grant. Verify release integrity after startup and after a
   shell-only stop/start, and check that workspace presses write valid state.
6. Do not reload Hyprland, change its config, reactivate systemd, install
   packages or log out as part of this repair. A genuine next-login check stays
   user-operated. Previously unsaved workspace choices cannot be recovered
   from a file that never existed.

## Completed approved deployment

Prepared and preflighted fresh immutable bundles. Under the normal control lock,
rechecked the exact three-file delta, copied and verified backups of the extra
caches plus affected launcher/state files and selector metadata, removed only
the extras and passed the original manifest unchanged. Installed through the
normal manager transaction flow; no manifested installed file was patched.

The first candidate exposed the legacy child-directory permission guard issue
above before shell creation. Added a red compatibility regression and a symlink
refusal regression, fixed source without chmod, and packaged/preflighted/installed
a new immutable candidate. All 526 unit tests pass. The final candidate starts
successfully and restores the recorded wallpaper. The running shell has the
explicit untimed session grant.

Approved live verification used only an existing empty workspace, guarded
against any windows appearing before each eval. Scrolling was reported by the
compositor and saved; floating was saved and survived an Omabuntu-only stop/start;
dwindle restored the original effective layout and removed the temporary saved
override. Other saved modes and application geometry were unchanged. The release
passes strict verification after both starts and after cleanup, with no bytecode
files and no runtime error markers. This does not claim visual/window-placement
acceptance or an actual fresh login.

The installed managed Hyprland snippet (including the saved-scrolling loader),
login unit and readiness helper match the reviewed templates. No config reload
or systemd write was needed. The login unit is still enabled; its displayed
failed state remains the historical pre-repair launcher failure because this
repair deliberately did not reactivate it. The rollback selector was backed up
and set to the independently verified last-known-working older release, not the
failed intermediate candidate. Private backup paths, manifests and verification
results are under the repair case referenced by
`work/plan-021-active-repair.json`. The user subsequently confirmed the actual
next login works, and the login service reports success. The separate remaining
wallpaper text is investigated in plan 022.
