# Fresh Ubuntu installation, updates, and downloaded artwork

## Goal and evidence

Provide one shell entry point for installing the currently implemented Omabuntu
on stock Ubuntu 26.04, including reviewed PPA/dependencies, plus repeatable
updates and rollback. The user additionally requires background images to be
downloaded, not committed to Git. This plan covers the installer request and
its update/artwork requirements together.

Compared repository evidence: tools/install.py, tools/user_install.py,
tools/package_user.py, Makefile, packages/installer-runtime.json,
upstream/source-lock.json, upstream/omasnap-source.json,
upstream/theme-backgrounds.json, docs/dependencies.md and config/hypr/minimal.lua.
Omarchy is pinned at 03ff1eff3812933f7088484533784d2f63eaf19a. Preserve
original sources with the existing reviewed Ubuntu adaptations, not an Arch
installer. No private workstation config is an installation template.

## Current gaps

- Existing local-release install/update/rollback and transaction recovery are
  reusable, but tools/install.py requires an already compatible compositor.
- Runtime manifest omits a complete stock-machine compositor/service/toolchain
  closure. Dependencies document cppiber/hyprland; candidate availability and
  the repository signing identity still need verification before PPA apply.
- Source builder pins Quickshell/cpptrace. Omasnap has a source/license pin but
  no reusable complete build/package pipeline here; its installed binary is
  external to releases. Hyprbars is tied to exact compositor headers/ABI.
- minimal.lua is an evaluation profile, hardcodes ghostty, and is not the
  production user's complete configuration. Export a reviewed generic baseline,
  not machine-specific monitor descriptions, corporate settings, or app paths.
- Source updates and native ABI updates must not be conflated. PPA changes can
  invalidate plugins and require a later compositor session transition.
- Existing artwork importer discovers GitHub's tree at runtime, rewrites the
  tracked record, reads downloads unbounded, and replaces mismatched files.
  Build a locked-manifest downloader instead for install/update.
- Wallpaper images have no per-image license declaration in the captured source.
  Root MIT is not independent proof for each image. Download locally from the
  pinned upstream after a visible notice; never bundle them into public releases
  or describe redistribution rights as cleared.

## Proposed interface (read-only preview implemented; apply pending)

- ./install.sh: inspect, show changes, request explicit local consent, install.
- ./install.sh --update: resolve and review a concrete source revision, stage and
  validate a full new release before switching; never git-reset a user checkout.
- ./install.sh --check: no system/desktop changes; report missing prerequisites.
- ./install.sh --rollback: restore the verified previous application/config
  state after review; explain system-package rollback is a separate domain.
- Keep one Python standard-library orchestrator behind the shell entry point.
  No curl-to-shell, blanket apt upgrade, automatic reboot, or root GUI processes.

## Update contract

Separate Ubuntu/APT packages, source-built runtime/plugins, Omabuntu immutable
releases, user configuration, persistent user data, and optional artwork.
Resolve a concrete trusted source commit before execution; record it with input
hashes and the dependency/source locks. Verify Git fetch/ref failures and remote
identity; a checksum is not a publisher signature. Build in an isolated staging
area and do all feasible verification before stopping the owned bar.

Serialize updates, journal phases and backups, refuse unfinished transactions,
and retain the prior working release. Preserve weather city, browser/terminal
preferences, themes, wallpapers, dock pins and workspace data. Check old/new
state-schema compatibility before migration; back up any migrated state, and
refuse rollback where incompatible state cannot safely be restored. Merge only
installer-owned config blocks; reject conflicting user edits rather than replace
them. Only restart the recorded bar after explicit approval. If startup fails,
restore previous selectors/config and restart the previous bar where safe.

Do not claim a full rollback of APT/PPA changes. Simulate exact package requests,
show origins and dependency changes, reject removals/unrelated upgrades, and
reapprove if package policy changes. Hyprland/Qt/plugin ABI changes block a
live swap and require a separately approved session transition. Do not change
PAM, sudo, boot/security policy or management services. Preserve GNOME login.
Installing the vendor hyprlock package may supply its package-managed PAM file;
never hand-edit or override it, and keep authentication acceptance separate.

## Package/source preparation slice

Launchpad's public HTTPS metadata identifies the cppiber/hyprland archive's
signing fingerprint as A54D23B62FF3FCC76EFF71E8FDBAAA1CF0CCF48E. Before
implementation, the resolute InRelease advertised Ubuntu 26.04/main/amd64 and
origin LP-PPA-cppiber-hyprland. Pin that identity, validate the downloaded key
fingerprint and signed InRelease using isolated GnuPG, and refuse redirects or
changed signing identity rather than trusting a server URL alone. This check
is not endorsement of future package contents. Never disable APT authentication.

