# Guided Ubuntu installer: usage, design and remaining work

## Status

`tools/install.py` implements the staged local-bundle workflow below, reusing
our [versioned user-release installer](user-installation.md). Package and
file apply require an explicitly approved saved plan, and session start is
separate. Running the tool with `--help` changes nothing.

This is not a universal fresh-desktop provisioner: a compatible compositor
and desktop services must already exist. Automatic keybinding/configuration
integration, wallpaper process management, autostart and clean-target
acceptance remain pending. Implementation is not approval to install on the
current machine; no host apply was performed while implementing it.

The supported development target is Ubuntu 26.04 on x86_64 with Hyprland
0.56.2 and system Qt 6.10.2. This is tested target context, not a compatibility claim
for arbitrary Ubuntu releases, Qt versions or Hyprland configurations.
Upstream behavior is compared against Omarchy commit
`03ff1eff3812933f7088484533784d2f63eaf19a`; never run its Arch installers.

Recent live fixes expose missing first-install checks: hyprpaper was absent
or stopped, its installed version used a newer IPC, and Qt lacked the WebP
image plugin. A successful file deployment alone did not make these features
work. The installer must distinguish collection, deployment integrity,
functional verification and user visual acceptance.

## Use the implemented workflow

Run from the repository as your normal user; never run this installer via
sudo. Only the separately approved package subprocess invokes sudo, in your
interactive terminal. It does not capture credentials or pass auto-yes.

```sh
python3 tools/install.py --help

# Read-only inventory, candidate policy and APT simulation; no bundle needed.
python3 tools/install.py package-plan --with-wallpaper
# Open the printed private package-plan.json and review its payload:
# policy (including sources), pinned requests, resolved versions,
# simulation, transaction and the complete before-state.
python3 tools/install.py packages <package-plan.json> --approve <printed-digest> --apply
```

Omit `--with-wallpaper` to leave hyprpaper out of the package selection. The
Qt image-format plugin stays required for WebP previews. Existing installed
packages are not upgraded just because a newer candidate exists. Removals,
changes to installed packages, missing candidates and unrecognized solver
results block apply. All new dependencies are pinned to their simulated
versions; requesting them explicitly may give them manual APT marks. Review
that consequence as part of the plan. Versions, existing marks and unexpected
additions are checked afterwards; no package purge or autoremove follows a
failure. There is no automatic APT refresh or repository addition.

Changing APT policy, the simulation, package versions/marks, or the dependency
manifest invalidates a package approval. Generate and review a new plan.
The digest detects changes; it is not a publisher signature. Only use locally
trusted bundles and plans.

