# Omabuntu

```text
   █▀█ █▀▄▀█ ▄▀█ █▄▄ █░█ █▄░█ ▀█▀ █░█
   █▄█ █░▀░█ █▀█ █▄█ █▄█ █░▀█ ░█░ █▄█

          Your Ubuntu. Reimagined.
```

An Ubuntu-native Hyprland desktop integration: the Omarchy bar, menus and
selected panels, adapted for Ubuntu. It keeps Ubuntu, GNOME and your personal
configuration — install and update it without building anything yourself.

> **Omabuntu is not a replacement for [Omarchy](https://omarchy.org/).**
> Omarchy offers the broader feature set and is the better choice when you can
> choose your distribution. Omabuntu exists for people who must use Ubuntu LTS,
> particularly in corporate environments, and recreates selected Omarchy
> behavior within those constraints. It does not match every feature and is not
> affiliated with or endorsed by the Omarchy project.

## Install

**Ubuntu 26.04 · x86_64.** Run this as your normal user, not with sudo:

```bash
curl -fsSL https://raw.githubusercontent.com/harald-mue/omabuntu/main/install.sh | bash
```

The latest release is **[v0.1.9](https://github.com/harald-mue/omabuntu/releases)**;
the next release will be v0.2.0. fresh-machine installation is not yet
accepted. The installer downloads it, verifies the publisher signature and
archive checksums before extraction, and asks before installing missing
prerequisites or switching the application. Updates ask separately before
restarting a running bar.

You need `curl`, Python 3 and `ssh-keygen` (OpenSSH client) for the bootstrap.
The installer checks native compatibility of the required Hyprland and Qt
packages and refuses incompatible versions instead of upgrading your system
silently.

### Your desktop stays yours

- Your personal `hyprland.lua` is never replaced or merged automatically.
- Package changes require approval; there are no blanket upgrades, automatic
  logouts or reboots.
- GNOME remains fully available. Omabuntu's services and settings never affect
  a GNOME session: its units start only under Hyprland, and no global GNOME
  setting is changed.

Installing the application does not finish a new Hyprland session setup.
Generic session configuration, plugin loading at next login and login
autostart are separate opt-in steps. The installer prints the retained
directory and the next step after download; details are in the
[session setup guide](docs/installer.md#session-and-next-login). An existing
personal profile is deliberately left alone — that is not an install failure.

### Inspect the script first

```bash
curl -fsSLo omabuntu-install.sh \
  https://raw.githubusercontent.com/harald-mue/omabuntu/main/install.sh
# Read omabuntu-install.sh, then:
bash omabuntu-install.sh
```

The bootstrap trusts GitHub HTTPS; release archives additionally require the
publisher signature. For the trust model and key fingerprint, see
[release verification](docs/releases.md#trust-model).

## Update

Run the same command again:

```bash
curl -fsSL https://raw.githubusercontent.com/harald-mue/omabuntu/main/install.sh | bash
```

It downloads the latest published release and asks before switching. No Git
checkout or `git pull` is needed; your preferences and private configuration
stay, and the previous release remains installed for rollback.

Rollback and recovery of interrupted updates are documented in the
[installation guide](docs/installer.md#release-install-and-update). Rolling back
the application does not undo APT package changes.

## What you get

- The Quickshell bar with application launcher, command menu, calendar and
  desktop panels.
- Per-workspace tiling, scrolling and floating, with layout persistence.
- Floating-workspace titlebars (close, maximize, minimize) through hyprbars,
  loaded automatically at login once granted.
- Versioned installation, signature-verified updates and rollback.

Titlebars come from separately approved hyprpm preparation rather than a
bundled plugin library; see [plugin management](docs/plugin-management.md).
Theme background images are excluded from public releases because their
redistribution rights are not cleared. Third-party code and fonts keep their
own license notices.

**Target: Hyprland 0.57.0 and Qt 6.10.2 on Ubuntu 26.04.** This is an
integration of selected original components — not the unmodified Omarchy shell
and not an Arch installer. Tests passing does not by itself establish
functional or security acceptance on your hardware.

## For developers

Most users only need the installation command above. A checkout is for local
development and release publication:

```bash
git clone https://github.com/harald-mue/omabuntu.git
cd omabuntu
make help
make build                    # prepare a local development bundle
make guide                    # review local installation stages
make test                     # unit suite
```

Maintainers publish a signed release after setting up the publisher key and
GitHub access:

```bash
make release VERSION=0.1.10
```

This asks before committing, builds the committed source without theme
artwork, creates checksums and a signature, and asks again before pushing and
publishing. It never installs or restarts a desktop. See
[publishing releases](docs/releases.md) for prerequisites and recovery.

Further reading: [runtime builds](docs/runtime-build.md),
[dependencies](docs/dependencies.md), [testing](docs/testing.md) and
[clean-source verification](docs/clean-source.md). Keep private configuration,
keys, diagnostics, backups and build outputs out of Git — `work/` is private
working material, not release content.

## Documentation

- [Installer and session setup](docs/installer.md)
- [Releases, signing and verification](docs/releases.md)
- [Plugin management](docs/plugin-management.md) and [titlebars](docs/hyprbars.md)
- [Capabilities](docs/capability-matrix.md) and [compatibility](docs/compatibility.md)
- [Architecture](docs/architecture.md) and [workspace modes](docs/workspace-modes.md)
- [Upstream provenance](upstream/README.md) and [third-party notices](THIRD_PARTY_NOTICES.md)

Original Omabuntu code and documentation use the [MIT License](LICENSE).
Third-party components retain their own notices and licenses.
