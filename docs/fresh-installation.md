# Fresh installation and updates: design and implementation status

The goal is a single `./install.sh` entry point on stock Ubuntu 26.04, with
`--update`, `--check` and `--rollback`. **The default entry now shows the live
guide. It can apply one reviewed stage at a time, but it is not yet a
working stock-system provisioner.** Explicit PPA and additive package stages
and a source-to-bundle runtime/Omasnap/plugin build stage are implemented. Generic
session files and next-login activation files can be prepared separately. Native
first-login validation and clean-target validation still remain. `--guide`
now shows the next implemented stage and can apply only that local stage.
The operator guide is [installer.md](installer.md). Plan [043](../plans/043-fresh-install-and-updates.md) tracks the broader installation work. Published distribution is documented in [releases.md](releases.md).
No PPA, packages, desktop files, session or service was changed by this audit.

## Terminal experience: implemented preview

Run `./install.sh` from your normal account, not via sudo. The shell wrapper
resolves its own directory and delegates to Python without writing bytecode.
It shows the accepted two-line Unicode block OMABUNTU wordmark, the tagline
"Your Ubuntu. Reimagined.", warm orange TTY accents and numbered readiness cards. No copied upstream font, art, external TUI dependency,
cleared terminal, fake progress bar or artificial delays are required.

```sh
./install.sh                      # installation readiness preview
./install.sh --update             # update readiness preview, no Git fetch
./install.sh --rollback           # review previous compatible release, no selector change
./install.sh --check              # nonzero until all apply gates are satisfied
./install.sh --plain              # no ANSI colors
./install.sh --json               # machine-readable preview, no banner
```

Colors turn off for redirected output, `NO_COLOR` or `TERM=dumb`. Dumb terminals
and limited output encodings use ASCII art; terminals too narrow for the chosen
art get a compact text banner. `--plain` disables color, not Unicode. Statuses are explicit: OK, CHECK, PLANNED,
BLOCKED. Default preview exit 0 means the preview ran, not installation success.
Source locks, target OS/architecture, tool presence and existing release integrity
are checked read-only. General readiness mode (without `--bundle` or `--rollback`)
still reports `ready_to_apply: false` until the stock-system pipeline is complete.
Explicit prepared-release plans are a separate implemented path described below;
only their confirmed `--apply` can change application files or restart the bar.

## PPA and package preparation: implemented stages

The entry point now has separate explicit source and package modes. These
commands run on a supported Ubuntu 26.04 x86_64 target as a normal user:

```sh
# Ubuntu tools needed before PPA verification (gnupg/gpgv, CA certificates, Git).
./install.sh --packages --base-only
./install.sh --packages --base-only --apply

# Download metadata/key into private work/, verify, show source plan; no /etc writes.
./install.sh --ppa

# Verify and ask before writing the two scoped files and refreshing APT metadata.
./install.sh --ppa --apply

# Review candidate origins, missing runtime/build requests and exact simulation.
./install.sh --packages
./install.sh --packages --apply
```

Without `--apply`, there are no system source/package changes. PPA review does
make HTTPS requests and write private evidence under `work/bootstrap/`.
Package review reads local APT metadata and simulates; it does not refresh it.
The base-only subset avoids a circular dependency on GnuPG before verifying
the PPA. Normal stock Ubuntu usually already has these base tools.

For a saved plan, use its printed path and exact digest rather than generating
a different new plan in a second process:

```sh
./install.sh --ppa --plan PATH --apply --approve DIGEST
./install.sh --packages --plan PATH --apply --approve DIGEST
# A saved base-only plan requires --packages --base-only on review/apply alike.
```

Apply without `--approve` requires interactive confirmation. `sudo` and APT use
the user's terminal, with no credential capture or automatic yes. JSON mode is
review-only for these system stages. Source/package modes cannot be combined
with bar-restart or local-release flags. These are building blocks, not a claim
that one invocation now completes a stock-desktop installation.

### Source identity and fixed destinations