Use a fixed deb822 source with a scoped Signed-By key, not apt-key or a global
trusted key. Review should stage only private local evidence. Apply must require
fresh digest confirmation, root-owned fixed destination paths through narrow sudo
argv, before-state recording and no overwriting different local source/key files.
Detect an already configured unmanaged duplicate and ask for manual source review.
APT metadata refresh is explicit and separate from installing packages. Failed
refresh/source apply keeps a journal and never silently purges existing sources.

Build the bootstrap package request from runtime, compositor/session, Quickshell,
Omasnap and plugin build groups, not a blanket desktop/system upgrade. Reuse the
existing simulation/pinned apply engine; allow no removals or changes to existing
packages in this slice. Include runtime desktop services but warn that Ubuntu
package maintainer scripts can start services. Do not explicitly restart network,
Bluetooth, login, audio, or corporate services. The new manifest is an initial
request inventory, not a verified fresh-machine dependency closure. Existing
GNOME/default applications remain; no browser/editor installation is inferred.

## Desktop font and headless plugin preparation

For stock systems, the shell/lock/titlebar require JetBrainsMono Nerd Font,
not just Ubuntu's unpatched JetBrains Mono package. Review and pin the Regular
face from nerd-fonts v3.4.0 at fa7b859994228a9c8759f99c55a8d31ee92a1b5e.
The folder explicitly declares OFL 1.1; preserve its notice and upstream licensing
overview before fetching/staging the TTF. Verify size, SHA-256, family and required
Nerd glyphs. Stage it inside new releases and provide a separately confirmed,
per-user installation/cache-refresh step. Never change GTK, terminal or existing
font preferences or replace user fonts. Use a content-addressed directory and
record prior file states; refuse conflicts and symlinks, retain previous versions.
Font activation is not implied by a source build or application update.

Hyprbars cannot depend on an already running Hyprland instance during fresh
installation. Obtain the installed binary's version/commit/ABI via its documented
exit-only JSON version flag; use the same data when generating version headers.
Never run hyprpm reconciliation or load/unload a plugin during build preparation.
Retain exact-commit and ABI checks. Integrating a verified plugin artifact with
fresh-session config remains a separate task, not permission to modify the live
compositor or reuse a private development plugin blindly.

## Isolated plugin artifact slice

Add a separate bootstrap-only builder, retaining the historical standalone
builder for existing maintenance workflows. Lock GitHub archives for both
hyprland-plugins 7644cecdb947060682891a0db2a0cdc5c0b9e704 and Hyprland
headers efb50993780079460b0cbed1363e2166a2de1d9f. Both root licenses were
reviewed as BSD-3-Clause in the exact local source checkouts before import;
preserve the two notices and verify them against the downloaded archives.
Generate version/protocol headers in a private writable build copy, not the
shared source checkout; retain pristine extracted sources read-only in Bubblewrap.
Use clean installed-binary metadata, exact commit/version/ABI and package input
rechecks. Probe ELF dependencies and plugin exports without dlopen, invocation
of plugin entry points, hyprpm, or a live compositor. Undefined compositor symbols
are expected and must not be confused with missing shared-library dependencies.
Stage only the verified plugin library, ABI descriptor and notices into immutable
application bundles; bind the exact returned build directory into the pipeline.
A load/first-login activation gate is separate and remains pending in this slice.
No native compilation or desktop deployment is authorized by this implementation.

## Source-build pipeline slice

Connect the existing pinned Quickshell/cpptrace sandbox builder, isolated runtime
checks and local packager. Add a reusable Omasnap builder for pinned commit
a432f40b14598a4a02b89fa0054f9a0ba3662dd4, using the system LayerShellQt
package instead of a developer-home library. Its 6,050,541-byte archive was
reviewed at SHA-256 ac184e0e051b0fdfb157601c8cc7296e98d02920c78936e07f13805fe4339548.
Verify all previously recorded notices and the three bundled font hashes before
building. Use Bubblewrap with no network/home/session access, read-only sources,
private outputs, bounded build commands, ELF/linkage checks and only --version
as a non-capture execution probe. Never run install-omarchy or an Omasnap capture.

