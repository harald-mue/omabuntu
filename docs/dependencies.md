# Installed packages this desktop depends on

This is the record of what the running setup actually needs, split by purpose.
Everything comes from the already configured Ubuntu 26.04 archive and the
already configured Hyprland PPA (`cppiber/hyprland`); **no additional package
source was added**. Versions are the ones verified on this machine on
2026-10-25 (`hyprpaper` and `qt6-image-formats-plugins` on 2026-10-26).
Package rollback is a separate reviewed transaction: the Hyprland dependency
upgrade below changed a shared library that the running compositor is
linked against.

## 1. Compositor and session (pre-existing, unchanged)

| Package | Version |
|---|---|
| hyprland | 0.56.2-1ppa2~1resolute1 (commit `efb50993…`, abiHash `…_aq_0.15_hu_0.14_hg_0.5_hc_0.1_hlg_0.6`) |
| hyprland-data | 0.44.0-10ppa1 |
| hyprland-guiutils | 0.2.2-1ppa2~1resolute1 |
| uwsm | session management already in use |
| xdg-desktop-portal-hyprland | 1.4.1-1ppa1~1resolute1 |

## 2. Desktop services the panels talk to (pre-existing, preserved)

| Package | Version | Used by |
|---|---|---|
| network-manager | 1.54.3-2ubuntu3.1 | Network panel, `helpers/network_nm.py` |
| bluez | 5.85-4ubuntu0.4 | Bluetooth panel (native BlueZ objects) |
| pipewire / wireplumber | installed | Audio panel |
| upower | 1.91.1-1ppa1 | Power panel (battery, time, rate) |
| power-profiles-daemon | 0.30-2 | Power panel profiles (via Quickshell's native D-Bus interface) |
| libxkbcommon-tools | 1.13.1-1 | Keyboard-layout widget: `xkbcli list` provides the description-to-brief table ("German" -> "DE"); installed by the user on 2026-10-25 from the already configured `universe` archive. Read-only tool, no daemon |
| systemd (logind) | installed | Brightness through session `SetBrightness` |

## 2b. Wallpaper daemon (installed by the user on 2026-10-26)

| Package | Version | Used by |
|---|---|---|
| hyprpaper | 0.8.4-1ppa3~1resolute1 (from the already configured `cppiber/hyprland` PPA) | Background apply: `tools/background_backend.py` and `tools/theme_backend.py` set the chosen still through `hyprctl hyprpaper` |

hyprpaper decodes WebP natively (links `libwebp` through `libhyprgraphics`), so
the imported upstream stills work as wallpapers. Its 0.8.4 IPC replaced the
pre-0.8.4 `preload`/`unload` requests with a single per-output request
`hyprctl hyprpaper wallpaper <mon>,<path>[,<fit_mode>]`; the backend tries that
request first and only falls back to the legacy sequence when it is rejected.
The daemon is **not** autostarted, supervised or managed by this project: it is
started separately with an explicit session-lifetime approval. That approval
is not an implemented process supervisor or proof of logout cleanup; session
lifecycle enforcement still needs verification. Without a running daemon,
background selection is recorded with `applied: false` but no wallpaper is
painted. Shell release rollback does not undo system package installation.

Corporate VPN, certificates, keyring, proxy and firewall configuration remain
untouched and are not package dependencies of this project.

## 3. Desktop shell and fonts

- Quickshell is **not** an APT package here. It is built from the pinned source
  and shipped inside the Omabuntu release; its build dependencies are recorded in
  [Quickshell runtime investigation](../packages/quickshell.md) and were installed earlier
  (Qt 6.10.2 development packages, `libpipewire-0.3-dev`, `libpam0g-dev`,
  `libpolkit-agent-1-dev`, `libcli11-dev`, `libjemalloc-dev`, cpptrace with
  libunwind/libdwarf, `spirv-tools`, CMake/Ninja/GCC).
- `fonts-jetbrains-mono` / Nerd Font variant provides the bar and panel glyphs.
  Missing glyphs degrade the display only; they are not a security dependency.
- `qt6-image-formats-plugins` 6.10.2-1 (Ubuntu `resolute/universe`; installed
  by the user on 2026-10-26) adds the `libqwebp.so` image plugin to the system
  Qt. Without it `QImageReader` — and therefore the Quickshell `Image` in the
  background picker — cannot decode the imported WebP stills, so previews
  stay blank even though hyprpaper paints the wallpaper. The plugin links the
  system `libwebp`; no bundled codec is added. A running shell must be
  restarted before it rescans the image plugins.

These feature dependencies are separate from the source-build toolchain.
Do not install all development packages just to run a reviewed compatible
release. This record is not yet a complete, clean-target-validated runtime
manifest. See [installation prerequisites](user-installation.md#prerequisites-and-installer-scope)
for APT simulation and approval, and the [guided installer](guided-installer.md)
for the implemented bounded checks and remaining functional acceptance.
`packages/installer-runtime.json` is the feature prerequisite manifest used
by that installer; it excludes the source-build toolchain and does not
claim an exhaustive, clean-target-validated native library closure.

## 4. Screen lock

| Package | Version | Notes |
|---|---|---|
| hyprlock | 0.9.6-1ppa1~1resolute1 | Standalone substitute for the unadmitted original lock UI; explicit `omabuntu lock --apply` only |

`hyprlock` brings `/etc/pam.d/hyprlock`, which delegates to the existing `login`
stack. Its bytes match the pre-install state; no PAM file was edited and no
account or authentication policy was changed.

## 5. Floating-workspace titlebar (hyprbars plugin build)

Omarchy's ×/□/− buttons come from the Hyprland plugin `hyprbars`, which is not
packaged for Ubuntu here. It must be built against the installed headers. The
plugin's `pkg-config` set pulls in everything `hyprland.pc` declares.

Already installed for this build:

```text
libcairo2-dev libpango1.0-dev libhyprlang-dev libhyprutils-dev hyprwayland-scanner
```

That step also upgraded `libhyprutils13` 0.14.2 → 0.14.3 (same soname, patch
level). Hyprland is linked against that library; a compositor restart is the
clean way to settle it.

Still required to satisfy `pkg-config hyprland` (its `Requires:` names
`aquamarine`, `hyprcursor`, `hyprgraphics`, `xcb-*` development files), plus
`glslang-dev` because Hyprland's `ShaderLoader.hpp` includes it:

```sh
sudo apt-get --no-install-recommends install glslang-dev
```

(Simulated on this machine: 3 new packages, no upgrades, no removals.) Everything
else in that list is already installed.

### Header mismatch and the source checkout (important)

The PPA's `/usr/include/hyprland` headers do **not** match the running binary's
commit: they lack `desktop/view/window/Window.hpp`, which the pinned hyprbars
commit includes. Plugins must therefore build against the Hyprland **source tree
at the exact commit**, which is what `hyprpm` normally does.

`tools/build_hyprbars.py` is being extended to:

1. clone `hyprwm/Hyprland` at `efb50993780079460b0cbed1363e2166a2de1d9f` into
   `work/hyprland-headers/`,
2. generate the Wayland protocol headers it needs with `hyprwayland-scanner`
   (`wayland.xml` with `--wayland-enums`, `stable/`, `unstable/`, `staging/` and
   Hyprland's own `protocols/*.xml`) into the checkout's `protocols/` directory,
3. point a private `hyprland.pc` at that checkout (`-I<root>`,
   `-I<root>/hyprland/protocols`, `-I<root>/hyprland/src`),
4. build and install hyprbars out of tree.

No package source and no system header directory is modified by this; the
checkout and the generated `.pc` stay under ignored `work/`.

Nothing in that list installs a runtime daemon, a new package source or a
service. After it, `python3 tools/build_hyprbars.py` builds and verifies the
plugin; loading it still requires a reviewed config include and a Hyprland
reload, which are separate approvals.

## 6. What is deliberately absent

No pacman/yay/Arch package, no Omarchy installer, no Tailscale or NordVPN, no
third-party helper scripts, no additional APT source, and no package-managed
service that the project enables. `omarchy-*` helpers are never installed or put
on `PATH`; the bar's own helpers come from the verified Omabuntu release.

## 7. Reproducing the dependency state

```sh
dpkg-query -W -f='${binary:Package}\t${Version}\n' \
  hyprland hyprland-data hyprland-guiutils hyprlock hyprpaper hyprwayland-scanner \
  qt6-image-formats-plugins \
  libhyprlang-dev libhyprutils-dev libhyprutils13 libcairo2-dev libpango1.0-dev \
  network-manager bluez upower power-profiles-daemon libxkbcommon-tools
python3 tools/build_hyprbars.py    # prints the exact missing packages
```

APT simulation before any change (`--simulate`) is mandatory; a printed summary
with removals or unrelated upgrades must be rejected rather than confirmed.