Prepare a verified bundle through the existing [build](runtime-build.md) and
[packaging](user-installation.md#prepare-and-review-workspace-only) process,
or use an existing locally reviewed bundle. No automatic source download or
build is added to the installer.

```sh
python3 tools/install.py preflight work/user-releases/<version> --with-wallpaper

# If updating an already running managed shell, stop it explicitly only
# after approving that desktop interruption. Planning will otherwise refuse.
# ~/.local/bin/omabuntu stop
python3 tools/install.py plan work/user-releases/<version> --with-wallpaper
# Review the printed deployment-plan.json and its exact target paths.
python3 tools/install.py install <deployment-plan.json> --approve <printed-digest> --apply

# Separate explicit session-lifetime grant; no wallpaper start or autostart.
python3 tools/install.py start --apply
```

Without `--apply`, `packages`, `install` and `start` print a no-change notice.
A deployment plan requires successful preflight and an explicitly stopped
managed shell. Apply repeats preflight and checks the plan again under the
existing deployment transaction lock. Bundle, launcher or version-selector
changes require a new plan. Unchanged reinstallations reuse the existing
idempotent installer; no running shell is implicitly stopped.

Reports, package before/after snapshots and probe results stay private under
`work/installer/`. Failed or timed-out commands block progress. Package
interruption leaves evidence, not an automatic system rollback. User-release
interruption uses the existing [recover/rollback](user-installation.md#update-and-rollback)
commands and journals. Review before retrying either domain.

Preflight checks the supported Ubuntu/architecture, installed Hyprland and Qt
versions, declared runtime packages and monospace family resolution. With
`--with-wallpaper`, it also reports the hyprpaper process lookup and the
installed hyprctl IPC help syntax. These are informational, not a daemon
ownership grant or proof of successful live application. A stopped daemon
does not block installing the files. The probe then
runs linkage, selected QML imports and real WebP decoding in Bubblewrap with
no host display, network, buses or user HOME; there is no host fallback.
Fonts installed outside APT are permitted; family resolution does not prove
Nerd Font glyph coverage. The runtime manifest is a feature prerequisite
list, not an exhaustive portable ELF lockfile. Missing native libraries block
deployment and need a separately reviewed dependency resolution.

After installation, configuration/keybinding integration and starting
hyprpaper remain manual, separately approved tasks. `--with-wallpaper`
installs/checks its package only; it does not start it. Shell integrity,
background apply, visible previews, shortcuts and security acceptance are
different checks; do not infer them from a successful package transaction.

## Stages and remaining design

### 1. Read-only preflight

Extend the existing Python-standard-library orchestration. Detect the target
OS, session, compositor/Qt versions, configured package origins, existing
installation and configuration conflicts. Keep bounded probes and explicit
missing-command, timeout and partial-failure results. Reports stay private
under ignored work/; do not publish inventories.

Check feature behavior as well as package names:

- Resolve native runtime libraries and QML imports for the reviewed bundle.
- Decode an imported WebP using the same Qt runtime as the shell.
- Identify installed versus running hyprpaper and its supported IPC.
- Check required fonts and report missing glyph/family support separately.
- Validate the target Hyprland configuration format without reloading it.

The general doctor remains an evidence collector. The installer preflight
adds the bounded isolated runtime/decode checks above, not full native
acceptance. It starts only isolated disposable probes, never a host shell or
wallpaper daemon; no sudo, package refresh or desktop configuration writes.

### 2. Reviewable dependency plan

Create separate runtime, optional-feature and source-build groups.
[Dependencies](dependencies.md) records current evidence; the existing
[Quickshell package planner](package-plan.md) covers source-build needs,
not a complete end-user runtime manifest.

Wallpaper support needs hyprpaper; WebP previews need
qt6-image-formats-plugins even when the wallpaper engine itself can decode
WebP. Avoid installing a compiler/header toolchain just to run a reviewed
compatible release. Do not claim a complete runtime closure until verified
on a clean supported target.

Use existing configured sources only. Show exact candidate versions, origins,
new packages, upgrades, removals and APT marks; simulate before requesting
approval. Refuse removals and unexpected unrelated upgrades. Changed solver
results require renewed review. Adding a repository is a separate decision,
not an automatic repair.

### 3. Explicit package transaction

Only after approval, perform the reviewed package transaction with normal
interactive authentication in the user's terminal. Never request credentials.
Record package/version/mark prestate and verify the outcome. Explain that APT
hooks and triggers may run; do not promise a system transaction is equivalent
to merely copying files.

### 4. Verified user deployment

Use tools/package_user.py and tools/user_install.py for reviewed local
bundles. Preserve manifest verification, private paths, version uniqueness,
selector/launcher backups and interrupted-transaction recovery. An integrity
manifest is not a publisher signature or permission to run untrusted bundles.
Fresh users currently need the documented pinned workspace build; a portable
binary distribution and publication approval do not exist yet.

### 5. Optional desktop integration

Show a per-path diff and preserve previous bytes, modes and existence before
any approved change. Keep shell deployment separate from keybindings,
Hyprland configuration and font configuration. Detect existing definitions
and refuse ambiguous merges rather than overwriting a user's desktop.

Consult official version-appropriate documentation before implementing any
configuration adapter. Preserve GNOME, login, VPN, certificates, keyring and
corporate agents. No boot, kernel, PAM, sudo policy, firewall or management
changes belong in this installer.

### 6. Session activation and verification

Ask before stopping/replacing the managed shell or starting a wallpaper
daemon. Use explicit session-lifetime grants, no expiry wrapper for normal
components. Check owned process identity and limit stop operations to the
managed child. Verify startup, a real background apply and preview decoding;
ask the user to confirm native shortcuts, focus and visible results.

Autostart and crash supervision are separate future gates: back up unit/config
and enablement state, tie lifetime to the correct Hyprland session, preserve
GNOME and verify logout cleanup. No lock, idle or suspend activation before
authentication and recovery acceptance.

## Rollback domains

| Domain | Current status / required behavior |
|---|---|
| Shell release | Existing current/previous selection, launcher backup and interrupted-deployment recovery |
| Desktop configuration | Future integration must restore only the reviewed paths; detect later user edits before restoration |
| Session processes | Stop only identity-verified managed processes; session lifetime does not imply supervision |
| System packages | Separate reviewed transaction; never blindly purge dependencies or run broad autoremove |

Do not call release rollback a whole-desktop or package rollback.

## Implementation and acceptance backlog

Implemented stages and remaining work:

- [x] Define a feature prerequisite manifest separately from build packages
      (`packages/installer-runtime.json`); exhaustive clean-target closure remains pending.
- [x] Add bounded target/package/font and isolated runtime/WebP preflight.
- [x] Add reviewed dependency transaction planning and pre/post-state evidence.
- [x] Provide separate approved package and existing user-release deployment stages.
- [ ] Implement conflict-aware, backed-up optional configuration adapters.
- [x] Expose separately approved shell activation using the existing manager's
      session validation and owned-process tracking.
- [ ] Add wallpaper session activation, owned-process tracking and verified logout cleanup.
- [x] Add fixture coverage for no-apply defaults, package drift/failure,
      saved-plan validation, backed-up deployment and later-launcher-edit refusal.
- [ ] Exercise real interrupted APT recovery and complete end-to-end integration adapters.
- [ ] Exercise a clean supported Ubuntu target, including WebP preview and wallpaper apply.
- [ ] Document and test rollback separately for releases, configuration and packages.
- [ ] Complete privacy, license and distribution review before any public release.

Autostart, supervision and lock/security acceptance remain independent of this
backlog; none is implicitly enabled by completing a first installation.
