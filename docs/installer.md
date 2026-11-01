# Omabuntu installer

This is the current operator guide for `./install.sh` on Ubuntu 26.04 x86_64.
It describes the implemented stages. It is not a claim that a stock machine has
been installed, that a native login passed, or that a release has been published.

Run every command as your normal user, from the repository directory. Do not
prefix `./install.sh` with `sudo`. Package steps ask for `sudo` only inside
your interactive terminal.

## What it is

`./install.sh` is a staged installer and updater. The default command shows the
live guide and changes nothing. Each later stage is reviewed first. `--apply`
performs only the stage you named, after confirmation or an exact `--approve`
digest.

Ordinary installer confirmations show `[Y/n]`: press Enter to accept, or type
`n`/`no` to decline. Missing input (EOF) and unrecognized answers decline rather
than grant permission. This is not an unattended `--yes` mode: every independent
package, deployment, restart, plugin-load or login approval is still requested.
Exact typed migration/recovery phrases and explicit opt-in flags remain required;
sudo/APT/hyprpm and release-publication prompts keep their own behavior.

The installer keeps these domains separate:

| Domain | What an update may change | What it does not change |
|---|---|---|
| Application release | The selected immutable Omabuntu bundle and its launcher | User settings, weather city, themes, dock pins |
| APT/PPA | Only a reviewed additive package transaction | Installed-package upgrades, removals, unrelated packages |
| Hyprland profile | An owned generic module, or an untouched managed snippet when explicitly adopted | Private monitor rules and other user lines |
| Artwork | A private cache of pinned downloads | Publication or a claim that every image may be redistributed |
| Public release | Signed GitHub archive, downloaded with explicit install approval | A development checkout or automatic desktop activation |

A checksum proves that bytes match a pin. It is not a publisher signature.
Application rollback does not undo APT changes.

### Explicit application handoff after a native upgrade

Normal updates still refuse a different native target. One separate approval
exists for an application built for Ubuntu 26.04 / Hyprland 0.56.2 / Qt 6.10.2
to a manager-policy application targeting Hyprland 0.57.0 with the same Ubuntu,
Qt and state schema. It does not upgrade or restart the compositor. The clean
matching 0.57.0 compositor must already be installed/running and the exact
receipted plugin build, headers and enable/load state must be verified.

Review the application handoff without changing anything:

```sh
./install.sh --update --bundle /absolute/path/to/new-bundle --migrate-native --restart-bar --plain
```

`--restart-bar` describes the separately approved bar stop/start in this plan;
without `--apply` nothing is stopped. After review, add `--apply` to request
interactive deployment approval. The transition stages/preflights the complete
candidate, backs up selectors/launcher and journals its prestate, then rechecks
native, manager and private-profile fingerprints before stopping the recorded
bar. The restart intentionally does not restore/write wallpaper configuration.
No packages, native plugins, private profile, session, service or login grant is
changed. Arbitrary Lua includes are not evaluated or adopted; profile hashes
prove preservation/drift only, not next-login or visual acceptance.

An existing owned session must already match the reviewed renderer. Existing
next-login activation (including an old bundled-plugin loader) requires its own
configuration handoff and is refused here. Unversioned state, other native
pairs, Qt/Ubuntu changes and schema conversion cannot use this flag.

After a successful handoff, omit `--migrate-native`: normal same-target updates
and rollback work through the existing transaction path. Rollback to the old
0.56.2 target is still refused. A startup failure restores the recorded previous
application/bar only, not packages, compositor, plugin state or user edits. An
interrupted handoff uses `--recover-update` review, never a blind retry. The
published installer offers this exact pair separately; an already valid active
manager build is preserved rather than needlessly rebuilt or enabled again.

## Guide

```sh
./install.sh
./install.sh --plain
./install.sh --check
./install.sh --json
```

The default command shows the next stage. It does not install packages or start
Hyprland. `--check` and `--json` keep the older readiness report and still
report that a complete stock install is not accepted. `--plain` disables color.
`NO_COLOR` and dumb terminals also disable color; narrow or limited terminals
use a compact or ASCII banner.

Long builds print a still-running line every 15 seconds. Compiler output stays
in `work/*/logs`.

## Stage order

The guide order is host, PPA, packages, font, build, release, session,
activation, then a manual login. A blocked stage is not skipped by installing
the next one. An already configured Hyprland PPA is not duplicated.

### PPA

```sh
./install.sh --ppa
./install.sh --ppa --apply
```

This prepares the signed `cppiber/hyprland` source and key. Apply writes only
the managed deb822 and keyring paths, then refreshes APT metadata. It does not
install packages. If the PPA is already configured under another filename, the
guide leaves that file alone.

### Packages

```sh
./install.sh --packages
./install.sh --packages --base-only
./install.sh --package-closure
```

Review shows the exact additions. The current policy adds missing packages only.
It refuses removals and upgrades of installed packages, including Hyprland, Qt,
and Hyprlock. `--apply` must be run in your own terminal because `sudo` asks
for the password there. Package scripts may start services. The installer does
not request a desktop start.

On the development machine, the reviewed transaction that was installed was:

- `liblayershellqtinterface-dev`
- `liblayershellqtinterface6`
- `qml6-module-org-kde-layershell`

That install is not a fresh-VM dependency-closure verdict.

### Font

