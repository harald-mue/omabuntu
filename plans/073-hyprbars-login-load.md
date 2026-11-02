# Load hyprbars automatically at login (receipt-driven managed snippet)

## Goal

The floating-workspace titlebar plugin (hyprbars) is loaded only by an
interactive `omabuntu-hyprbars-repair` (`hyprpm reload`) after each boot.
Every fresh Hyprland start since the 0.57.0 upgrade begins without the
plugin, so the titlebar buttons are absent until a manual repair runs.
Make the plugin load automatically at login again, through the
installer-owned plan-018 managed snippet, and ship that fix in the
published installer so `curl … install.sh | bash` repairs it.

## Evidence compared

- Running compositor: Hyprland 0.57.0, commit
  `0aa6745f705f2c4b0a5004eb019ef76e5bbdb426`, started 2026-11-02 08:37:57.
- Plugin pin (unchanged): `hyprwm/hyprland-plugins` `d2427d4d15b36df40468f5a58bbd67cdba19835d`,
  library `/var/cache/hyprpm/muha/hyprland-plugins/hyprbars.so`
  (SHA-256 `f5a1d4aeed89fbfbbabc3e6b51df72a55ebdc9a78036976c8942bfb835c664f6`),
  receipt `~/.local/state/omabuntu/hyprpm.json` (`activated: true`).
- Comparison source: local Hyprland 0.56.2 checkout
  `efb50993780079460b0cbed1363e2166a2de1d9f` (`work/hyprland-headers/hyprland`).
  Omarchy visual reference `03ff1eff3812933f7088484533784d2f63eaf19a` is
  unchanged by this plan.
- Live session evidence (2026-11-02): the boot log of the running
  compositor contains zero plugin/hyprbars lines and zero Lua/config
  errors (`hyprctl configerrors` empty), while `hyprctl plugin list` and
  `/proc/12231/maps` show hyprbars mapped — from the 08:38:22
  `omabuntu-hyprbars-repair` transaction, not from login. A second repair
  ran at 08:37:05 against the previous compositor instance.
- 0.56.2 source mechanics (`src/config/lua/ConfigManager.cpp`,
  `src/plugins/PluginSystem.cpp`): the config dir is on `package.path`
  (`require("omabuntu-managed")` resolves); `hl.plugin.load` during a
  config pass registers the path; `updateConfigPlugins` then loads new
  paths (de-duplicated by path), unloads config plugins that disappear,
  and logs ERR plus a notification overlay on load failure. A handler-time
  registration is wiped by `reinitLuaState()` before any pass reads it —
  the plan-020 finding that makes the `hyprland.start` handler dead code.
- Deployed state: `~/.config/hypr/omabuntu-managed.lua` (installer-owned,
  plan 018) loads `~/.local/lib/omabuntu/hyprbars.so` — the 0.56.2 build
  from 2026-10-25 — at every config load. On 0.57.0 that library fails the
  compositor's version check and nothing loads. The private
  `~/.config/hypr/hyprland.lua` additionally carries a `hyprland.start`
  handler (added 2026-11-01) that calls `hl.plugin.load` from the handler —
  dead per the mechanism above.
- Published flow: signed release v0.1.8 ships the same stale managed
  template. Today's two installer runs (08:36 and 08:38, downloads
  `v0.1.8-bjwxdawj`/`v0.1.8-ylbkkn5t`) each ended in a live repair only;
  neither persists a login load. The guided session stage on a private
  profile reports "kept, not replaced or merged".

## Decision gate result (task 1, 2026-11-02)

Source review of the pinned 0.57.0 tarball
(`work/source-cache/Hyprland-0aa6745f….tar.gz`, SHA-256
`f121d86cc9c1441bdb4eece6340f0269ba3c661ba6adf9e2121f8aa9522f1482`,
extracted to ignored `work/hyprland-057-review/`) against the 0.56.2
checkout:

- `hlPluginLoad`, its registration, `updateConfigPlugins`,
  `loadPluginInternal`, `phase1Load` (package.loaded clearing) and the
  `reload()`/`postConfigReload()` flow are byte-identical between 0.56.2
  and 0.57.0. 0.57.0 did not drop config-time loading.
- **But config-time loading was never boot-capable in either version:**
  `CCompositor::initManagers(STAGE_PRIORITY)` creates the ConfigManager
  and runs `Config::mgr()->init()` — the first full config pass — while
  `g_pPluginSystem` is only created in a later stage
  (`STAGE_BASICINIT` in 0.57, `STAGE_LATE` in 0.56.2).
  `handlePluginLoads()` starts with `if (!g_pPluginSystem) return;`, so
  the path registered by `hl.plugin.load` during the boot pass is
  silently discarded. Only config passes after compositor init
  (manual `hyprctl reload`, plugin-init `doLater` reloads) consume the
  registration. The 0.56.2-era "it works" evidence came from those
  post-init reloads and manual `hyprctl plugin load`, not from login.
- The running session's log cannot falsify this: after line 16
  ("Disabling stdout logs") the 0.57 logger writes none of Hyprland's
  own lines to `hyprland.log` (4.5 h, 0 own lines vs 8613 aquamarine
  lines), so the earlier "zero plugin lines" observations are not
  evidence about the plugin system either way.
