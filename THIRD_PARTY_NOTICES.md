# Third-party notices

## Desktop Nerd Font

The optional desktop face is JetBrainsMono Nerd Font Regular from
`ryanoasis/nerd-fonts` v3.4.0, commit
`fa7b859994228a9c8759f99c55a8d31ee92a1b5e`, originating from JetBrains Mono
2.304. Its folder explicitly supplies SIL OFL 1.1. Preserve both the folder
notice (`licenses/Desktop-JetBrainsMonoNerd-OFL.txt`, copyright JetBrains Mono
Project Authors) and the upstream licensing overview
(`licenses/Desktop-Nerd-Fonts-LICENSE.txt`, including Ryan L McIntyre's notice).
No font patching or renaming is performed. The TTF is downloaded from the
pinned URL, not committed. Source and byte identity are recorded separately.

## Omasnap screenshot executable

The optional release-local `runtime/bin/omasnap` is built from
`omacom/omasnap` commit `a432f40b14598a4a02b89fa0054f9a0ba3662dd4`
(version 1.24.0), copyright Tobi Lütke, MIT. Source/archive identity and
annotation font hashes are recorded in `upstream/omasnap-source.json`.
`tools/build_omasnap.py` verifies the source MIT, bundled Neucha/JetBrains
Mono/Inter font OFL notices, Lucide ISC notice and fonts provenance note
against the preserved `licenses/Omasnap-*` records before compiling.
These notices accompany the local executable under `licenses/omasnap/`.
No Omasnap source tree, font binaries or compiled executable is committed.
System Qt and LayerShellQt remain Ubuntu dependencies, not copied from a
private home directory. This build path does not authorize public binary
publication or run an Omarchy installer.

## Weather panel

`vendor/omarchy/shell/plugins/panels/weather/` originates from Omarchy commit
`03ff1eff3812933f7088484533784d2f63eaf19a`. The manifest names Omarchy as
author; the reviewed QML/JavaScript files carry no separate third-party notice.
The root MIT notice is preserved in `licenses/Omarchy-MIT.txt` and
`vendor/omarchy/LICENSE`. `tools/weather_frontend.py` derives the original panel
and bar widget with the original location editor and a bounded Python backend
for wttr.in weather/IP location and Open-Meteo forecasts/city search.
No images, fonts, or weather datasets are bundled with this port.

Current reports and IP-based city lookup also use [wttr.in](https://wttr.in/).
No wttr.in dataset or source code is bundled. The provider sees the requesting
network's public IP; manual city searches are sent to Open-Meteo.

Forecast weather data is provided by [Open-Meteo](https://open-meteo.com/), under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Values and condition
codes are rendered by the original model as rounded temperatures and icons.


Omabuntu's [MIT License](LICENSE) covers its original work, not every dependency
or local asset. Preserve each third-party copyright and license notice. This
inventory distinguishes source included in the public candidate from external
software and optional local material; it is not a blanket redistribution grant.

## Source included in this repository

### Selected Omarchy components and adaptations

- Upstream: https://github.com/omacom/omarchy
- Pinned commit: `03ff1eff3812933f7088484533784d2f63eaf19a`
- Copyright: David Heinemeier Hansson; retain any additional file-level notices.
- License: MIT; complete notices are in [vendor/omarchy/LICENSE](vendor/omarchy/LICENSE)
  and [licenses/Omarchy-MIT.txt](licenses/Omarchy-MIT.txt).
- Included scope: selected QML/JavaScript components and a workspace-toggle
  reference, not the complete upstream shell or installer.
- Unchanged files: inventory in [vendor/omarchy/README.md](vendor/omarchy/README.md).
- Adaptations: deterministic derivation tools and their generated/staged mirrors;
  per-file source URLs, hashes and transformations are recorded in
  [upstream/clock-preview.json](upstream/clock-preview.json),
  [widget-candidates.json](upstream/widget-candidates.json) and related profiles.
- Recorded palette data: [config/menu/themes.json](config/menu/themes.json)
  includes its pinned source-file provenance.
- The extracted Omarchy mark is recorded in
  [upstream/omarchy-mark.json](upstream/omarchy-mark.json); the original font
  binary and its other marks are not included. Copyright licensing does not
  imply endorsement or grant unrestricted trademark rights.

Do not extend root-license assumptions to unrelated images, fonts, datasets or
components. Unimported components discussed in historical audits are not claimed
as licensed imports by this inventory.

### Elsewhen world clock

- Included path: [vendor/omarchy/shell/plugins/panels/elsewhen](vendor/omarchy/shell/plugins/panels/elsewhen).
- Upstream: https://github.com/omacom/omarchy at pinned commit `03ff1eff3812933f7088484533784d2f63eaf19a`.
- Author: Jason Fried. Component manifest: `manifest.json` (Elsewhen 1.1.0, MIT).
- License: MIT. The Omarchy root notice in [licenses/Omarchy-MIT.txt](licenses/Omarchy-MIT.txt) also covers this tree. This component notice does not extend to branded agent SVGs or the separate notification service.
- The staged panel keeps the original layout and drops Open-Meteo requests, GitHub profile requests, notification delivery and system timezone changes. `world.json` and `cities.json` are data for the drawn globe, not image assets.

### Project Nayuki QR Code generator

- Included file: [tools/qrcodegen.py](tools/qrcodegen.py).
- Upstream: https://github.com/nayuki/QR-Code-generator
- Author's documentation: https://www.nayuki.io/page/qr-code-generator-library
- Copyright: Project Nayuki.
- License: MIT; the complete applicable copyright, permission and disclaimer
  notice is retained at the top of the included file and must remain in copies.
- The exact upstream revision for this existing import is not recorded. This
  notice does not invent a pin; reconcile its bytes to upstream before claiming
  complete per-file revision provenance or publishing a binary release.

## Runtime sources fetched only for an explicitly approved local build

These source trees and compiled outputs are not part of the public source
candidate. [upstream/source-lock.json](upstream/source-lock.json) records exact
archive URLs, sizes, checksums and revisions. Local bundles include the collected
runtime license texts; source-distribution obligations still require review.

| Component | Source / revision | License evidence |
| --- | --- | --- |
| Quickshell | [quickshell-mirror/quickshell](https://github.com/quickshell-mirror/quickshell), `2b4501a282689792b62e94f3fb30d8f512324fe6` | Lock records LGPL-3.0-only; packaging retains upstream `LICENSE` and `LICENSE-GPL`. Review actual file/component obligations rather than applying one label to all dependencies. |
| cpptrace | [jeremy-rifkin/cpptrace](https://github.com/jeremy-rifkin/cpptrace), `3db8da80111171c219ab5839905771386bee06b3` | MIT; packaging retains the upstream license text. |

See [runtime build](docs/runtime-build.md) and
[local packaging](tools/package_user.py). A private executable bundle is not
cleared for GitHub Releases merely because its source checksum is pinned.

## External desktop and build dependencies

The optional bootstrap hyprbars artifact uses hyprland-plugins commit
`7644cecdb947060682891a0db2a0cdc5c0b9e704` (Hypr Development, BSD-3-Clause),
compiled against Hyprland headers at `efb50993780079460b0cbed1363e2166a2de1d9f`
(vaxerski, BSD-3-Clause). Their root notices were reviewed in the exact source
checkouts before archive acquisition and are preserved as
`licenses/Hyprland-plugins-BSD-3-Clause.txt` and
`licenses/Hyprland-BSD-3-Clause.txt`. Locked archives and notice hashes live in
`upstream/hyprbars-build.json`. This does not authorize plugin activation or
publication of a release; other upstream plugins/assets are not packaged.

Qt, Hyprland, hyprpaper, Hyprlock, hyprland-plugins/hyprbars, font packages and
native desktop libraries are external dependencies, not relicensed by Omabuntu.
The public candidate does not include their installed binaries or font files.
Use the distributions' and upstream projects' actual notices and source/license
requirements when redistributing any of them. Dependency/build references are
in [packages/](packages/), [dependencies](docs/dependencies.md) and
[hyprbars](docs/hyprbars.md).

## Excluded local images

`config/menu/backgrounds/` and `config/menu/themes-previews/` are ignored and kept
local. Their upstream per-image redistribution rights are not established;
[upstream/theme-backgrounds.json](upstream/theme-backgrounds.json) records origin
but is not an image license. They are not approved for public source or binary
publication. Local bundle preparation may include them when present, so inspect
bundle contents separately from the Git candidate.

The installer WebP codec probe is an authored 16x16 gradient lossless image
embedded in `tools/install.py`, not an imported wallpaper.

## Remaining publication review

Keep this inventory, the source locks and original file notices together.
A notice does not replace missing license evidence or a required corresponding
source offer. The [publication checklist](docs/publication.md), privacy/history
review, unresolved provenance and explicit hosting/publication approval remain
separate gates.
