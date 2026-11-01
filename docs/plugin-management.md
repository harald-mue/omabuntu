# Hyprpm-managed titlebars

## Status

New application builds target **Ubuntu 26.04 x86_64, Hyprland 0.57.0 and Qt
6.10.2**. The version-pinned official Lua APIs, example configuration, command
manual, manager implementation and header-install requirements have been
source-reviewed. This is **not** clean-VM, native, visual or security acceptance.
The previously reviewed 0.56.2 manager/session mapping remains available for
legacy source use; new application bundles have the 0.57 native contract.

New bundles carry `native/hyprpm.json`, not a precompiled `hyprbars.so`.
Existing v0.1.0 archives remain unchanged and do not acquire these source fixes.
Exact revisions and evidence URLs are in [upstream/hyprpm.json](../upstream/hyprpm.json).
Future compositor versions are not implicitly accepted.

Manager bundles also ship the installer-managed snippet without the legacy
titlebar artifact load: `config/hypr/omabuntu-managed.lua` is rendered per
bundle mode at packaging time (plan 071), because loading a bundled
`~/.local/lib/omabuntu/hyprbars.so` belongs to legacy bundles. In manager
bundles, plugin loading is owned by the explicit activation/login grant, never
by a path registered during the config load.

## The one-command installer

For a new manager-mode release, the public installer offers distinct steps:

1. Review PPA/runtime prerequisites for the published application.
2. Separately offer the local plugin compiler/header prerequisites. Declining
   this offer does not rebuild or cancel installation of the application. The
   installer first reviews the exact package plan without applying it. If the
   plan is blocked, explicitly choose whether to continue without plugin builds;
   installed-package upgrades are never enabled as a workaround. A failure after
   attempting package application still stops for review.
3. Install/update the prebuilt application under separate deployment/bar consent.
   From GNOME/TTY, optionally prepare a generic owned profile and next-login
   titlebar/wallpaper files. Choose keyboard layout explicitly. Existing private
   profiles are neither overwritten nor silently adopted.
4. Ask separately about persistent plugin loading and the bar login unit. File
   preparation never starts a service, compositor, manager or plugin.
5. In a matching plugin-free Hyprland session, offer pinned manager preparation,
   then separately offer live plugin enable/load and owned titlebar rules.

Manager preparation requires a running compatible compositor. A first installer
run from GNOME therefore **defers** that stage, prints the reason, and never logs
out or starts Hyprland automatically. After a separately approved first login,
rerun the same installer to receive the build/load offers. No temporary-cache
paths or internal `--plugins` commands are required for this user workflow.
Deferred compiler packages suppress new build offers, not reuse of an existing
independently verified healthy manager build. An unprepared login hook fails
closed rather than compiling or requesting sudo at login.

Use `install.sh` again to revisit deferred profile/login stages as well. Answer
with ordinary Enter (or `y` then Enter), not Shift+Enter. Unrecognized terminal
sequences are not interpreted as approval. Session transitions remain separate;
the installer does not log out, replace the current desktop or bypass blockers.

An application-installed message is not a titlebar/native acceptance claim.
Updates do not silently disable, unload, rebuild or adopt manager repositories.
An independently verified healthy manager build is reused; an already active
hyprbars is not enabled/loaded again. Ordinary installer questions show `[Y/n]`;
this changes Enter's default, not the independent approval boundaries.

## Repair through the same installer

The normal `install.sh` flow also detects an existing enabled, receipted hyprbars
that is missing from the current session. If the exact native identity, policy,
repository, library, headers and persistent manager state verify, it offers a
live repair instead of demanding another build or a plugin-free session. An
identical verified application is not redeployed/restarted merely to reach repair;
a reusable manager build needs no compiler-package installation.

Repair has **one explicit live confirmation** after its plan. It takes verified
private backups under the existing control lock, repeats drift checks, runs only
an unforced system `hyprpm reload`, and verifies loaded state and unchanged
persistent/native evidence. The executable must be protected and package-owned.
It does not enable/disable, build, download, request sudo, rewrite private Lua,
apply titlebar rules, start services or grant future-login loading. Existing
foreign plugins/repositories, failed transactions or stale evidence block repair.
Do not run external plugin/manager operations concurrently: official reload is a
reconciliation operation. Failure keeps a manual-review journal; there is no
automatic unload, restore of a live plugin, or retry. Native code loading can
crash the compositor, so it is never folded into application update consent.

This repairs the current session's missing plugin, not arbitrary desktop damage
or missing private-profile login integration. Persistent integration remains a
separate backed-up approval; repair does not silently adopt an unowned profile.

