# Omabuntu

An Ubuntu-native, reversible integration of selected Omarchy desktop components
with Hyprland and Quickshell. This is not an Arch installer or a complete Ubuntu
provisioner, and it does not run Omarchy installers or migrations.

## Status

The development target is **Ubuntu 26.04, Hyprland 0.56.2 and Qt 6.10.2**.
Selected original component/layout sources are retained with narrow Ubuntu
backend adaptations; the unmodified full Omarchy shell is not deployed.

Implemented and exercised on the development target:

- Quickshell bar, application launcher, command menu, calendar and desktop panels.
- Versioned local installation, strict release integrity, updates and rollback.
- Explicit untimed session lifetime and a separately approved login autostart unit.
- Per-workspace tiling, scrolling and floating state persistence and restore.
- Wallpaper restoration and the independent hyprpaper splash-disable setting.

A real login and removal of the wallpaper splash have been user-confirmed.
That is not fresh-machine acceptance or proof that every panel/backend works on
other hardware. Lock authentication/recovery, idle/suspend activation, full-shell
compatibility and some native/visual paths remain separate acceptance gates.
See [capabilities](docs/capability-matrix.md), [compatibility](docs/compatibility.md)
and [lock readiness](docs/lock-readiness.md). Do not infer security acceptance
from successful tests or diagnostics.

## Start with read-only commands

Python 3 standard-library tooling is used for orchestration. The source builder
requires Python 3.12 or later. Native checks require their documented dependencies;
none of these commands installs packages or activates the desktop:

```sh
make help
make test
python3 tools/omabuntu.py --help
python3 tools/build_runtime.py
python3 tools/check_runtime.py
```

`python3 tools/omabuntu.py doctor` collects bounded OS/package/session diagnostics
and writes private reports under ignored `work/`. Reports may contain private
information. Collection success is not functional or security acceptance.

For an offline source-only verification with no existing build/image inputs:

```sh
python3 tools/check_clean_source.py --run
```

See [clean-source verification](docs/clean-source.md) for what is and is not
exercised. The regular unit suite does not require imported wallpaper images or
a prebuilt runtime; executable Lua tests explicitly skip if Lua 5.4 is absent.

## Build and local installation

Read [runtime build](docs/runtime-build.md), [dependencies](docs/dependencies.md)
and [installation](docs/user-installation.md) before applying anything.
A working compositor and compatible system libraries must already exist.
Dependency installation, source downloads/building, desktop configuration and
session activation are separate approval steps.

After reviewing dependencies and explicitly approving a local build:

```sh
python3 tools/build_runtime.py --build --jobs 4
```

The builder creates a new `work/builds/<build-id>/` and reports its location.
Use that exact directory explicitly; no timestamp from the developer's machine
and no unverified automatic "latest" selection is built in:

```sh
# Replace your-build-id with the directory produced by the approved build.
BUILD_DIR=work/builds/your-build-id
python3 tools/check_runtime.py --run --build-dir "$BUILD_DIR"
make release VERSION=local-test BUILD_DIR="$BUILD_DIR"
make preflight VERSION=local-test
make plan VERSION=local-test
```

These steps prepare and check a **local** bundle; they do not install or start it.
Follow the separately approved apply steps in the
[installation guide](docs/user-installation.md) or
[guided installer](docs/guided-installer.md). Nothing here authorizes a public
binary release.

Useful explicit live targets, only after desktop approval:

- `make install VERSION=...`: install a prepared release without starting it.
- `make start`, `make stop`, `make status`: control/inspect the owned shell.
- `make update VERSION=... BUILD_DIR=...`: prepare if needed, stop, install, start.
- `make dev-update BUILD_DIR=...`: fresh release, preflight, backed-up managed
  config/autostart deployment, config reload and owned-shell restart.
- `make hypr-settings`, `make autostart`: separate managed deployment gates.

The hyprpaper config is a separate explicit deployment; `make hypr-settings`
does not install it. See [wallpaper splash settings](docs/user-installation.md#separate-wallpaper-splash-setting-plan-022).
No desktop component expires on a timer. Autostart is not crash supervision.

## Local-only images and private artifacts

`config/menu/backgrounds/` and `config/menu/themes-previews/` are excluded from
Git because per-image redistribution rights are not cleared. Existing local
images are kept; an asset-free checkout works with palettes and available system
backgrounds. Missing imported previews are represented as absent, not downloaded
silently. [Origin metadata](upstream/theme-backgrounds.json) remains available.

Local packaging includes those directories **if they exist**. Consequently a
private bundle may contain images excluded from Git: do not publish such a bundle
without a separate asset and runtime-license review. The installer codec probe
uses an authored tiny image and does not require upstream wallpapers.

`work/`, build outputs, diagnostic logs, source snapshots, machine inventories,
backups and local configuration must remain private. Do not delete the retained
verified build or rollback material merely because they are ignored, and never
use a blanket `git clean -fdx` as project cleanup.

## Documentation and licensing

- [Architecture](docs/architecture.md) and [workspace modes](docs/workspace-modes.md)
- [Testing](docs/testing.md) and [clean-source verification](docs/clean-source.md)
- [Installation and rollback](docs/user-installation.md)
- [Upstream provenance](upstream/README.md) and [third-party notices](THIRD_PARTY_NOTICES.md)
- [Publication checklist](docs/publication.md) and [development summary](WORKLOG.md)

Original Omabuntu code and documentation use the [MIT License](LICENSE).
Third-party components retain their own notices and licenses. Selected upstream
sources and deterministic adaptations are documented under `vendor/` and
`upstream/`; do not remove them as disposable build output. No affiliation with
or endorsement by Omarchy or its authors is claimed.

A passing suite, an ignore rule or a source pin is not publication approval.
Review the complete candidate and Git history for private data and secrets before
creating a remote, committing or uploading anything.
