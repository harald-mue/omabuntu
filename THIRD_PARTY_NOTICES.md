# Third-party notices

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