`--build-release` should plan by default and require explicit `--apply` plus
confirmation for downloads/builds/private outputs. It must require installed
build dependencies, serialize the pipeline, use exact returned build paths
rather than "latest", and never install packages, change selectors or restart
the desktop. Bundle the verified Omasnap executable and license notices with the
application release. The manager then selects the release-local Omasnap for
menu actions, while legacy releases retain the old approved-binary fallback.

Artifact preparation does not complete native build acceptance, font registration
or first-login activation. State the scope before confirmation; don't call an
application/artifact bundle a complete stock-system install. Source input drift, failed checks,
missing requirements and an incompatible stage must stop packaging. Retain
private failed-build reports. No release publication is authorized.

## Generic session configuration slice

Create a dedicated fresh-session template, not a copy of the private workstation
configuration or a repurposing of the evaluation minimal.lua. Before authoring,
re-read the official example and global-dispatcher/bind implementation from
Hyprland efb50993780079460b0cbed1363e2166a2de1d9f; those files in the verified
workspace checkout match the pinned source. Use preferred/auto monitor placement
at scale 1, selectable validated keyboard layout, installed default terminal,
original menu/app-grid/keybinding shortcuts and window/workspace/mouse actions.
Screenshot/minimize bindings call verified release helpers with fixed argv and
bytecode disabled. Package the existing minimize helper instead of requiring a
private standalone installation. Manual lock shortcut is an explicit opt-in,
not an authentication/recovery verdict. No idle/suspend policy.

The owned module contains no autostart or plugin loading. Initial hyprland.lua
is a small editable include plus border-color literals compatible with the theme
backend. Refuse an existing unowned Lua or legacy .conf profile. Keep a receipt
for the owned module; later updates preserve the editable main file and reject
module drift. Preserve keyboard/lock options unless explicitly changed. Save
pre-state/backups before writes and restore on synchronous failure without
clobbering concurrent user edits. A pending journal blocks retries. Source apply
must refuse while any user Hyprland process is running, even from a GNOME/TTY
terminal; never trigger implicit config reload, logout, lock or a capture.
Add a separately confirmed --session-config stage, with review-only default.
Actual session/autostart/wallpaper/plugin activation remains separate work.

## First operational slice: prepared local releases

Before PPA/bootstrap apply is complete, support explicit prepared local bundles
through the same entry point. `--bundle PATH --apply` reviews file identity and
host/runtime preflight; `--update` requires an existing release. The outer
coordinator uses the manager's control lock and a separate persistent journal,
stages a full immutable candidate before stopping the owned bar, preserves
current/previous and the exact launcher pre-state, and restores these if start
fails. `--restart-bar` is a separate session-lifetime grant; without it a running
bar blocks deployment. Reinstalling identical content is a no-op, not a restart.
Require an approval digest or interactive confirmation of the exact plan.

Declare user-state schema and native target in new bundle metadata. No migrations
are performed. Refuse mismatched schema/native targets before stopping; an
unversioned older release needs an explicit `--allow-legacy-state` acknowledgement,
not an assumed compatibility claim. Missing/changed bundle, drifted launcher,
concurrent update, interrupted journal or unknown/failed locker lookup blocks
apply. Refuse updates during an active lock. Recovery after interruption is
explicit, never a blind startup retry. Application rollback does not revert
APT or erase persistent user preferences. Tests must use fixture releases and
mocked startup, not the active desktop.

## Artwork download contract

Use the committed record as the complete allowlist: currently 23 themes,
97 backgrounds and 23 previews (64,913,495 bytes total). Download exact URLs at
the pinned Omarchy commit, verify byte count and Git blob hash before promotion,
record SHA-256 in private evidence/cache, and reject redirects, unsafe paths,
symlinks, oversize responses and short/corrupt downloads. Use atomic temporary
files. Verify cached files and reuse them. Report local conflicts instead of
clobbering them. Never rewrite tracked provenance during installation.

Fetch only changed/missing managed assets during update. Retain user images and
selected images removed upstream; do not prune caches/release rollback inputs
implicitly. Separate downloaded assets from redistributable code bundles. Use
system backgrounds or existing images when downloads are declined/unavailable;
report the degraded state instead of claiming all themes have previews.
No videos, lock art, fonts, scripts or installers are included in this downloader.

## Presentation

The user requested a pleasant Omarchy-inspired terminal entry with an Omabuntu
ASCII wordmark. Use an original text-art design, not unreviewed upstream binary
fonts or images. Show numbered phases, honest status cards and a concise change
summary before confirmation. Honor NO_COLOR, redirected output and narrow
terminals. The user accepted a compact two-line Unicode block wordmark and
"Your Ubuntu. Reimagined." tagline instead of the initial hash-glyph design.
Use it on capable terminals; retain ASCII for dumb/limited encodings and compact
text when the terminal is too narrow. Do not fake progress or clear useful
terminal history. No additional TUI dependency. The first implemented frontend is explicitly a readiness preview,
not an installer that can apply the still-incomplete provisioning pipeline.