The reviewed public Launchpad API names the archive `~cppiber/ubuntu/hyprland`
and signing fingerprint `A54D23B62FF3FCC76EFF71E8FDBAAA1CF0CCF48E`.
The preparer downloads that key and signed `resolute/InRelease`, validates the
primary fingerprint/expiry, verifies the signature using an isolated GnuPG
home/keyring, and checks the signed origin/suite/architecture. Changed identity,
revoked/expired keys, bad signatures or unsupported host stop the stage. A real
read-only verification of the published key and InRelease succeeded during
development; no source was installed by that check.

Only these managed paths are used on apply:

- `/etc/apt/keyrings/omabuntu-hyprland.gpg`
- `/etc/apt/sources.list.d/omabuntu-hyprland.sources`

The deb822 file uses HTTPS, `resolute`, `main`, `amd64` and a scoped `Signed-By`.
There is no `apt-key`, `trusted=yes` or signature bypass. Already configured
unmanaged duplicates and changed managed files/ownership/modes block apply;
the tool does not silently replace or duplicate the development machine's
existing PPA. It records pre-state and backs up existing managed bytes privately.
A failed source apply/metadata refresh retains evidence and requires review,
not automatic deletion of sources or a promise of package rollback. Adding a
source changes future APT candidate availability; review its trust accordingly.

### Package scope and limitations

`packages/bootstrap.json` supplies the initial compositor/session, native
services, base tools, Omasnap and plugin build requests. The planner merges
these with the existing runtime and Quickshell build manifests. This is an
initial request set, **not a fresh-VM-validated complete dependency closure**.
The pinned Nerd Font now has a separate verified staging/user-install step.
ABI-matched plugin pipeline integration remains separate work. The Omasnap
builder is implemented but not yet native-build accepted.
No Ghostty, browser/editor, VPN or corporate-agent installation is inferred.

The package stage reuses the existing guided simulation and pinned apply engine,
including resolved dependencies, before/after package state, holds/manual marks,
full origin policy and private transaction evidence. Missing candidates,
changes/removals of existing packages, incompatible Hyprland/Qt/Hyprlock target
versions, drifted plans and failed verification block apply. It never does a
blanket upgrade, purge or autoremove. This additive-only policy may block a fresh
installation if a PPA requires shared-library upgrades; such a transaction needs
a separately reviewed policy, not automatic relaxation of this guard.

Package maintainer scripts can activate native system services. The UI warns
about this before confirmation. No explicit network/Bluetooth/audio/login
restart is issued. The hyprlock package supplies its vendor PAM file; it is not
hand-edited and no authentication acceptance is implied.

## Source-to-bundle build stage: implemented

Once the planned runtime/build packages are actually installed:

```sh
# Read inputs and installed requirements only; no source/image download or compile.
./install.sh --build-release

# Confirm pinned source/artwork downloads, sandbox builds, checks and packaging.
./install.sh --build-release --apply --jobs 4

# Explicitly skip background/previews, using available system/user images later.
./install.sh --build-release --apply --skip-artwork
```

The pipeline builds the bar runtime (Quickshell/cpptrace), Omasnap and hyprbars,
stages the pinned desktop Nerd Font with its notices, then prepares a local
bundle. Hyprbars uses exact source headers and an isolated private build copy,
not installed mismatching headers or an old development binary. It does not
register the font, load the plugin or activate the session configuration.
It never installs packages, changes current/previous, starts the desktop, locks,
or captures. Build/deploy are distinct approval scopes. `--restart-bar` and
`--bundle` cannot be combined with build mode. A missing installed prerequisite
blocks it even if a private hand-installed development library happens to work.

Plans bind source pins, shell profile/bytes, builder/helper/config hashes and
installed required package versions. Default release names derive from these
inputs; `--release-version NAME` selects an explicit unique name. Interactive
apply confirms the exact digest; noninteractive JSON apply requires
`--approve DIGEST`. Rechecked input drift stops packaging. Source downloads
are hash/size checked and the original upstream installer is never executed.

The runtime builder returns an exact build directory, which is passed to
isolated linkage/QML checks; there is no search for a developer's latest build.
The new Omasnap builder verifies its pinned archive, six notices and three
annotation font hashes, builds against system LayerShellQt in Bubblewrap with
no network or host session sockets, and probes only `--version` offscreen.
The resulting binary and notices are verified again during packaging and live
inside the application release. No home-library rpath workaround is reused.

