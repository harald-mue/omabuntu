# Omabuntu

```text
   █▀█ █▀▄▀█ ▄▀█ █▄▄ █░█ █▄░█ ▀█▀ █░█
   █▄█ █░▀░█ █▀█ █▄█ █▄█ █░▀█ ░█░ █▄█

          Your Ubuntu. Reimagined.
```

An Ubuntu-native Hyprland desktop integration with the Omarchy bar, menus and
selected panels, adapted for Ubuntu. Keep Ubuntu, GNOME and your personal
configuration — install and update Omabuntu without building it yourself.

## Prefer Omarchy if you can

> **Omabuntu is not a replacement for [Omarchy](https://omarchy.org/).**
> Omarchy offers a broader feature set and is the better choice for most users
> looking for the Omarchy experience. If you are free to choose your distribution,
> use Omarchy instead.
>
> Omabuntu exists primarily for people who are required to use Ubuntu LTS,
> particularly in corporate environments. It aims to recreate selected Omarchy
> behavior and workflows within those constraints — not to match every feature
> or replace the original project.

## Install

**Target: Ubuntu 26.04 · x86_64**

Open a terminal and run this as your normal user, **not with sudo**:

```bash
curl -fsSL https://raw.githubusercontent.com/harald-mue/omabuntu/main/install.sh | bash
```

**Status:** v0.1.0 is published, but **fresh-machine installation is not yet
accepted**. Its VM test exposed dependency and Hyprland-version blockers. Source
fixes do not change the existing release archive.
See [GitHub Releases](https://github.com/harald-mue/omabuntu/releases).

No Git checkout, Makefile or local compilation is needed. The installer:

1. Downloads the latest published release for Ubuntu 26.04 x86_64.
2. Checks the publisher signature and archive checksums before extraction.
3. Asks before installing missing prerequisites and switching the application.
4. Asks separately before restarting a running Omabuntu bar during an update.

You need `curl`, Python 3 and `ssh-keygen` (OpenSSH client) for the initial
bootstrap. Compatible Hyprland and Qt packages are also required; the installer
checks native compatibility and refuses incompatible versions rather than
silently upgrading your system.

### Your existing desktop stays yours

Your personal `hyprland.lua` is not replaced or merged automatically. Package
changes require approval; there are no blanket upgrades, automatic logouts or
reboots. GNOME remains available.

Installing the application does **not** finish a new Hyprland session setup.
Generic session configuration, plugin loading at next login and login autostart
are separate opt-in steps. Follow the [session setup guide](docs/installer.md#session-and-next-login)
using the retained installer directory printed after download. An existing
personal profile is deliberately left alone; that is not an application install
failure.

### Prefer to inspect the script first?

```bash
curl -fsSLo omabuntu-install.sh https://raw.githubusercontent.com/harald-mue/omabuntu/main/install.sh
# Read omabuntu-install.sh before running it.
bash omabuntu-install.sh
```

The initial bootstrap trusts GitHub HTTPS. Downloaded release archives additionally
require the publisher signature. For the trust model, public-key fingerprint and
immutable bootstrap pinning, see [release verification](docs/releases.md#trust-model).

## Update

**Run the same command again:**

```bash
curl -fsSL https://raw.githubusercontent.com/harald-mue/omabuntu/main/install.sh | bash
```

It downloads the latest **published GitHub Release** and asks before switching.
You do not need Git or `git pull`. Your preferences and private configuration are
kept, and the previous application release remains available for rollback.

For rollback and interrupted-update recovery, see the
[installation and recovery guide](docs/installer.md#release-install-and-update).
Application rollback does not undo APT package changes.

## What is included?

- Quickshell bar, application launcher, command menu, calendar and desktop panels.
- Per-workspace tiling, scrolling and floating state persistence.
- Versioned application installation, verified updates and rollback.
- Separately approved session and login integration.

New source builds delegate hyprbars to separately approved hyprpm preparation
and activation instead of shipping a compositor-specific plugin library. Existing
v0.1.0 artifacts are unchanged. See [plugin management and current limits](docs/plugin-management.md).

Public release builds exclude theme background images because their redistribution
rights are not cleared. Third-party code and fonts retain their license notices.

New builds target **Hyprland 0.57.0 and Qt 6.10.2 on Ubuntu 26.04**.
The 0.57 APIs are source-reviewed; clean-VM and native acceptance are still outstanding.
This is an integration of selected original components, not the unmodified full
Omarchy shell or an Arch installer. Stock-machine installation and native-login
acceptance are still in progress; successful tests do not establish functional
or security acceptance on your hardware.

## For developers and release maintainers

Most users should use the installation command above. A source checkout is for
local development and publication:

```bash
git clone https://github.com/harald-mue/omabuntu.git
cd omabuntu
make help
make build                    # prepare a local development bundle
make guide                    # review local installation stages
```

Maintainers can publish a versioned release after publisher-key and GitHub access
setup:

```bash
make release VERSION=0.1.1
```

This asks before committing changes, builds the committed source without theme
artwork, creates checksums and a signature, and asks again before pushing the
commit/tag and publishing on GitHub. It does not install or restart the desktop.
New files must be reviewed and staged explicitly. See
[publishing releases](docs/releases.md) for prerequisites and failure recovery.

Run `make test` for the unit suite. For detailed development work, see
[runtime builds](docs/runtime-build.md), [dependencies](docs/dependencies.md),
[testing](docs/testing.md) and [clean-source verification](docs/clean-source.md).
Keep private configuration, keys, diagnostics, backups and build outputs out of
Git; `work/` is private working material, not release content.

## Documentation and licensing

- [Installer and session setup](docs/installer.md)
- [Releases, signing and verification](docs/releases.md)
- [Capabilities](docs/capability-matrix.md), [compatibility](docs/compatibility.md)
  and [lock readiness](docs/lock-readiness.md)
- [Architecture](docs/architecture.md) and [workspace modes](docs/workspace-modes.md)
- [Upstream provenance](upstream/README.md) and [third-party notices](THIRD_PARTY_NOTICES.md)
- [Publication checklist](docs/publication.md)

Original Omabuntu code and documentation use the [MIT License](LICENSE).
Third-party components retain their own notices and licenses. No affiliation
with or endorsement by Omarchy or its authors is claimed.