## Fewer, scoped confirmations

The installer no longer asks an outer "review?" and then the same approval again.
PPA, mandatory runtime packages, user font, application deployment, generic
profile writing and plugin preparation/loading each use their final reviewed
transaction prompt. The deployment prompt explicitly names a proposed recorded
bar restart when needed. A declined mandatory prerequisite or application switch
does not proceed to follow-up desktop writes.

The keyboard choice is an input, not another Yes/No gate (`skip` defers it).
Future plugin loading and bar login enablement remain separate choices before
the final next-login file plan; current login files do not repeat those questions.
Optional blocked packages can still be explicitly deferred. Typed migration and
recovery phrases, sudo/APT/third-party prompts and release publication approvals
are unchanged. EOF/unknown responses still decline; fewer prompts do not imply
blanket unattended consent.

## Package scopes

```sh
make runtime-packages
make plugin-packages
```

Both commands review only. Explicit apply commands are:

```sh
./install.sh --packages --runtime-only --apply
./install.sh --packages --plugin-build-only --apply
```

Runtime packages exclude compiler/development-header groups. The plugin scope
includes the compiler tools and dependencies needed by the official Hyprland
0.57 CMake configure/installheaders path, including Wayland/Hyprland protocols,
Lua headers, libeis, libcanberra and sdbus-c++ development files. It excludes the
Quickshell/Omasnap-specific build groups. `make packages` remains the application
source-build inventory. Installed-package upgrades/removals are still refused.
A valid APT upgrade line is now reported as a prohibited installed-package
change, not additionally misreported as an unparseable install line.

The plugin package stage handles one reviewed compatibility case itself. If a
candidate simulation would change installed packages, it checks whether APT
provides `libudev-dev` in exactly the installed `libudev1` version. It verifies
package/version/architecture and the exact runtime dependency, then re-simulates
with that header version. The package review explicitly shows this older-header
selection and preserves both simulations and metadata in its private report.
Only an additions-only result can proceed after the normal package approval;
apply repeats the complete state/metadata/simulation checks. Held packages,
unavailable/malformed metadata, failed probes and residual upgrades stay blocked.
This is not an installed-package downgrade or a general old-version solver; no
repositories, shared runtime versions, systemd, udev or PAM settings are changed.
No extra flags or package commands are required from the user: the same
`install.sh` entry point performs this review. An installed old runtime is not
thereby updated to a newer security baseline.

Read-only inspection confirmed direct runtime requirements for LayerShellQt,
libdeflate, jemalloc, libdwarf and libunwind; their runtime packages are explicit.
The current Ubuntu PPA Hyprland binary links Lua 5.4. The process-scoped Lua 5.4
include workaround is retained; no global environment or alternative is changed.
Official source discovery allows a Lua fallback, but this does not claim support
for future PPA Lua ABI changes. A clean-VM dependency/build test is still required.

## Manager preparation and backups

```sh
make plugins
make plugins-prepare
```

The first command is read-only. The second asks before downloads, compilation,
cache changes and possible internal sudo requests. Never run the whole command
as `sudo hyprpm`.

The pinned official implementation can reconcile live load state even during
`update`. Preparation therefore refuses **any loaded compositor plugin**, any
enabled manager plugin, unrelated/unowned repositories, wrong revisions and
installed/running compositor or ABI mismatches. Only the update child loses its
compositor signature, preventing its final live reconciliation. Its exit 1 is
accepted only after fresh header/global ABI and exact repository/build checks;
all other errors stop. Evidence and metadata are rechecked between commands,
new receipts always include verified header fingerprints, and a plugin appearing
during preparation is left alone rather than unloaded. Do not run other manager
operations concurrently. Preparation never intentionally unloads a working
plugin to make room. An already upgraded binary with an older running compositor
is explicitly blocked; restarting that session is a separate user decision.

In addition to `/var/cache/hyprpm/<user>`, the official root header-install step
can overwrite **`/usr/share/pkgconfig/hyprland.pc`**. The reviewed plan records
that file's existence/hash/owner/group/mode and cache directory prestate. The
apply step privately backs up its original bytes, the manager tree and any
existing receipt before executing commands, then journals the result. Shared
cache-parent metadata is recorded without copying other users' data.

Failure retains the evidence and blocks automatic retry. There is no automatic
root restore, repository purge, package rollback or plugin unload. Review the
private journal and `system-hyprland.pc.before` before a separately approved
manual recovery; never blindly extract a backup over system paths.

## Live activation and rules

```sh
make plugins-activate
```