Artwork uses lock-specific private cache directories. Unchanged verified files
can be copied from older cache namespaces; only missing/changed managed files
need downloading. Previous caches and user images are never overwritten/pruned.
The package step consumes that explicit cache, not arbitrary images in the
checkout. `--skip-artwork` produces an intentionally asset-free bundle.

After packaging, the full bundle runs the existing native preflight. Failed
steps retain private reports under work/; no deployment occurs. An existing
bundle with exactly matching build provenance is verified/reused instead of
rebuilt. An explicit name collision is refused, not overwritten. Changed QML
currently causes a new bundle name. A compiled runtime, screenshot or plugin
stage is reused only when it is the single verified match. Several matches or a
symlink are rebuilt rather than selecting the newest developer build.

## Generic session configuration: implemented, not activated

After a compatible application bundle is installed, review the new profile:

```sh
./install.sh --session-config --keyboard-layout de

# Run from GNOME/TTY only after ending every user Hyprland session.
./install.sh --session-config --keyboard-layout de --apply
```

The source is `config/hypr/session-template.lua.in`, authored against the official
0.56.2 example and bind/global-dispatcher implementation at the exact pinned
Hyprland commit. Rendered Lua was executed with real Lua 5.4 and mock compositor
objects in tests, not loaded into the active compositor. Native first-login
acceptance remains pending.

The profile provides auto-positioned preferred monitors at scale 1, validated
XKB layout selection (initial default `us`), the installed default terminal,
Super+Space/ESC/Alt+Space/K menu shortcuts, Print and Super+Shift+S screenshot,
minimize, focus/move/workspace/fullscreen/float/scratchpad and mouse actions.
Screenshot/minimize use verified release-local helpers with bytecode disabled;
no installed app names or private display descriptions are copied.

The initial `hyprland.lua` is an editable include plus theme border literals.
Only `omabuntu-session.lua` is installer-owned. Existing unowned Lua or legacy
.conf profiles are refused, not replaced or guessed at. `--adopt-managed` replaces
only an untouched `omabuntu-managed` snippet whose file bytes still match the
reviewed template. Any extra line, including monitor rules, blocks adoption. A private receipt tracks
module ownership; edits/removal block updates. Later applies preserve main-file
additions, theme edits and previously chosen keyboard/lock options. Unknown XKB
layouts and unsafe paths are refused. Existing configuration on the development
machine was only reviewed and correctly blocked as unowned; nothing was changed.

No manual lock chord is added by default. After personally verifying manual
lock authentication and recovery on the target, `--enable-manual-lock` opts into
Super+Ctrl+L on key release; `--disable-manual-lock` removes that managed chord.
The installer never locks or changes PAM and this option is not an auth verdict.
Existing manual menu locking remains its separate explicit action.

Before source writes, approval and input state are rechecked under the application
control lock and every affected path is backed up privately. Live Hyprland is
refused even if the caller is in GNOME/TTY; no implicit auto-reload is attempted.
Synchronous failures restore unchanged tool-written files, while concurrent user
edits are retained and require manual recovery. Interrupted journals block retry.
The application updater also checks the receipt's helper contract so an update
or rollback cannot silently remove helpers referenced by this profile.

This stage does not enable/start services, start wallpaper, load plugins, log
out or start Hyprland. Application release rollback does not automatically revert
source configuration or font registration; those are separately backed-up domains.

## Guided path: one local stage

```sh
./install.sh --guide
./install.sh --guide --apply
```

The guide orders host, PPA, packages, font, build, release, session, activation
and a manual Hyprland login. It never reports `ready_to_apply` and never starts
Hyprland, hyprpaper, the shell or a plugin. `--apply` runs only the next stage.
PPA and package stages run only with the additional `--allow-system` flag.
`./install.sh --package-closure` simulates additions and dependencies without
installing them. That simulation is not a stock-Ubuntu dependency-closure verdict.
`./install.sh --acceptance` reports the same gates read-only and always leaves
native-login acceptance false. `./install.sh --rehearse` runs install, repeat,
failed start, update and rollback in a temporary home. It does not change the
host and is not VM acceptance.