## Implementation tasks and approval boundaries

- [x] Audit current repository installer/update/artwork paths and record gaps.
- [x] Implement/test locked artwork downloads with offline validation and reuse.
  `tools/download_backgrounds.py` plans by default; check is offline, downloads
  are explicit, conflicts are preserved and tracked provenance is never changed.
- [x] Implement pinned PPA identity, isolated key/signature verification, scoped
  source/key destinations, pre-state/conflict checks and explicit source apply.
- [x] Implement base-only and merged bootstrap package review/apply using the
  additive, pinned guided APT engine; reject incompatible native targets.
- [x] Decide the shared-library upgrade policy: additions do not require one, and
  installed-package upgrades/removals stay refused, including native packages.
- [ ] Validate the complete runtime/build package closure on a stock Ubuntu VM.
- [x] Implement pinned sandbox Omasnap build/probe/notice verification and
  release-local packaging, plus combined exact-path runtime/build/artwork staging.
- [x] Reuse a compiled stage only when it is the single verified match; never select
  the newest of several builds.
- [x] Implement pinned/licensed desktop font staging and separate per-user
  registration with family/glyph checks, backups and no preference edits.
- [x] Remove the live-session dependency from standalone hyprbars metadata,
  retain old outputs and record library hash/post-build binary identity.
- [x] Integrate isolated pinned plugin/header builds, exact native client-ABI
  checks, inert artifact/descriptor/notice packaging and update pre-switch gates.
- [ ] Validate native Omasnap/plugin builds and the prepared next-login loader on stock Ubuntu.
- [x] Implement a generic session module and editable main entry with validated
  keyboard selection, release-helper binds, explicit manual-lock opt-in,
  ownership receipts, backups, drift/live-session refusal and safe failure restore.
- [x] Prepare next-login plugin, titlebar, hyprpaper splash and optional user-unit
  files without starting, loading or reloading anything.
- [x] Add a one-stage guide that reviews the implemented path and applies only the
  next local stage, without packages, service starts, plugin loads or bar restarts.
- [x] Add a read-only acceptance command that reports stock-install gates and never
  claims a native Hyprland login or installs packages.
- [ ] Validate native first-login activation and the guided path on stock Ubuntu.
- [x] Implement original ASCII welcome and shell/Python read-only readiness UI,
  including install/update/rollback previews, check exit status and plain/JSON modes.
- [x] Implement explicit prepared-bundle review/apply with staging before stop,
  shared control lock, launcher/selectors backup, journal and synchronous
  start-failure rollback. Declare update/state/native contracts in packaged releases.
- [x] Complete one-stage orchestration for PPA/packages behind explicit --allow-system,
  plus a read-only closure summary that does not install or claim VM acceptance.
- [x] Implement local-release locking/journaling, schema/native-target refusal,
  no-op reinstall and previous-release rollback; test with fixture bundles.
- [x] Implement explicit interrupted outer-journal recovery that restores prestate
  and never resumes the new release or starts a bar by default.
- [x] Implement pinned source acquisition: exact reviewed archives only, private
  cache, no checkout reset, and no claim that a checksum is a publisher signature.
- [ ] Review and pin any newer upstream source revision before offering it as an update.
- [x] Implement an explicit schema policy: schema 1 only, no registered migration,
  no state rewrite, and rollback only when both directions are reviewed.
- [x] Test blocked unfinished journals, asset conflicts, launcher/bundle approval
  checks, preflight/staging failure, control-lock contention and failed-bar rollback.
- [x] Adopt only an untouched managed Hyprland snippet; refuse every extra user line.
- [ ] Test actual power-loss recovery, native package updates and VM config merges.
- [x] Document implemented artwork, release, PPA and package commands, along
  with remaining bootstrap/VM gates and license/network/security boundaries.
- [x] Run unit tests and clean-source checks after implemented phases; repeat
  after future integration. No live source/package apply has been exercised.
- [ ] Validate fresh install, repeat install, update and rollback in stock Ubuntu VM.

This plan authorizes no live PPA, package, service, desktop or Git changes.
Actual application, VM creation, service activation, session transitions and
publication still require their own approvals. One-time shell consent cannot
promise that sudo credentials remain cached across a long build.