- The proven working login-time load path is the dispatch route: an
  external process running `hyprpm reload` (today's 08:38:22 repair),
  which loads the enabled receipted plugin directly and triggers the
  config reload from plugin init.
- **Gate decision: mechanism B.** Mechanism A cannot load at login on
  any reviewed version. A prime variant (a managed-snippet
  `hyprland.start` handler exec-ing `hyprctl dispatch plugin load …`
  directly) reaches the dispatch route without the receipt chain, but
  the project's own recorded policy (native/hyprpm.json limitations,
  plugin_login.py contract) requires startup loading to stay behind the
  explicit receipt-checked grant; it is rejected. B keeps that chain:
  the installed release already ships `helpers/plugin_login.py` and
  `config/hypr/titlebars.lua.in`.

## Current gaps

1. The managed snippet's only plugin load targets the stale 0.56.2
   artifact, refused by the 0.57.0 version check at every login.
2. The private config's `hyprland.start` handler cannot load a plugin
   (registration wiped before any pass reads it).
3. The designed persistent path for hyprpm bundles — `--session-activate
   --enable-plugin-login` writing `omabuntu-activation.lua`, exec'ing the
   receipt-checked `helpers/plugin_login.py` (`hyprpm reload`) from a
   `hyprland.start` handler — is unreachable here: `session_activation`
   requires the generic session receipt/module, `session_config` refuses
   unowned profiles, and `plugin_login.review()` hard-reads the missing
   `~/.local/state/omabuntu/session-activation.json`. That flow also
   lacks native login acceptance.
4. Nothing in any release loads the plugin at login, so re-running the
   public installer cannot fix the symptom the user reported.
5. Hyprland 0.57.0's config-time plugin-load semantics are not yet
   source-reviewed locally (today's silent refusal differs from the
   0.56.2 ERR/notification path).

## Safety constraints

- Diagnose before changing configuration; this plan is not approval to
  edit the desktop, reload the compositor, log out, install packages, or
  commit/publish.
- No sudo, no hyprpm enable/disable/unload, no service or unit changes,
  no autostart/exec-once additions, no workspace-mode or bind changes,
  no plugin-feature work (hyprbars pin stays `d2427d4d…`).
- The managed snippet is deployed only through the existing plan-018
  flow (`make hypr-settings` → `tools/deploy_hypr_settings.py`), which
  backs up the installed snippet and never reloads Hyprland; the change
  takes effect at the next Hyprland start.
- Loading a plugin can crash the compositor. The login load is accepted
  only under an explicit deployment approval and a real login
  verification. A stale or mismatched receipt library degrades to the
  compositor's version-check refusal, proven benign today (no crash, no
  load, no config error); titlebars then stay absent until the next
  repair, which is exactly today's status quo.
- The Lua side cannot verify SHA-256 or the compositor version; it trusts
  the installer-written receipt and the compositor's own version check.
  Residual risk (root-modified cache library between installs) equals the
  trust already placed in `hyprpm reload` and is documented, not removed.
- Any edit to the private `~/.config/hypr/hyprland.lua` is a separate
  explicit approval with a manual backup; the deploy tool never touches
  unowned files.

## Proposed shape

Chosen at the gate: mechanism B — extend the persistent activation flow
so this machine's private profile can receive it.

- Extend `tools/session_activation.py`: when the generic session module
  is absent but the installer-owned managed snippet is present and
  current, allow the activation stage for that private profile instead
  of blocking on the generic-session guard. The managed-snippet state
  replaces the generic-module guard in `plan()`/`apply()`.
- `--session-activate --enable-plugin-login` then writes, as designed
  for manager bundles: `~/.config/hypr/omabuntu-titlebars.lua` (rendered
  from `config/hypr/titlebars.lua.in` with the release minimize helper),
  `~/.config/hypr/omabuntu-activation.lua` (`dofile` of the titlebars,
  plus a `hyprland.start` handler exec-ing the release's
  `helpers/plugin_login.py`), and the `session-activation.json` receipt
  with `plugin_login_enabled: true`. `plugin_login.py` runs `hyprpm
  reload` at login under its full receipt/ABI/library verification.
- Integrate the activation into the installer-owned managed snippet
  `config/hypr/omabuntu-managed.lua`: replace the dead legacy
  `~/.local/lib/omabuntu/hyprbars.so` load block with a guarded
  `dofile` of the activation file when it exists (same guard pattern as
  the workspace-layouts block). The private `hyprland.lua` is not
  edited; the integration ships through `make hypr-settings`.
- The dead `hyprland.start` handler block in the private
  `~/.config/hypr/hyprland.lua` is removed only under the separate
  optional approval with a manual backup.
- Titlebar rules are not otherwise changed; `plugin_login.py` applies
  them once after loading, exactly as designed.

Deployment and publication:

- Update `tests/test_session_activation.py` and
  `tests/test_hypr_settings.py` for the private-profile activation path
  and the managed-snippet integration (the no-receipt, no-grant and guard
  cases; `test_contains_no_desktop_behaviour` must stay true) and run the
  full suite.