## Published distribution

Use `make release VERSION=0.1.0` to build and publish a signed GitHub Release
after explicit approvals. Users install and update from the latest published
release, without a checkout or local build. Development checkouts use
`make build` and `make guide`. See [release setup and verification](releases.md).

## Next-login activation: files only

After session configuration and a release that contains an ABI-checked plugin:

```sh
./install.sh --session-activate
./install.sh --session-activate --enable-login --apply
```

Apply writes an owned activation file, titlebar rules and `hyprpaper.conf` with
`splash = false` only. The plugin path is the immutable release library, not
`current` or `~/.local/lib`. The titlebar minimize action uses the release helper.
`--enable-login` enables the existing oneshot user unit. `--disable-login` disables
it. Neither starts or stops a service, and apply is refused while Hyprland or
hyprpaper is running. Unowned wallpaper, unit or titlebar files are not overwritten.
No hyprctl, plugin load or compositor reload is performed. A real login is still
required before this is accepted.

## Desktop Nerd Font: implemented staging and user registration

The default shell/titlebar/lock family is `JetBrainsMono Nerd Font`, which is
not provided by the unpatched Ubuntu JetBrains Mono package. The installer now
pins the Regular face from Nerd Fonts v3.4.0 with exact commit, size and SHA-256
in `upstream/desktop-font.json`. Its folder OFL and upstream licensing overview
are preserved under `licenses/Desktop-*`. No TTF is committed.

```sh
./install.sh --font          # inspect destination/conflicts, no download or writes
./install.sh --font --apply  # confirm download, user installation and cache refresh
```

Build mode stages this face into `assets/fonts/` with its notices under
`licenses/desktop-font/`, but does not activate it. Font apply separately verifies
bytes, family and required icon glyphs, retains old content-addressed versions,
records previous file states/backups, installs only into the user fonts directory
under `omabuntu/<hash>`, refreshes that cache and checks family/glyph resolution.
No sudo, GTK/terminal defaults, saved font choice or desktop restart. Symlinks,
local conflicts and drifted approval are refused. Failed registration retains
files and a private `font-transactions/` journal rather than deleting fonts.
The actual pinned face's family/glyph coverage was probed read-only during
development; real user registration was not performed.

The standalone hyprbars builder now reads installed Hyprland's exit-only
`--version-json`, without needing a running desktop. It uses fresh outputs,
retains existing builds, records library hash and refuses binary drift during
compilation. The bootstrap pipeline now uses a separate isolated builder:
`build_plugin.py` locks both source archives, verifies BSD notices, generates
private headers/protocol bindings and checks the exact installed client ABI.
ELF architecture, absence of an ELF interpreter, linked shared-library availability
and defined plugin exports are checked in Bubblewrap. No dlopen or entry-point
probe occurs; unresolved compositor symbols are expected, not a linkage error.
All scanner failures/timeouts block the build rather than being silently ignored.
Protocol notices are preserved with the two root notices.

The packager receives the exact returned stage and embeds `native/hyprbars.so`,
a byte-hash/ABI descriptor and notices. No executable directory is added to PATH
and the old `~/.local/lib` plugin is not overwritten. Input/dependency/native
identity changes stop packaging; old build directories are retained. Candidate
updates/rollback check the descriptor against the installed binary and libraries
again before stopping the bar. Non-plugin older bundles remain supported.
The fresh-session loader is still pending. No preparation step loads/unloads a
plugin or runs hyprpm reconciliation. Native source compilation has not run in
this implementation phase; source archives and headless ABI metadata were
actually checked, while build/ELF process outputs in unit tests are simulated.

Native compilation and VM acceptance are still pending: the automated suite
uses fake compiler processes and fixture stages. Do not interpret those tests
as evidence that a fresh machine has all build requirements or that plugin/font
and desktop setup are complete.

## Prepared local release apply: implemented

