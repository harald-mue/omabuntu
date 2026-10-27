# Local user installation and versioned updates

## Status and boundaries

The local installer, standalone installed manager, release packager, integrity
checks and rollback/recovery are implemented. Tests deploy only into private
workspace fixtures. Preparing a bundle is not installation or desktop approval.
Real login autostart, workspace persistence and wallpaper splash removal have
been user-confirmed on the development target. Use `omabuntu status` and
`omabuntu verify` for the actual selected release/process; no historical release
name in documentation is a live status query. Login autostart is a separately
approved user unit without crash supervision. hyprpaper activation is separate;
the shell manager does not manage that daemon.
The selected original panels remain the reviewed trial shell, not the original
full shell startup. Screen locking is a separate security gate; see
[lock readiness](lock-readiness.md). Do not describe this as a fully accepted or
crash-supervised production desktop yet.

## Login autostart unit (plan 012, Option A)

The reviewed autostart path is a single additive systemd user unit,
`config/systemd/omabuntu-shell.service`, deployed to
`~/.config/systemd/user/omabuntu-shell.service` by `tools/deploy_autostart.py`
(`plan` / `apply` / `remove`; apply backs up and requires `--replace` when a
unit already exists). It follows the enabled `hyprpaper.service` pattern:
`PartOf/Requires/After=graphical-session.target`,
`ConditionEnvironment=WAYLAND_DISPLAY`, `Slice=session.slice`,
`WantedBy=graphical-session.target`, and runs `%h/.local/bin/omabuntu start`
once per login. Before that command, `ExecStartPre` runs
`omabuntu-shell-wait.py` from the same systemd user directory. Hyprland 0.56.2
imports `WAYLAND_DISPLAY` before it writes `hyprland.lock`, and `hyprctl
instances -j` can print a lone `]` instead of a JSON list during that window.
The readiness helper and current manager poll until the matching live instance
is listed (40 attempts, 0.25 seconds apart). Invalid JSON is not ready, not a
shell failure. This is not a lifetime limit and does not restart a shell that
exits later. The UWSM-managed session imports `HYPRLAND_INSTANCE_SIGNATURE`,
`XDG_CURRENT_DESKTOP` and `WAYLAND_DISPLAY` into the user manager environment.
There is intentionally no `Restart=` directive: this is pure autostart, not supervision,
and a dead shell stays down until manually started. The unit uses `Type=oneshot` and
`RemainAfterExit=yes`: it stays `active (exited)` after the launcher finishes,
so systemd does not immediately terminate the shell's control group. This is
not shell-health monitoring; use `omabuntu status` to check the owned process.
The shell ends at logout through `PartOf` and normal control-group cleanup.
Use `omabuntu stop` for an identity-checked manual shell stop; stopping the
unit instead terminates its whole control group. After a manual shell stop,
`omabuntu start` still works, but the existing unit does not supervise that
new process. A fresh login is required to verify any new autostart deployment; the corrected
path has been user-confirmed on the development target. Enabling is a distinct
approval step and never starts the service; rollback is `tools/deploy_autostart.py remove` plus
`systemctl --user daemon-reload`.

### Historical repair: release integrity (plan 021)

A login passed the readiness helper but failed the launcher
with `Release identity, scope or integrity differs`. Do not add retries or
ignore integrity failures to hide this error. The subsequently approved read-only
comparison confirms exactly three extra Python bytecode cache files and no
missing or changed manifested files. The installed manifest matches the original
packaged manifest, and the previous release is intact.

A regression fixture reproduces a new cause in the plan 020 startup path:
wallpaper restore invokes a Python helper that imports sibling modules without
`PYTHONDONTWRITEBYTECODE=1`, adding cache files to a sealed release when its
helper directory is writable. The next start correctly rejects those extra
files. The source fix disables bytecode for this invocation, passes the actual
state directory and reports bounded added/missing/changed filenames on integrity
failure. It never excludes caches from verification or re-signs altered files.

The separately approved repair is complete: backed up the exact extra cache
files, removed only those additions, verified the original manifest unchanged
and installed a fresh corrected immutable release through the normal transaction
flow. A compatibility regression caught an overly strict check on legacy
`current/` directory modes: startup now preserves those child-directory modes
under the private owned state parent, still rejecting symlinks and foreign
ownership. No installed source was patched and no preferences were chmodded.

