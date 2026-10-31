# Clean-source verification

## What the source candidate contains

Public source includes original project files, tests, selected reviewed vendor
source, license texts and upstream provenance. It excludes `work/`, snapshots,
backups, compiled artifacts and the local-only wallpaper/preview directories.
No private image download or prebuilt runtime is required for the unit suite.

From a checkout with Python 3 and Make:

```sh
make help
make test
python3 tools/build_runtime.py
python3 tools/check_runtime.py
```

The latter two commands only print plans. The build implementation requires
Python 3.12 or later. Tests use standard-library fixtures; executable Lua tests
need the system Lua 5.4 library and explicitly report a skip when unavailable.
A missing optional system library is not a silently passed native test.

## Verify an export without existing local inputs

In the project Git working tree:

```sh
python3 tools/check_clean_source.py --run
```

The checker reads Git's tracked/untracked non-ignored candidate list, copies
current regular source files into a new ignored `work/clean-source/<id>/source/`,
and never copies Git metadata, old work contents, local images or environment
files. Explicit private-path exclusions also protect against accidentally tracked
private artifacts. This is not a secret scanner: other tracked/private content
still requires manual and history review.

It records that the export initially has neither work inputs nor local images,
then runs the full unit suite and fixed read-only CLI/help/plan checks. Test HOME,
XDG directories and temporary storage are private and new. It also checks that
packaging/development update refuse a missing explicit build directory before
any packaging or live action. Exit status, timeout/partial logs and limits are
recorded under the private case. It never initializes another Git repository,
changes the index, installs, downloads, builds or activates services.

The export uses the same host Python/native dependencies. This verifies source
independence from old inputs, not a separate OS, bit-identical native rebuild,
visual acceptance, lock authentication or complete dependency availability.

## Native build and package flow

After separately reviewing dependencies and approving source downloads/building:

```sh
python3 tools/build_runtime.py --build --jobs 4
```

Use the new directory printed by that command, not an example timestamp and not
an automatically selected latest directory:

```sh
BUILD_DIR=work/builds/your-build-id
python3 tools/check_runtime.py --run --build-dir "$BUILD_DIR"
python3 tools/check_desktop_panels.py --run --build-dir "$BUILD_DIR"
python3 tools/check_command_menu.py --run --build-dir "$BUILD_DIR"
python3 tools/check_image_picker.py --run --build-dir "$BUILD_DIR"
make package VERSION=local-test BUILD_DIR="$BUILD_DIR"
make preflight VERSION=local-test
make plan VERSION=local-test
```

Replace `your-build-id` with the actual new build directory. Every consumer still
verifies the source lock, successful stage evidence and artifact hashes. A path
argument does not bypass verification. The builder's dependency and shader gates
remain unchanged. A full native build is not performed by the source-export check.

Without local images, theme palettes still exist and imported previews are absent;
background discovery can use documented system/user image directories. The
installer's WebP decode probe uses an authored tiny gradient image. Local-only
assets are included in a private bundle when present: an ignored image is not
therefore safe to publish inside that bundle. No automatic asset fetch occurs.

Installation, managed config/autostart deployment, shell start and any live
reload are separate steps in the [installation guide](user-installation.md).
Never use `make dev-update` as a read-only clean-checkout check.