This is a **live action** requiring an unchanged successful build receipt and
matching installed/running compositor identities and ABI. It asks before
`hyprpm enable hyprbars`, which can crash the session. After a verified load, a
separate prompt can apply only the owned, hash-checked titlebar rules. That action
does not reload the entire configuration or create a persistent login grant.
Without owned activation/titlebar files it is deferred, not merged into private
Lua. No application-build stage implicitly loads native code.

## Explicit persistent login grant

While Hyprland is stopped, review and apply:

```sh
./install.sh --session-activate --enable-plugin-login
./install.sh --session-activate --enable-plugin-login --apply
```

This backs up/writes the existing owned activation files and receipt. It does
not load anything now. `--enable-login` is a different flag for the bar unit;
neither flag implies the other. `--disable-plugin-login --apply` removes only
the future plugin hook and does not unload a running plugin.

At `hyprland.start`, the immutable release helper validates the explicit grant,
owned file hashes, completed transactions, repository name/revision/filename,
only-hyprbars enablement, library hash, existing headers/cache and exact built,
installed and running compositor metadata/ABI. Under the existing control lock,
it invokes only `hyprpm reload`, checks the reported load and applies the owned
rules through `hyprctl eval`. Missing prerequisites, edits or unrelated loaded
plugins cause refusal rather than mutation. If the plugin was already loaded,
normal configuration loading already applied the rules; the helper does not
append duplicate buttons.

There are no builds, downloads, enable/disable commands, sudo, whole-config
reloads, crash supervision or desktop-component lifetime timers at login. The
one-shot IPC operations are bounded, not the lifetime of the loaded plugin.
Next-login preparation rechecks actual unit enablement before writes and before
any approved systemd operation. A failure after a systemd reload/enable attempt
requires manual state review rather than claiming full restoration. An initial
wallpaper record is removed on file-stage failure; an unrelated pre-existing
lock background without a matching record is refused, not adopted.

After compositor/package/policy changes, rebuild/review explicitly. If an old
immutable helper and a new manager receipt no longer share the same policy,
reapply the owned next-login files separately; do not delete previous releases.

## Explicit migration of the recognized mixed manager state

This is separate from ordinary preparation and is **not** a general adoption or
reset command. The supported case is one official `hyprland-plugins` repository
with the recorded 0.56 source pin, recorded successful 0.57 build commit, stale
0.56 global manager ABI, only hyprbars enabled (or already disabled), and no
Omabuntu receipt. A clean running/installed 0.57 pair with matching ABI, no loaded
plugins, safe paths and installed compiler/header prerequisites is required.
Unknown revisions, other repositories/enabled plugins, an existing receipt or
unfinished transactions are refused. Neither an old library nor metadata alone
is accepted as a newly verified build.

First review the packages, then explicitly approve their separate installation:

```sh
make plugin-packages
./install.sh --packages --plugin-build-only --apply --plain
```

APT must still show an acceptable additive transaction. The missing direct
package names in the migration plan need not equal the number of APT additions:
APT can also add dependencies such as `libsystemd-dev`. No package installation
is implicit in migration.

Review the exact migration without invoking any manager command:

```sh
make plugins-migrate
```

Only after reviewing it, apply interactively:

```sh
make plugins-migrate-apply
```

This asks both for the migration and the exact text **`replace hyprland-plugins`**.
The manager's own sudo/removal/repository-trust prompts remain interactive and
untimed. The orchestrator verifies private tar backup contents/hashes/owner/group/
mode against the reviewed snapshot, backs up shared `hyprland.pc` bytes, and
journals before running these fixed official operations:

1. Disable hyprbars. With stale headers, the official command may write the
   disabled state and then return 1. Continue only after proving the exact sole
   enablement change, unchanged library/global state and an empty live list.
   DataState may initialize an empty `headersRoot`; no other cache changes are
   accepted at this stage.
2. Remove only the identified official repository. This is an explicitly
   approved replacement, not a purge of the user's manager cache. Its official
   unload path is gated by the old ABI, and the migration requires an empty
   live list. No working plugin is intentionally unloaded.
3. Refresh headers with no repositories registered. **Only this child process**
   has `HYPRLAND_INSTANCE_SIGNATURE` removed, so the official final load-state
   reconciliation stops before IPC. Its resulting exit 1 is accepted only after
   proving the fresh header commit/global ABI and allowed cache changes. This
   avoids unloading a plugin that appears during a long header build.
4. Add/build the exact reviewed 0.57 plugin revision. Verify the repository
   identity/revision, header/global ABI, regular library and all-disabled state
   before creating an inactive ownership receipt.