- Update `docs/hyprbars.md` to describe the login load, its gating and its
  degradation.
- Present the diff, then request explicit approval to deploy via
  `make hypr-settings`. After deployment, request a real logout/login and
  verify: `hyprctl plugin list`, titlebar visible, `hyprctl configerrors`
  empty. User-observed acceptance is required; the repair transaction is
  not it.
- Optional, separately approved: remove the dead `hyprland.start` handler
  block from the private `~/.config/hypr/hyprland.lua` with a manual backup.
- Publish a new signed release (separate approval) so fresh and re-install
  users acquire the fixed template through the public installer.

## Explicit exclusions

- No changes to `plugin_login.py`'s receipt/verification chain: the
  activation stays opt-in through `--enable-plugin-login`, and the
  helper's full review() checks run unchanged at every login.
- No adoption, overwrite, or merge of the existing private Hyprland
  profile; no generic-profile rollout on this machine.
- No removal of the legacy `~/.local/lib/omabuntu/hyprbars.so` file, no
  unload of the currently loaded plugin, no hyprpm state changes.
- No autostart, systemd unit, exec-once, idle, lock, or suspend coupling.
- No new hyprbars features (workspace_tag, button_rounding); no visual or
  workspace-mode behavior change.
- No commit, push, tag, or release publication without separate approval;
  the local deployment and the public release are separate gates.

## Tasks

- [x] Source-review pinned Hyprland 0.57.0 (`0aa6745f…`) config-time plugin
      load path and decide mechanism A or B at the gate.
      Result: B — config-time registration is discarded before
      `g_pPluginSystem` exists at boot (both versions); the dispatch
      route behind the receipt-checked grant is the only login-capable
      path. See "Decision gate result".
- [x] Back up affected source paths under ignored work/ and implement
      mechanism B in `tools/session_activation.py` and the managed-snippet
      template `config/hypr/omabuntu-managed.lua`.
      Also: mode-neutral `package_user.managed_snippet` witness (both bundle
      modes ship identical bytes) and the once-per-Lua-state titlebars guard
      `omabuntu_titlebars_applied` in `config/hypr/titlebars.lua.in`.
- [x] Extend `tests/test_session_activation.py` and
      `tests/test_hypr_settings.py`; run `python3 -m unittest discover
      -s tests -v` and the clean-source/whitespace checks.
      Also updated `tests/test_publication_cleanup.py` for the new witness.
      1047 tests pass; clean-source check passes.
- [x] Update `docs/hyprbars.md` (and `docs/plugin-management.md`).
- [x] Present the reviewed diff and request approval for the
      `make hypr-settings` deployment.
      Approved and executed 2026-11-02: the deployed snippet was backed up
      (`~/.config/hypr/omabuntu-managed.lua.bak-20261102T134200.051306Z`, SHA-256
      `4bf2aa18…`), the new template written (byte-identical to the source), the
      include was already present, `hyprland.lua` untouched (SHA-256
      `d551d68c…` unchanged), no reload performed, `configerrors` empty.
      A read-only `--session-activate --enable-plugin-login` plan on this
      machine reports no blockers (digest
      `dc1b048865cac1e0a766c6d3840fef23080e72ce28db6ed5e39718e650414130`).
- [ ] After approval: deploy with backup, then verify at a real
      logout/login (plugin list, titlebar, configerrors).
- [ ] Optional, separate approval: remove the dead `hyprland.start`
      handler block from the private `~/.config/hypr/hyprland.lua` with a
      recorded backup.
- [ ] Request separate approval to publish a new signed release carrying
      the fix.
## Follow-up: the first live login silently skipped the load (2026-11-02)

The 16:22 login (Hyprland 0.57.0) did not load hyprbars: `hyprctl plugin
list` stayed empty. The mechanism itself is sound — the manual helper run
returned `loaded-and-configured` immediately — and the source review explains
the collision:

- `events.start` is emitted from the first rendered frame
  (`src/render/Renderer.cpp`, `static bool once`), so the `hyprland.start`
  handler fires roughly 1-2 s after the compositor starts.
- The autostart unit starts `omabuntu start` at that exact moment (service
  started 16:22:12, manager run `20261102T152212.506054Z`), and the manager
  holds the exclusive `control.lock` (`manager.py`, `flock LOCK_EX`) for its
  wallpaper restore and shell spawn until 16:22:13.
- `plugin_login.run()` opens the same lock with `LOCK_EX | LOCK_NB` and
  refuses a busy lock by design; `hl.exec_cmd` discards the helper's stderr,
  so the refusal was silent.

Fix: `tools/session_activation.py` `render()` now wraps the unchanged helper
in `/bin/sh -c 'for attempt in 1..12; do <helper> && exit 0; sleep 1; done'`.
Only the spawned command waits out the lock window; the helper and every
receipt check stay byte-identical. Full suite (1058) and clean-source pass.

Applying it to the live machine requires the activation stage again (outside
a Hyprland session): logout → GNOME/TTY → run
`work/plan-073-apply-login-grant.sh` (fresh digest) → login. The old
activation file and receipt are backed up by the transaction journal.
