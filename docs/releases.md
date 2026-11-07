# Publishing and installing GitHub Releases

## Status

The current published release is **[v0.2.2](https://github.com/harald-mue/omabuntu/releases/tag/v0.2.2)**,
published on 2026-11-07 at 18:17:35 UTC from commit
`bb5a20c63bcc4e9e2a295497aba60aa4aadb7043`. It is public, not a draft or
prerelease. All four expected assets are present: the Ubuntu 26.04 x86_64
archive, `release.json`, `SHA256SUMS` and `SHA256SUMS.sig`. Retained artifact
hashes match GitHub's asset digests; publisher-signature, source-export,
bundle-integrity and artwork-exclusion checks pass. Publication does not
establish fresh-machine or native/security acceptance.

Historically, the signed v0.1.0 release was published, but its stock-VM installation failed.
It is not fresh-machine accepted. New source builds use a separate hyprpm policy
instead of shipping a native titlebar library; existing artifacts are immutable
and do not acquire this change. New builds target source-reviewed Hyprland
0.57.0. On the development workstation, the pinned manager build/recovery,
live plugin activation and explicit application handoff completed; the user
reported that the bar/menus appear to work. This is not stock-VM, first/repeat
login, generic migration or security acceptance: those remain outstanding.
The project remains an Ubuntu-native integration, not an Omarchy provisioner.

### v0.1.1 release scope

- Separate runtime, application-source-build and plugin-build package scopes;
  published application installation does not require the application toolchain.
- Source-reviewed Hyprland 0.57.0 target; pinned local hyprpm builds instead of
  shipping an ABI-specific titlebar library in new application bundles.
- Independent preparation, live load, titlebar-rule and persistent-login consent;
  explicit legacy manager migration and narrowly scoped failed-checkpoint recovery.
- Reviewed Ubuntu PPA system-header support, verified backups/headers and inactive
  ownership receipts only after successful preparation. Header updates run
  without a compositor socket; plugin activation remains a separate live action.
- Explicit 0.56.2 to 0.57.0 application handoff on an already matching session;
  private profiles and healthy active manager plugins are preserved.
- Ordinary installer questions default to Yes on Enter. Typed safety phrases,
  noninteractive approval guards and commit/publication prompts remain separate.
- Next-login preparation detects unit-state drift, rolls back its initial
  wallpaper record on file-stage failure, and requires manual review after a
  failed systemd operation instead of claiming complete restoration.

GitHub release metadata and verified signed artifacts determine availability;
this source scope section does not itself claim that v0.1.1 has been published.

### v0.1.6 release scope

Since v0.1.1 the installer stayed the single user entry point and accumulated
reviewed repairs:

- v0.1.2 keeps setup resumable through that one entry point: a blocked optional
  plugin-build scope can be deferred without aborting, and the same run continues
  instead of pointing at a temporary cache.
- v0.1.3 matches plugin build headers to the installed udev runtime, proving the
  exact `libudev-dev` version for the installed `libudev1` and re-simulating an
  additions-only transaction before any package step.
- v0.1.4 repairs an enabled-but-unloaded hyprbars through `install.sh`, with
  verified backups and one unforced `hyprpm reload`; JSON or a digest cannot
  bypass the live prompt.
- v0.1.5 offers and downloads the pinned Omarchy theme artwork into the private
  user directory on artwork-free public releases; releases stay artwork-free.
- v0.1.6 adds per-file progress to that artwork download and suppresses the
  Hyprland update-news popup, which is drawn through Hyprtoolkit/EGL and
  segfaults on systems without hardware GL (for example a Q35 VM without 3D
  acceleration). The popup is a one-time event per Hyprland upgrade.

A clean-VM test of v0.1.5 completed application installation, the private
artwork download and next-login preparation; the Omabuntu bar rendered in the
Hyprland session. The two observed crashes (`hyprpaper` in a GNOME session and
`hyprland-update-screen` after the Hyprland upgrade) both came from
Hyprtoolkit/EGL tools on a GPU-less VM, not from Omabuntu code.

No blanket APT upgrades/removals, general native-target bypass, automatic private
profile conversion or legacy login-loader adoption is added. First/repeat login,
stock-VM dependency closure and a second distinct live application update/rollback
still need acceptance. Current automated coverage and actual-payload rehearsals
do not remove those limitations. Artwork remains excluded from public builds.

### v0.2.0 release scope

Version **[0.2.0](https://github.com/harald-mue/omabuntu/releases/tag/v0.2.0)** is
published. The tag identifies commit `9537b211a02fa5f74c40558f3f31f218e0427ec2`.
Post-release source-documentation updates do not replace its immutable artifacts.

Changes since v0.1.9:

- Create and validate the private build `work/` root before nested bootstrap
  directories. This fixes fresh isolated release builds under permissive umasks
  without weakening checks or changing existing unsafe directory permissions.
  Artwork-free builds also report honestly that theme artwork is excluded.
- Rebase admitted desktop components onto Omarchy v4.5.0 stable at
  `ac2690cd7be4f47e4a255f5e2e78d904d436b068`, preserving reviewed Ubuntu
  controllers and exclusions. See [component scope and acceptance](omarchy-450-update.md).
- Disable automatic fullscreen HDR switching in the managed Hyprland settings
  to preserve fullscreen colors. Existing private profiles are not overwritten.
- Explain browser-owned versus floating-workspace titlebar controls during
  installation. Ordinary Chrome windows can use the manual **Use system title
  bar and borders** setting; Edge remains unresolved. No browser profile or
  shared GNOME/GTK setting is changed automatically. See
  [browser setup and limitations](installer.md#browser-window-controls).

Target remains Ubuntu 26.04 x86_64 with source-reviewed Hyprland 0.57.0 and
Qt 6.10.2. The release number does not establish full Omarchy parity, stock-
machine/first-login acceptance, all browser actions, PWA/PiP or a fresh GNOME
login. Public artifacts remain artwork-free; plugin preparation/activation and
local desktop deployment are separate approval gates.

### v0.2.1 release scope

Version **[0.2.1](https://github.com/harald-mue/omabuntu/releases/tag/v0.2.1)** is
published. Local and remote tags identify source commit
`26e9ca4dca0752569bbd17b7a717a1210445e85e`. Post-release documentation changes
do not replace that commit or its immutable artifacts. Signature, retained
artifact/GitHub asset-digest comparison, source-export identity, bundle integrity
and artwork-exclusion checks pass.

Changes since v0.2.0:

- Original-derived Menu Bar/Dock Appearance controls: visibility, bar
  Opaque/Glassy/Clear, clock presets, battery percentage and dock position/
  visibility policy. Preferences persist through guarded, backed-up atomic
  changes with exact conditional rollback. See [Appearance controls](appearance-controls.md).
- Correct translucent bar rendering by requesting an alpha-capable surface
  before creation; user-confirmed Opaque/Glassy/Clear behavior on the local
  desktop. Correct battery-percentage allocation so it does not overlap the
  next component, with contained layout regression checks.
- Original Update menu placement with **Update > Omabuntu**, an independent
  terminal and separately confirmed signed-metadata check, candidate download
  and application-only switch. Preserve wallpaper/preferences, block local
  adaptations and downgrades, and refuse missing prerequisites/migrations
  instead of installing system components. See [Application Update menu](application-update-menu.md).
- Recognize the publisher's `release-VERSION` bundle names during installed
  version comparison and incoming bundle validation, while retaining strict
  numeric signed metadata and local-adaptation refusal. Temporary transaction/
  recovery tests now exercise publisher-style bundle names.

The user confirmed local terminal invocation and pre-network cancellation.
A separately approved real metadata-only check verified the public v0.2.0
signature and correctly protected the private installed derivative. This does
not establish a real public-version update pair/self-restart or native failure
recovery. GNOME, fresh-machine, full focus/lifetime and generic security
acceptance remain separate. Publication does not automatically replace the
private installation or weaken its local-release protection.

No desktop double-click gesture is included; the proposal was rejected.
Target versions/pins remain unchanged. Public archives remain artwork-free;
no package/service/plugin activation, desktop deployment or system updater is
part of release publication. Existing tags/assets remain immutable.

### v0.2.2 release scope

Version **[0.2.2](https://github.com/harald-mue/omabuntu/releases/tag/v0.2.2)** is
published. Local and remote tags identify source commit
`bb5a20c63bcc4e9e2a295497aba60aa4aadb7043`. All four expected assets are public;
retained hashes/sizes match GitHub asset digests. Publisher signature, source-
export/packaged-source identity, bundle integrity and artwork exclusion verify.
Documentation follow-up does not replace the published commit or artifacts.

Changes since v0.2.1:

- Replace exact native patch-version locks with a shared stable-family policy:
  Hyprland >=0.57.0,<0.58.0; Qt >=6.10.2,<6.11.0; Hyprlock >=0.9.6,<0.10.0.
  This admits current PPA 0.57.1/0.9.7 candidates to further checks rather than
  rejecting their version numbers. Numeric comparisons, minimums, upper bounds,
  explicit exclusions and malformed/prerelease/dirty-evidence refusal remain.
- Apply the policy consistently to package/source-build planning, application
  binary/Qt preflight, generic-session planning and lock-version preflight.
  Keep runtime linkage/QML-import/WebP checks, policy/approval drift detection,
  package add-only safety and existing native-transition contracts.
- Decouple compatible shell/session installation from optional hyprbars source
  approval. Offer explicit continuation without that integration when no
  reviewed plugin target exists; skip unnecessary compiler-package review and
  new plugin-login grants. Preserve existing plugins/grants and keep strict
  source/header/ABI/build/receipt and separate activation checks.
- Explain detected installed/candidate/binary version, supported range, reason
  and next step. Preflight errors identify failed checks, library/symbol,
  QML/codec and timeout categories as well as private report paths.
- Package the shared compatibility helper in both ordinary helper and standalone
  updater payloads. See [native compatibility](native-compatibility.md).

The fresh candidate fixture reproduces the old refusal and passes with the new
policy. All 1158 unit tests and clean-source checks pass, and a contained review
bundle's helper/updater imports and manifest verify. The published isolated build
and artifact checks do not establish native fresh-VM installation, plugin
activation, verified unlock/recovery, GNOME/login or actual update-pair acceptance.
The exact legacy native
handoff is not generalized. Unknown plugin targets remain explicitly deferred;
family admission is not proof of every future patch's behavior or plugin ABI.

Public artifacts remain artwork-free. Publication does not install the release,
change native packages, activate plugins/locking, replace private profiles or
modify previous immutable tags/assets.

### v0.2.3 release preparation

Version **0.2.3 is being prepared**, not yet published. v0.2.2 remains latest
until the interactive publisher completes and public assets are verified.

Changes since v0.2.2:

- Make logout/reboot/shutdown available without hidden application grants on
  fresh installs and after updates, ignoring obsolete ordinary-action flags
  without rewriting user preferences. Ubuntu authorization/inhibitors and
  separate suspend/hibernate safety grants remain unchanged.
- Resolve logout against the current owned Hyprland session. Validate an exact
  UWSM compositor service's MainPID before stopping it, or use the current
  direct compositor's dispatcher. Refuse GNOME/TTY/stale/ambiguous contexts;
  no wildcard service stop, broad user termination or forced window closing.
- Retain wallpaper command/stderr errors and show them in the existing background
  and theme picker. Check active image targets after daemon acceptance; no legacy
  preload fallback for connection/handshake/file errors. Preserve recorded choices
  and add bounded transient readiness retry only to login restoration.
- List downloaded theme stills even before the first theme is selected. Add
  read-only `omabuntu wallpaper-status` with bounded daemon/session/IPC/journal
  diagnostics, no daemon start and no state-directory/control-lock creation.
- Keep the application-only update path free of wallpaper restoration or native
  package/service changes. See [command actions](command-menu.md) and
  [wallpaper behavior and diagnostics](image-picker.md).

All 1185 unit tests, clean-source, contained picker/menu and private bundle
integrity checks pass. These are source/fixture checks, not native logout or
VM rendering acceptance. The guest's selectable-but-black wallpaper is not
proven fixed; a correct active-target report cannot establish rendered pixels.
No guest graphics, daemon activation, authentication, plugin activation or local
installation change is part of publication. Public artifacts remain artwork-free.

The user also requested retiring old GitHub releases. Exact version/tag scope,
private backups and destructive-action confirmation remain separate from this
publication; no old public release/tag has been removed by preparation.

## One-time publisher setup

Use an existing, dedicated Ed25519 SSH signing key stored outside the repository.
Do not put its private key or passphrase in Git, environment values, logs or CLI
arguments. `OMABUNTU_RELEASE_SIGNING_KEY` contains only its filesystem path.
No tool here generates keys or changes SSH/Git configuration.

1. Review the key and its recovery/storage policy privately.
2. Put only the public key in `config/release-signing-key.pub` and review/stage it.
   The configured Ed25519 public-key fingerprint is
   `SHA256:qpDxJf0c/vbS55vfhMkLIcY+2vgonerMB8i8VT1ZJC4`.
   Verify it independently before trusting downloads. Private key material is
   never included in the repository or release archive.
3. Export the private key path in your own terminal:

   ```sh
   export OMABUNTU_RELEASE_SIGNING_KEY=/path/to/private/publisher-key
   ```

4. Ensure Git, GitHub CLI (`gh`), and OpenSSH (`ssh-keygen` with SSH signing
   support) are available. Authenticate `gh` yourself with release-write access
   to `harald-mue/omabuntu`. No credentials belong in the repository.
5. Have the documented Ubuntu 26.04 x86_64 build dependencies installed. The
   release command does not install them or grant privileged access.

## Publish

```sh
make release VERSION=0.1.1
```

Use numeric `major.minor.patch` versions. Existing tags and local publication
workspaces are refused, never overwritten. Run from `main` with the expected
origin and no conflicts. The command fetches upstream metadata, requires the
local history to include origin/main, and shows changed files. It refuses any
untracked non-ignored files: stage intended new files yourself after review.
Ignored files are not automatically included. Review staged files for secrets;
.gitignore and tests are not a publication or license audit.

After explicit commit confirmation it runs tests, checks whitespace, and commits
tracked changes with an English Conventional Commit. Hooks are not skipped.
A clean tree reuses HEAD. It exports exactly that commit into an isolated private
workspace, builds the runtime and screenshot components without theme artwork,
records the hyprpm policy without compiling/loading its plugin, and verifies
the bundle. This can take significantly longer than a cached development build.
GNOME, user preferences, desktop processes, services and selectors are unchanged.

Artifacts under `work/publish/vVERSION/`:

- `omabuntu-VERSION-ubuntu-26.04-x86_64.tar.gz`: tracked source/installer plus
  the checked bundle, not caches or build logs;
- `release.json`: source commit, target, archive size and digest;
- `SHA256SUMS`: archive and metadata checksums;
- `SHA256SUMS.sig`: SSH signature in the `omabuntu-release` namespace.

Interactive publisher-key and signing prompts have no timeout: entering a
passphrase is not a timed probe. Network, build and signature-verification
commands retain their bounded execution limits.

After separate publication confirmation the tool creates an annotated tag and
atomically pushes main and the tag. It uploads artifacts into a draft GitHub
Release, then makes it public. There is no force push, tag replacement, package
installation or desktop deployment.

Failures stop immediately. Local commits, build workspaces, tags or GitHub drafts
may remain, depending on the failed step. Inspect them manually; do not blindly
retry with another version, delete evidence or overwrite a published release.
No automated destructive cleanup or unpublish/rewrite is provided. Only complete
non-prerelease GitHub Releases are selected by the downloader.

### Start over after a failed build or signing attempt

A complete fresh build is supported. Before retrying the same version, verify
that no corresponding tag or GitHub Release was created and no release process
is still running. Move the existing workspace out of `work/publish/vVERSION/`
into a uniquely named private backup directory under `work/`; do not delete it
or overwrite a published version. Commit any reviewed source fixes, then run
`make release VERSION=...` again. The archive will be built from the new commit.
A fresh build is independent of the archived artifacts and may take several
minutes. Existing tags or remote releases require separate manual review.

### Optional: resume after a signing interruption

If you prefer not to rebuild and packaging finished but signing stopped, keep the workspace:

```sh
make release-resume VERSION=0.1.1
```

This is an explicit pre-publication recovery path, not a fresh build. Review and
commit any pending fixes first; a clean main checkout is required. The recorded
artifact commit must be HEAD or its ancestor. The tool verifies the metadata,
archive checksums, original Git export, packaged source, bundle integrity and
absence of theme artwork. It does not rebuild, commit or include later source
changes in the existing archive. The tag identifies the original artifact commit;
main may also include newer committed fixes, which are displayed before approval.

After confirmation it signs in a fresh retained attempt directory, verifies the
signature/archive and asks separately before pushing and publishing. Interactive
signing does not expire. An existing valid signature can be reused; an invalid
signature or incomplete workspace requires manual review, not overwrite/deletion.
Changed HEAD/artifacts or an existing tag are refused. Failures after tag creation,
push or GitHub draft creation are outside this resume path.

Extraction retains the bundle's reviewed regular-file permissions after the safe
Tar data filter so that read-only manifest files remain read-only. Links cannot
be used as archive parent paths; privileged modes and unsafe paths remain refused.

## Install and update without Git

```sh
curl -fsSLo install.sh https://raw.githubusercontent.com/harald-mue/omabuntu/main/install.sh
bash install.sh
```

Alternatively `curl -fsSL URL | bash` is supported. Prompts read `/dev/tty`;
there is no unattended approval. Never pipe to `sudo bash`.

The bootstrap requires Python 3, curl, OpenSSH, Ubuntu 26.04 and x86_64. It
fetches the latest published GitHub Release, verifies the SSH signature before
trusting checksums, verifies the downloaded archive and metadata, and safely
extracts it with path/type/size restrictions. Downloads have time and size limits.
Native/runtime checks in the existing installer remain mandatory: Ubuntu and CPU
alone do not prove compatibility with the installed Hyprland/Qt stack. New bundles
use separately reviewed [hyprpm stages](plugin-management.md); the source policy
is not permission to activate a plugin or accept an unreviewed compositor version.

System prerequisite plans and application deployment retain their own confirmation
and refusal rules. No blanket upgrades, source builds, automatic login, plugin
loading, locking, logout or reboot occurs. Legacy installed state may require a
separate explicit review; the bootstrap never silently enables legacy adoption.
The original private Hyprland profile is not merged or replaced. Fresh generic
session/login setup still uses the separate steps in [installer.md](installer.md)
from the retained source directory printed after download.

Verified installer source, bundle and private prerequisite reports are retained
under `$XDG_CACHE_HOME/omabuntu/published/` (default `~/.cache`). Do not publish
that cache. Installed releases and rollback journals stay in their normal XDG
locations; deleting a cache is not an uninstall.

Repeat the command to update. For the exact 0.56.2 to 0.57.0 application pair,
the installer offers a separate [native application handoff](installer.md#explicit-application-handoff-after-a-native-upgrade).
It requires an already upgraded matching session and verified manager build; it
is not a compositor/profile migration or general target bypass. Existing
next-login loaders require their own handoff. Healthy enabled manager plugins
are preserved without a duplicate build/load. Later same-target updates need no
native-transition flag. Real VM/update/login acceptance remains separate.
From a checkout `make update` takes the same public release path. `make build` and `make guide` remain the source-development path.
Published versions are selected through GitHub Releases; development versions
are built from the checkout.

## Trust model

SHA-256 alone is integrity, not publisher authentication. Archives require an
SSH signature matching the configured public key. The initial shell/Python
bootstrap and key are obtained over GitHub HTTPS: compromising the repository
or that initial download can replace both code and key. This is not independent
out-of-band trust, and a moving main URL is not immutable.

For a reviewed immutable bootstrap, use the full reviewed Git commit in the raw
script URL and set the matching ref, for example:

```sh
curl -fsSLo install.sh https://raw.githubusercontent.com/harald-mue/omabuntu/COMMIT/install.sh
OMABUNTU_BOOTSTRAP_REF=COMMIT bash install.sh
```

Verify the publisher key fingerprint through an independent trusted channel.
Key rotation requires an explicit reviewed bootstrap/key update, not trusting a
key supplied by the downloaded archive. Only the public key belongs in Git.

Theme backgrounds remain excluded; source licenses, bundled fonts and third-party
notices must still be reviewed before the first publication. No green test or
signature proves stock-machine functionality or security acceptance.