```sh
./install.sh --font
./install.sh --font --apply
```

This registers the pinned JetBrainsMono Nerd Font Regular face for the user.
It does not change GTK, terminal, or saved Omabuntu font preferences.

### Build

```sh
make build
./install.sh --build-release --apply --skip-artwork
```

`make build` prepares a local development bundle. The second command omits
artwork. Public `make release VERSION=0.1.0` is a separate reviewed commit/build/
publication workflow; see [releases.md](releases.md). Other commands are `make guide`,
`make packages`, `make font`, `make acceptance`, and `make rollback`.

Apply downloads pinned sources, artwork, and the font when they are missing,
then builds the runtime and Omasnap in isolated sandboxes. It packages a pinned
hyprpm policy rather than a native titlebar library. The result
is a private bundle under `work/user-releases/`. It is not installed, loaded, or
started. A compiled stage is reused only when it is the single verified match.

The development build `source-447226aa17e9898a` reached
`bundle-prepared-and-checked`. That does not install it.

### Release install and update

```sh
./install.sh --bundle work/user-releases/VERSION
./install.sh --bundle work/user-releases/VERSION --update --allow-legacy-state
./install.sh --rollback
./install.sh --recover-update
```

`--apply` switches the local application release. Add `--restart-bar` only when
you explicitly want the recorded bar stopped and started. Without it, a running
bar blocks the switch. An older installed release without an update contract
needs `--allow-legacy-state`. That acknowledgement does not migrate state.

Rollback restores the previous application release. It does not undo packages.
`--recover-update` restores one interrupted update to its recorded prestate and
does not resume the new release.

### Theme artwork on published releases

Public release archives ship **artwork-free**: the Omarchy stills/previews are
not cleared for redistribution, so a normal install alone would leave the
themes/backgrounds menus without the Omarchy images. The published installer
checks this itself and, after installation, offers **one** download of the
pinned upstream set into your private
`~/.local/share/omabuntu/artwork` (`XDG_DATA_HOME` respected). The menus,
theme previews, recorded stills and the next-login wallpaper record all fall
back to that private directory when the selected release ships none.

```sh
make artwork            # read-only completeness report
make artwork-apply      # download missing pinned files (one confirmation)
```

Downloads use only the pinned per-file URLs, sizes and blob hashes recorded in
`upstream/theme-backgrounds.json` (commit
`03ff1eff3812933f7088484533784d2f63eaf19a`), refuse redirects, never
overwrite existing conflicting files, and write a 0600 receipt. Declining or
failing changes nothing else; rerun the same `install.sh` to retry. The files
stay private user data: they are never bundled into a release, published, or
cleared for redistribution. A release that ships its own artwork is used
without any private download.

### Session and next login

```sh
./install.sh --session-config --keyboard-layout de
./install.sh --session-config --adopt-managed
./install.sh --session-activate
./install.sh --session-activate --enable-login
```

Session apply writes a generic profile only on a machine without its own
Hyprland configuration, and only when Hyprland is not running. An existing
personal `hyprland.lua` is kept. That is not an install failure. The application
release can still be updated. `--adopt-managed` replaces
only an untouched `omabuntu-managed` snippet. Extra lines, including private
monitor rules, block adoption.

Activation writes next-login titlebar/splash files and an optional wallpaper
record. Manager-mode activation does not load any library; hyprpm preparation
and live activation are separate [plugin-management stages](plugin-management.md).
Legacy bundled-plugin activation remains supported for old immutable releases.
File apply does not load the plugin, start hyprpaper, or
lock the screen. Login enablement is a separate flag and does not start the
service.

### Acceptance and rehearsal

```sh
./install.sh --acceptance
./install.sh --rehearse
./install.sh --state-schema
./install.sh --source-update
```

`--acceptance` is read-only and never marks a native login as accepted.
`--rehearse` runs install, failed start, update, rollback, session, and
activation in a temporary home. It does not change the host and is not VM
acceptance. `--state-schema` reports schema 1 and does not rewrite preferences.
`--source-update` fetches only already pinned archives into the private cache.

## Published releases

Use `make release VERSION=0.1.0` to prepare and publish a signed GitHub Release
after explicit commit and publication confirmations. Use `make update` to fetch
the latest published release, rather than building from the checkout.
The publisher public key is configured and v0.1.0 is published. Its fresh-VM
installation failed on runtime package scope and the newer Hyprland candidate;
new source changes are not retroactively applied to that immutable release.
See [release setup, trust and recovery](releases.md).

A checkout is the development path; GitHub Releases are the published path.

## Not done

- Source builds now use hyprpm, but existing v0.1.0 artifacts are unchanged.
- New builds target source-reviewed Hyprland 0.57.0; real manager/build/login
  acceptance remains outstanding. A source pin does not authorize a live action.
- The published installer offers plugin prerequisites separately, defers manager
  work outside a matching live session and offers an explicit plugin-login grant.
- No stock Ubuntu VM install, reinstall, update, or rollback has been accepted.
- Native first-login, plugin loading, and wallpaper appearance still need a real
  Hyprland login.
- A newer upstream source revision is not offered until it is reviewed and pinned.
- The development machine's private Hyprland profile has not been replaced.

Plan [043](../plans/043-fresh-install-and-updates.md) tracks the broader
fresh-install work. [User installation](user-installation.md) documents the
installed release manager.
