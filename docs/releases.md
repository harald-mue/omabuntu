# Publishing and installing GitHub Releases

## Status

The workflow is implemented but has not published anything or passed stock-VM
acceptance. The publisher public key is configured; private-key access and the
first real release remain manual gates. Do not advertise a working public
download until those gates are complete.
The project remains an Ubuntu-native integration, not an Omarchy provisioner.

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
make release VERSION=0.1.0
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
workspace, builds all native components there without theme artwork, and verifies
the bundle. This can take significantly longer than a cached development build.
GNOME, user preferences, desktop processes, services and selectors are unchanged.

Artifacts under `work/publish/vVERSION/`:

- `omabuntu-VERSION-ubuntu-26.04-x86_64.tar.gz`: tracked source/installer plus
  the checked bundle, not caches or build logs;
- `release.json`: source commit, target, archive size and digest;
- `SHA256SUMS`: archive and metadata checksums;
- `SHA256SUMS.sig`: SSH signature in the `omabuntu-release` namespace.

After separate publication confirmation the tool creates an annotated tag and
atomically pushes main and the tag. It uploads artifacts into a draft GitHub
Release, then makes it public. There is no force push, tag replacement, package
installation, channel promotion or desktop deployment.

Failures stop immediately. Local commits, build workspaces, tags or GitHub drafts
may remain, depending on the failed step. Inspect them manually; do not blindly
retry with another version, delete evidence or overwrite a published release.
No automated destructive cleanup or unpublish/rewrite is provided. Only complete
non-prerelease GitHub Releases are selected by the downloader.

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
Native ABI checks in the existing installer remain mandatory: Ubuntu and CPU
alone do not prove compatibility with the installed Hyprland/Qt stack.

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

Repeat the command to update. From a checkout `make update` takes the same public
release path. `make build` and `make guide` remain the source-development path.
No dev/stable channel is needed. Old local channel commands are deprecated
compatibility only; neither installation nor publication reads/writes those pins.

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