For a trusted locally prepared bundle, the new coordinator validates the exact
bundle, selected releases, launcher, running-bar identity, native target and
user-state contract. Preparing a bundle is still the existing explicit build
workflow; no new code fetch or build occurs in these commands.

```sh
# Review a new bundle. Replace PATH with an actual prepared release directory.
./install.sh --update --bundle PATH --restart-bar

# Repeat with --apply: interactive confirmation of the exact displayed plan.
./install.sh --update --bundle PATH --restart-bar --apply

# Noninteractive apply requires the digest printed by the matching review.
./install.sh --update --bundle PATH --restart-bar --apply --approve DIGEST

# Review previous release, then explicitly apply if desired.
./install.sh --rollback --restart-bar
./install.sh --rollback --restart-bar --apply
```

For first application installation omit `--update`. No bundle or compatible
compositor/dependencies are automatically created by this path. A stopped bar
stays stopped unless `--restart-bar` explicitly grants a bar start. If the bar is
running, a real version switch without that flag is refused. Reinstalling exact
current contents is a no-op and does not restart a running bar.

Apply serializes on the manager control lock, repeats the reviewed prestate,
runs the existing host/native/QML/WebP preflight, checks for a locker, journals
and backs up the launcher/selectors, then copies/verifies the complete candidate
before stopping the old bar. Source/launcher/process drift invalidates approval.
No new bar has a lifetime timer. On synchronous switch/start failure the old
selectors and launcher are restored, and the old bar is started again only if
it was previously running. If recovery fails, stop and inspect the journal;
do not force a retry or kill an unrelated process.

New packaged releases declare `update_contract` with user-state schema 1 and
the native target. Different schemas or native ABI targets are refused; there
is no state migration in this slice. An existing unversioned release needs
explicit `--allow-legacy-state` in both review and apply after compatibility
review. This acknowledgement is not an automated compatibility verdict. Older
rollback bundles without a valid update contract cannot use this coordinator.

Journals and backups live under the private state directory's `updates/` tree;
inner manager selector changes keep their existing `transactions/` journal.
Power loss/SIGKILL leaves an unresolved journal and blocks later updates.
`./install.sh --recover-update` reviews exactly one interrupted outer journal.
`--apply` restores its recorded selectors and launcher; it does not resume the
new release, delete the journal, or start a bar unless `--restart-bar` is
separately passed for a bar that was running before the interruption. A running
bar blocks selector recovery without a forced stop. Divergent selectors or
launcher bytes remain manual. This is explicit recovery, not proof that every
power-loss case can be reconstructed.
User preferences and config are not migrated or replaced. No package, PPA,
compositor restart, autostart change, lock or capture occurs.

`--json` emits one JSON document, without the banner. Plans are read-only and
`--check --bundle PATH` validates this local release plan only, not runtime or
stock-system readiness. Native preflight on apply can write private reports
under `work/installer/`; it performs bounded isolated probes before any bar stop.
An apply approval digest is content/prestate consent, not a publisher signature.

## Reuse and remaining gaps

| Area | Existing implementation | Fresh-machine/update gap |
|---|---|---|
| Local releases | Verified pre-staging, recovery, pinned source fetch and schema policy that refuses unreviewed migrations | Clean-VM lifecycle validation |
| Package apply | Scoped signed-PPA preparation/apply, additive simulation, closure summary and an explicit refusal of installed-package upgrades | Fresh-VM dependency closure and end-to-end integration |
| Source runtime | Pinned builds, exact stage checks, and reuse of one verified component stage | Native clean-target build validation |
| Screenshots | Reusable sandbox builder, pinned source/fonts/notices, release-local executable, manager and generic hotkey wiring | Native build/VM and interaction acceptance |
| Titlebars | Isolated pinned archive builder, exact commit/client ABI, inert artifact/descriptor/notices packaging and update checks | Fresh-session loader plus native build/first-login acceptance; no blind reuse after PPA upgrades |
| Hyprland config | Owned generic module plus next-login activation files for plugin, titlebar, splash and optional user unit | Native first-login acceptance; private configs remain untouched |
| Fonts | Pinned OFL Nerd Font staging, family/glyph probes and separate user registration | Native fresh-session visual acceptance; do not change existing font preferences |
| Images | Pinned downloader, release staging, and a next-login wallpaper record when none exists | Native wallpaper acceptance; individual redistribution rights remain unresolved |
| Tests | Unit suite and isolated local-bundle preflight | Fresh stock VM install, repeat install, update, conflict handling, interrupted apply and rollback |