The corrected shell starts, restores its recorded wallpaper and passes strict
release verification after an Omabuntu-only stop/start without creating bytecode.
The rollback selector points to the independently verified last-known-working
older release, not the failed intermediate repair candidate. Private backup and
verification evidence remains under ignored `work/`. The installed managed
snippet, login unit and readiness helper match their reviewed templates; no
config reload or systemd change was needed. A real subsequent login was user-confirmed, separately from the unit tests.
Private deployment timestamps and process records remain under ignored `work/`.

For future integrity failures, the normal install path can also reject a
corrupted current/previous selector; do not delete files, rewrite manifests or
bypass that guard blindly. Compare and back up the exact delta first.

## Installer-managed Hyprland settings (plan 018)

Hyprland draws a random startup splash ("Thanks raf!" and others), an optional
logo background and a twice-a-year donation nag in its own background pass.
Those compositor settings are independent of hyprpaper 0.8.4's own splash:
the wallpaper daemon fetches the same text from Hyprland and draws it over each
wallpaper by default. This explains why the message remained visible despite
`misc:disable_splash_rendering = true` and a transparent compositor splash color.
The separate wallpaper setting below is necessary; repeatedly changing the
compositor flags cannot control that other renderer.

The reviewed file is `config/hypr/omabuntu-managed.lua`; it contains those
settings, a guarded title-bar plugin registration (plan 020: `hl.plugin.load`
during the config load, because a `hyprland.start` handler only queues a path
no later pass reads; the load triggers one config reload), and a loader that
re-registers saved `scrolling` workspace rules from
`current/workspace-layouts.txt` before the first window opens. No binds,
autostart or monitors. The supported installer step is:

```sh
make hypr-settings
```

It plans first, then writes `~/.config/hypr/omabuntu-managed.lua`, backs up an
existing file, and appends exactly one `require("omabuntu-managed")` line to
`~/.config/hypr/hyprland.lua` (also backed up first). Repeated runs change
nothing. It refuses a differently spelled reference or a duplicate include
instead of guessing. It never reloads Hyprland, touches systemd or starts a
session; the settings apply at the next Hyprland start.

Rollback is `make hypr-settings-remove`: it removes the exact managed block and
the snippet, and leaves the rest of `hyprland.lua` unchanged. A running session
is unaffected until it restarts.

### Separate wallpaper splash setting (plan 022)

The authored template `config/hypr/hyprpaper.conf` contains:

```ini
splash = false
```

