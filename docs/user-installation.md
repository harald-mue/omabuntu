# Local user installation and versioned updates

## Status and boundaries

The local installer, standalone installed manager, release packager, integrity
checks and rollback/recovery are implemented. Tests deploy only into private
workspace fixtures. Preparing a bundle is not installation or desktop approval.
The user approved host apply. The latest recorded deployment is
`20261025-local.23` at `~/.local/share/omabuntu`, started manually via
`~/.local/bin/omabuntu`; its previous release is `.22`. This is a historical
deployment record, not a live status query. Use `omabuntu status` to check
the selected version and owned running process. No login autostart or
service supervision has been configured. hyprpaper was separately started
with approval for the session; the shell manager does not manage it.
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
once per login. The uwsm-managed session imports `HYPRLAND_INSTANCE_SIGNATURE`,
`XDG_CURRENT_DESKTOP` and `WAYLAND_DISPLAY` into the user manager environment,
so the manager's own Hyprland validation passes unchanged. There is
intentionally no `Restart=` directive: this is pure autostart, not supervision,
and a dead shell stays down until manually started. The unit hands off and
goes inactive; the manager's `running.json` record remains the source of truth,
and the shell still ends at logout through `PartOf`. Stop the shell mid-session
with `omabuntu stop`, never `systemctl --user stop` (stopping the unit would
kill the process group). Enabling is a distinct approval step and never starts
the service; rollback is `tools/deploy_autostart.py remove` plus
`systemctl --user daemon-reload`.

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
  fallback. Release `.23` contains that correction and removes the
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
python3 tools/package_user.py --version <new-local-version>
python3 tools/check_user_release.py work/user-releases/<new-local-version>
python3 tools/user_install.py plan work/user-releases/<new-local-version>
```

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

## Autostart is deliberately not enabled

The target uses UWSM's `wayland-session@hyprland.desktop.target`, with the matching
`wayland-wm@hyprland.desktop.service`. An eventual user service must be tied to
that specific session, not GNOME's generic graphical login, and must manage the
actual child lifetime, imported Wayland environment, single-instance behavior,
bounded restart rate and clean logout. No service unit or Hyprland startup edit
is installed by the current installer. Service activation and session-transition
tests follow daily-use and lock/recovery acceptance, with separate approval and
backups of existing unit/configuration/enablement state.