The PPA stage verifies `cppiber/hyprland` signing identity and signed suite data.
That is not proof of future package behavior or clean-target dependency closure;
candidate simulation and functional/VM acceptance remain separate.

## Artwork: implemented building block

The committed `upstream/theme-backgrounds.json` lists 97 wallpapers and 23
picker previews across 23 themes, totaling 64,913,495 bytes. Images themselves
remain outside Git. The new downloader uses only these exact pinned URLs and
does not discover a moving upstream tree or rewrite the record.

Commands below are implemented, independent of the future installer:

```sh
# Plan only: no downloads or writes.
python3 tools/download_backgrounds.py

# Offline validation: no download and no directory creation.
python3 tools/download_backgrounds.py --check --output work/artwork-cache

# Explicitly download missing files into a private staging/cache directory.
python3 tools/download_backgrounds.py --download --output work/artwork-cache
```

`--check` exits nonzero when anything is missing or differs. `--download`
verifies exact length and the committed Git blob hash, reports SHA-256 for each
verified file, reuses verified local files, and refuses local conflicts. HTTPS
requests have a 30-second probe timeout, bounded replies and no redirects.
Verified data is published atomically without replacing a concurrently created
file. Interrupted downloads do not install partial images. Existing user
images are never pruned. No videos, fonts, scripts or lock-specific art are
fetched. Nothing is activated by these commands.

**License limitation:** upstream's root MIT declaration does not establish an
individual license for every image. Direct local downloads do not clear public
redistribution. The downloader displays this limitation; images must remain
separate from published Omabuntu bundles. The future installer must offer a
clear download/skip choice. Skipping or failed downloads must visibly report
missing previews and use available system/user backgrounds, not silently claim
full artwork parity.

## Updates are a first-class requirement

Use the same pipeline for install and update: resolve a concrete reviewed
source revision, stage everything, verify sources/assets/native compatibility,
show changes, back up owned paths, then switch the application release. Never
`git reset --hard` a user's checkout or run a moving branch via curl-to-shell.
A locally computed checksum proves content consistency, not publisher trust.
`./install.sh --source-update` reviews that policy. `--apply` downloads only
missing exact archives into `work/source-cache`. It does not fetch Omarchy's whole
tree, move a branch, reset a checkout, build, or deploy. A newer upstream revision
still requires a separate human pin review.

Keep these domains distinct:

- **Omabuntu release:** bar/QML/helpers and its compatible runtime. Keep the
  prior release; stop/restart only the recorded bar after approval.
- **User configuration/data:** preserve browser/terminal choices, weather city,
  theme/wallpaper, dock pins and private monitor rules. Merge owned blocks,
  refuse conflicting user edits, and back up state before schema migrations.
- **APT/PPA and compositor:** do not silently run a system upgrade. Simulate
  and approve exact changes independently. Hyprland/Qt/plugin ABI changes may
  require a separately approved session transition, not a live bar-only swap.
- **Artwork:** cache/reuse verified files and fetch only missing/new ones.
  Preserve selected and user-added images even if an upstream release removes
  them. Cache cleanup must not break the rollback release.

Serialize deployment, journal before mutation and detect unfinished updates on
retry. On failed bar startup, restore the previous verified application and
managed config where safe. Application rollback does not undo APT, PPA, or
arbitrary user-data changes. Refuse schema-incompatible rollback rather than
pretending it is safe. Never delete the last working release automatically.

GNOME remains available as the recovery desktop. No automatic lock, reboot,
logout, PAM override, boot/security-policy changes or corporate provisioning.
Package-managed authentication files are not hand-edited. Neither successful
installation nor a passing suite proves lock authentication or recovery works.