The real executor uses only the root-owned Hyprland-package-owned
`/usr/bin/hyprpm`, not an arbitrary PATH replacement; its bytes/ownership are
sealed in the review and rechecked. Source policy, required package versions,
native identities, live plugin list,
cache snapshots and shared metadata are rechecked between commands. Do not run
other hyprpm commands concurrently. Success is **`plugin-migrated-disabled`**:
there is no live activation, titlebar application or login grant. Review
`make plugins-activate` separately afterward. Private Lua loaders and bundled
plugin activation receipts are **not** migrated by this operation; do not reload
or transition the desktop to bypass those separate handoff checks.

On failure, stop. The printed private transaction contains `manager-before.tar`,
`system-hyprland.pc.before` when it previously existed, the reviewed prestate,
verified backup digest and each started/verified/failed step. The original
repository pin/enablement is retained in the backup even if replacement stopped
partway. A partial disable is not automatically undone; there is no automatic
re-enable, cache deletion, privileged restore, resume or retry. An incomplete
journal blocks normal preparation/activation and the next migration attempt.
Manual recovery needs its own review and privilege approval; do not delete the
journal or invent a receipt to suppress it. Root-owned cache/metadata restoration
must also preserve the recorded ownership and modes without touching other users.
The manager's transient runtime build scratch is not automatically restored.

This migration is fixture-tested, not native or VM accepted. The real
implementation run performed read-only local review only; the manager was not
executed and no packages, enabled state, loaded plugins or private files changed.

## PPA header layout and the interrupted header-check checkpoint

The reviewed Ubuntu PPA source `hyprland 0.57.0-1ppa2~1resolute1` includes
`debian/patches/99-hyprpm-global-headers`. It accepts the packaged global
`hyprland.pc`, skips building cache headers and records the current global ABI.
Source provenance: the [published Debian source archive](https://launchpad.net/~cppiber/+archive/ubuntu/hyprland/+sourcefiles/hyprland/0.57.0-1ppa2~1resolute1/hyprland_0.57.0-1ppa2~1resolute1.debian.tar.xz),
queried through Launchpad by the exact source package/version. This differs from the unpatched
0.57.0 manager and explains why an empty `headersRoot` is legitimate here.

Omabuntu now independently checks package ownership, protected root ownership,
pkg-config version/prefix, header commit/clean state and available build-library
version macros. A nonempty broken cache is refused, never silently bypassed.
Validated header fingerprints are recorded in migration/recovery receipts and
checked before activation/login. Empty cache directories must already exist at
login; no privileged initialization is permitted. Previously packaged immutable
helpers are unchanged and may safely refuse this layout/resolution: deploy an
updated owned helper only under separate application/session approval.

For **only** the earlier cache-only verifier failure after verified disable and
removal, retain the exact failed journal. Do not repeat migration or add the
repository manually. First review the explicit checkpoint recovery:

```sh
make plugins-recover JOURNAL=/absolute/path/to/transaction.json
```

The review verifies the original backup and unchanged package/native/backend
identity, original shared metadata, no receipt/repositories/loaded plugins and
the precise empty-cache/current-ABI checkpoint. It plans only the missing pinned
`hyprpm add`. Applying requires new terminal consent and the exact phrase
**`resume hyprland-plugins`**:

```sh
make plugins-recover-apply JOURNAL=/absolute/path/to/transaction.json
```

It backs up the current checkpoint, preserves the failed journal byte-for-byte,
and verifies an all-disabled pinned build before writing the inactive receipt.
Only then does a separate `resolution.json` bind the original journal hash to the
completed recovery journal/hash. Normal manager and updated login checks accept
only this verified resolution, not an edited failure status. A missing/tampered
resolution or interrupted recovery remains blocked. No automatic restore/retry,
plugin load, header refresh, further removal, private-loader change or login
permission is part of this operation. Success remains `plugin-migrated-disabled`.
The isolated header-refresh child's missing compositor signature was intentional;
it does not indicate a broken running desktop.

## Legacy handoff and acceptance

The updater refuses switching away from an activation receipt that still loads
a bundled library. It also refuses native-target-changing application updates;
that is a separate session migration, not a reason to bypass the guard.
Private `hyprland.lua` remains untouched. Existing immutable bundles/verifiers
retain their behavior; there is no implicit adoption of an old manager checkout.

Still outstanding: real pinned-manager/header build, first live load/rules,
first and repeat login, failure recovery, clean-VM APT closure and application
install/update/rollback under the new target. Unit tests use private fixtures.
No release publication or desktop mutation was performed during implementation.