This is a **hyprpaper** setting, not a Lua field in `hl.config`. Official
hyprpaper v0.8.4, commit `20fc0fa6c2056c388a4cd69cb394a9f989dd27c0`, defaults it
to enabled in `src/config/ConfigManager.cpp:57`; `src/ui/UI.cpp:56-116` retrieves
`/splash` and creates the separate overlay. See the
[pinned renderer source](https://github.com/hyprwm/hyprpaper/blob/20fc0fa6c2056c388a4cd69cb394a9f989dd27c0/src/ui/UI.cpp#L56-L116).

New local bundles record the template under `config/hypr/hyprpaper.conf`, but
packaging, installing a release and `make hypr-settings` do **not** deploy this
wallpaper config or restart its service. Deployment remains separately approved:
review `~/.config/hypr/hyprpaper.conf` (or the daemon's actual XDG/explicit config
path), back up an existing file or record its absence, and preserve unrelated
wallpaper settings. Copy the minimal template only when no existing config needs
merging. Record the current wallpaper mappings before activation.

The observed service has no reload action. After explicit approval, restart only
hyprpaper. If the saved background matches the current live mappings, reapply it
using the installed packaged helper with bytecode writes disabled and the actual
Omabuntu state directory. Otherwise preserve and restore the exact active
per-output mappings through the reviewed wallpaper IPC; do not replace the user's
current image with stale saved state or rewrite that state as part of a splash
fix. The wallpaper may briefly disappear; no compositor or shell restart is
necessary.
Rollback restores the previous config bytes/mode or removes only the newly
created file when it was absent, then separately approves daemon restart and
wallpaper restoration. Template tests and source evidence are not visual
acceptance; confirm the text has disappeared after the approved live change.

The approved target deployment created the previously absent config, restarted
only hyprpaper and restored the original mappings on all three monitors. No
service errors were reported, shell identity and application geometry remained
unchanged, and release integrity still passes. The background record was older
than the actual active image, so this deployment preserved the live mappings
without rewriting the record. The user subsequently confirmed that the splash
text has disappeared; visual acceptance for this change is complete.

## Prerequisites and installer scope

The low-level `tools/user_install.py` deploys a reviewed user release; it
does not install packages. The new [guided entry point](guided-installer.md),
`tools/install.py`, adds separately approved runtime-package transactions,
bounded target checks and isolated linkage/import/WebP verification before
using this same deployment mechanism. It is not a complete Ubuntu provisioner:
a compatible compositor and native desktop services must already exist,
and no desktop configuration or keybinding merge is automatic.
See [dependencies](dependencies.md) for recorded packages and the
[guided workflow](guided-installer.md#use-the-implemented-workflow) for
commands, approval digests and remaining fresh-target acceptance work.

The development target uses Ubuntu 26.04, Hyprland 0.56.2 and Qt 6.10.2.
Confirm compatibility before building or installing on a different target.
The existing [Quickshell package plan](package-plan.md) is a source-build
plan, not a minimal end-user runtime dependency list.

For Style > Theme / Background in particular:

- Install a compatible `hyprpaper` only after reviewing an APT simulation.
  The verified installed version is `0.8.4-1ppa3~1resolute1` from the
  already configured `cppiber/hyprland` PPA. Merely installing it is not
  session activation: an approved running daemon is needed to paint images.
- `qt6-image-formats-plugins` supplies `libqwebp.so`; without it the Qt picker
  cannot decode WebP, even if hyprpaper paints that same file. The verified
  package is `6.10.2-1` from Ubuntu `resolute/universe`. Restart the managed
  shell after installing the plugin if it has already cached its formats.
- The helper uses the current per-monitor wallpaper IPC and has a legacy
  fallback. It includes that correction and removes the
  unconditional "no daemon approved" picker message.

Review, do not blindly replay, these package operations on each target:

```sh
apt-get --simulate --no-remove --no-install-recommends install \
  hyprpaper qt6-image-formats-plugins
# Only after approving the candidates, origins and complete solver result:
sudo apt-get --no-remove --no-install-recommends install \
  hyprpaper qt6-image-formats-plugins
```

Do not add a PPA automatically to obtain these versions. Recheck candidates
if the package metadata changes; reject removals and unrelated upgrades.
Package installation, user-file deployment, configuration integration and
session starts are distinct approval and rollback domains.

## Layout (approved and applied default host paths)

- `$XDG_DATA_HOME/omabuntu/releases/<version>/` (default `~/.local/share`):
  standalone runtime, selected sealed QML, Python helpers, manager, licenses and
  provenance. No private inventories, source snapshots or machine backups.
- `.../omabuntu/current` and `previous`: relative, verified version selectors.
- `~/.local/bin/omabuntu`: regular Python bootstrap, not an Omarchy bin directory.
- `$XDG_STATE_HOME/omabuntu/` (default `~/.local/state`): private launch records,
  logs, before-change display readings, transaction journals and launcher backups.
- `~/.config/omabuntu/` is reserved for later reviewed preferences. The installer
  does not currently create it or persist session-local UI preferences.

No Git/workspace path is needed at runtime. Python bytecode writing is disabled
for installed helpers so imports cannot mutate the release manifest. Runtime
`bin/qs` is made relative to `quickshell`; all other stage bytes are copied from
the verified build. The runtime depends on the already installed, target-matched
Ubuntu libraries; this is not a portable all-distributions binary package.
Symlinked deployment/state parents, unsafe selectors, altered manifests, special
files and whitespace in release paths are refused. The whitespace limitation is
inherited from the reviewed QML helper-path policy. Do not weaken that check
silently for a different home path.

## Prepare and review (workspace only)

After source/contract/QML review and tests:

```sh
python3 -m unittest discover -s tests -v
python3 tools/package_user.py --version <new-local-version> --build-dir work/builds/<build-id>
python3 tools/check_user_release.py work/user-releases/<new-local-version>
python3 tools/user_install.py plan work/user-releases/<new-local-version>
```

Choose the exact verified build produced by the approved runtime builder;
`--build-dir` is required and has no machine-specific default. An asset-free
checkout is supported. Local ignored wallpapers/previews are included only when
present, so review a private bundle separately before any redistribution.
The WebP preflight uses an authored tiny probe, not an imported wallpaper.
See [clean-source verification](clean-source.md).

Version names are unique and cannot be silently reused for different contents.
The packager validates source seals and the existing build artifact manifest. It
includes Omabuntu/Omarchy MIT notices, the Quickshell LGPL/GPL texts and cpptrace's
MIT notice. Provenance is retained. This local packaging is not approval for
remote publication, redistribution or release/license compliance claims.
Integrity checks are consistency checks, not a signature or a sandbox for
untrusted downloaded code. Only install a locally reviewed bundle.

The relocation probe mounts the runtime at `/relocated/omabuntu/runtime` in
Bubblewrap, with no `/opt/omabuntu-runtime`, real buses or displays. It verifies
actual runtime/module loading and the session-grant parser. It does not render
panels or test native device actions. Tests and reports are private under work/.

## Apply only after the named host paths are approved

```sh
python3 tools/user_install.py install work/user-releases/<new-local-version> --apply
```

Without `--apply`, install prints a read-only plan. There is no sudo, APT
transaction, service enablement, shell-profile edit, Hyprland config edit or
implicit process replacement. Existing launcher bytes/mode and version selectors
are recorded and backed up before replacement. The state contains original path
existence, hashes and operations. A new release is copied to an incoming tree,
verified and renamed before selecting it. Existing release directories are not
overwritten. Reinstalling the exact selected version is idempotent.

Caught application failures restore selector/launcher pre-state. A prepared
journal left by an interruption blocks new install/start/rollback operations;
inspect it and use explicit recovery. This is not a guarantee against filesystem
failure or power loss; durable full-system backups remain separate.

## Manual session control

These commands are for the actual Hyprland session terminal after installation:

```sh
~/.local/bin/omabuntu verify
~/.local/bin/omabuntu status
~/.local/bin/omabuntu start
~/.local/bin/omabuntu stop
```

Start requires a live matching Hyprland instance, Wayland socket and session
environment. It refuses GNOME, ambiguous environments and any other Quickshell.
For the initial handoff, stop an existing workspace trial explicitly with
`python3 tools/bar_session.py stop`. Installing files alone does not stop it.
The approved host handoff has now completed: only the recorded trial process
was stopped, then the verified installed release was started against that same
live Hyprland session. The current bar no longer runs from the workspace.
`tools/bar_session.py` controls workspace trials, not the installed bar; use
`~/.local/bin/omabuntu status|stop|start` for the installed instance.

The manager checks release integrity before launch, uses the explicit session
lifetime grant, records PID/UID/start ticks/exact argv, and confirms startup logs.
Startup failure terminates only the child it launched, not the compositor or
other applications. Stop never uses a broad kill, forced kill, session stop or
logout. An unknown/reused PID is not stopped. The bar does not expire on a timer.

## Update and rollback

Prepare a distinct new version and review it first. With an installed bar,
explicitly stop it, then install the new bundle and start it manually. The
previous release remains intact. Updates do not auto-restart a desktop process.

```sh
~/.local/bin/omabuntu stop
~/.local/bin/omabuntu install /absolute/path/to/reviewed/new-bundle --apply
~/.local/bin/omabuntu start
```

From the Git checkout the same three steps plus release preparation are one
Makefile target, which is the supported local source update:

```sh
make update VERSION=my-change BUILD_DIR=work/builds/<build-id>
```

`make install VERSION=...` stops at installation and never starts the shell.
`make release VERSION=... BUILD_DIR=...` only prepares the bundle under `work/`, and
`make help` lists every target without side effects.

### Complete live development update

Use this instead of the older `update` target when iterating on source:

```sh
make dev-update BUILD_DIR=work/builds/<build-id>
# Optional explicit fresh version; the verified build stage is always required:
make dev-update VERSION=dev-my-change BUILD_DIR=work/builds/<build-id>
```

The default version is a fresh UTC timestamp. Even with an explicit version,
this target always packages current sources; an existing bundle causes a refusal,
not silent reuse. The sequential steps (also with `make -j`) are:

1. Package a new immutable release, including current shell/QML, packaged Python
   helpers, manager, assets and a copy of managed Hyprland/systemd templates.
   Reuse the selected verified runtime build stage; do not rebuild C++ dependencies.
2. Preflight the bundle and print managed-settings and autostart plans.
3. Stop the owned Omabuntu shell; abort on failure.
4. Install via the checkout's current manager, without modifying a sealed release.
5. Update the managed Hyprland snippet/include with backups and a unified diff.
6. Update and enable the autostart unit and readiness helper, with backups and
   user-manager daemon-reload; never start the unit here.
7. Run `hyprctl reload`, then check `hyprctl configerrors` (bounded commands).
8. Start the newly installed Omabuntu shell with its session-lifetime grant.

**This is a live configuration reload, not a Hyprland restart.** The compositor,
login session and applications remain running. Startup hooks do not run again.
It cannot replace the compositor binary or an already-loaded plugin; those need
separate reviewed actions. Arbitrary personal Hyprland config, binds, plugin
artifacts and lock/idle configuration are not synchronized. Wallpaper restoration
is handled separately by the manager, not by recursively copying repository data. There is no blind recursive copy of all repository files.

The target changes the desktop and enables login autostart: invoke it only when
those operations are approved. Implementation tests use stubs and do not deploy.
A failure stops subsequent steps; there is no cross-tool transaction. In particular,
a failed install/reload can leave the shell stopped or the new release selected.
Inspect the printed error and backups, fix configuration or use the release rollback
below, then explicitly `make start`. Release rollback does not undo managed config
or systemd files; those retain their separate restoration paths.

Individual actions are also available:

| Target | Action |
| --- | --- |
| `make hypr-settings-plan` | Read-only managed-settings unified diff |
| `make hypr-settings` | Back up and deploy managed settings, no reload |
| `make autostart-plan` | Read-only unit/helper deployment plan |
| `make autostart` | Back up, deploy and enable unit/helper, no start |
| `make reload` | Reload Hyprland configuration and check errors |
| `make restart` | Stop/start only the owned Omabuntu shell |
| `make hypr-settings-remove` | Remove managed include/snippet with backups |
| `make autostart-remove` | Remove/disable the autostart unit |

If the new version fails:

```sh
~/.local/bin/omabuntu stop
~/.local/bin/omabuntu rollback --apply
~/.local/bin/omabuntu start
```

Rollback switches verified current/previous versions. For the very first
installation, rollback restores the prior launcher (or removes the introduced
one) and removes the introduced selector; there is then no installed launcher
to start. Reinstallation remains available through `tools/user_install.py`.
Version directories and private journals are intentionally retained, not deleted.
Rollback refuses to overwrite a launcher modified outside the installer.

After an interrupted deployment, review its prepared journal, then:

```sh
python3 tools/user_install.py recover --apply
```

Use the same `--root`, `--state`, `--launcher` options if nondefault paths were
chosen. The repository-side tool remains available if no bootstrap is active.
Recovery requires exactly one pending journal and refuses unrelated selector or
launcher changes. It validates backup bytes and target releases before restoring.
No release pruning or dependency/package removal is automated. This rollback
restores release selection and the launcher only, not theme/font edits,
Hyprland configuration, package state or a separately started wallpaper
daemon. Those require their own backed-up, reviewed restoration steps.

## The installer does not enable autostart

The target uses UWSM's `wayland-session@hyprland.desktop.target`, with the matching
`wayland-wm@hyprland.desktop.service`. The release installer does not install a
user unit or edit Hyprland startup. The separate reviewed unit described above
is pure autostart: no `Restart=`, no crash supervision, and no GNOME graphical
login binding. Replacing that unit, reloading systemd, and the next login check
remain separate approval steps.
