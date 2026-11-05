# Upstream provenance policy

Selected unchanged sources under [vendor/omarchy/](../vendor/omarchy/README.md)
now target Omarchy **v4.5.0 stable**, commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. These include original shared UI,
clock/calendar, tray, network, weather, desktop-panel and dock parents/models,
plus narrow source-derived bar/frame/tooltip surfaces. Full MIT notice and
per-file provenance are in [widget-candidates.json](widget-candidates.json),
[spacer-candidate.json](spacer-candidate.json) and [clock-preview.json](clock-preview.json).
The sealed clock label remains read-only; live component derivations retain
reviewed Ubuntu backend boundaries. The workspace-toggle script is reference
source only, never staged or executed. The full upstream shell/service registry,
helpers and native Arch binaries are not activated or staged. Independently
reviewed artwork/assets have separate provenance and are not silently repinned.
See the [stable update report](../docs/omarchy-450-update.md). The [source lock](source-lock.json)
records verified build-source download metadata. Other downloaded source, build
outputs, staged binaries, and logs remain private under ignored work/. They are not automatically licensed under the project's MIT
License; upstream licenses and source obligations still apply.

[Quickshell packaging research](quickshell-packaging.json) records the original
recipe matched to the captured buildinfo hash and its pinned patch/hook hashes.
It is research metadata, not a build input or authorization to apply the patch.
See the [shell audit](../docs/shell-audit.md) for its Qt-version-specific meaning,
original-shell provenance gaps, and unsafe startup/helper boundaries.

[Original Omarchy source metadata](omarchy-source.json) pins the stable component
source commit; its explicitly labeled rc1 reference-package comparison is
historical evidence, not a claim that the separate reference package was updated. The complete upstream MIT
notice is retained in [licenses/Omarchy-MIT.txt](../licenses/Omarchy-MIT.txt).
This is not blanket clearance for assets, datasets, derived components or
supplemental helpers. See the [source/gate evidence](../docs/shell-gate.md) for
remaining notice, package-recipe, runtime and startup-integration gates. The
[widget review](../docs/widget-candidates.md) records the blocked UI closures,
first original pure-code import, and contained Qt mathematical checks. The
[passive spacer profile](../docs/passive-spacer.md) separately records the sealed,
authored compatibility namespace and original Item geometry diagnostics; it is
not stock Style behavior or production catalog admission. The
[clock preview](../docs/clock-preview.md) records the derived read-only label
and private software image; it does not start a host Wayland session.

Before importing each component, record:

1. Original project and canonical source URL.
2. Exact tag/commit, or a clearly described packaged-file origin.
3. File paths and content hashes.
4. Applicable license and required notices.
5. Local modifications and rationale.
6. Redistributability of bundled fonts, images, icons, and other assets.

A private installed-file snapshot is useful evidence, but does not by itself
establish redistribution rights or a reproducible upstream revision.
Do not copy private configuration, credentials, absolute home links, service
activation links, or native Arch binaries.

Reference projects:

- https://github.com/omacom/omarchy
- https://github.com/quickshell-mirror/quickshell
- https://github.com/hyprwm/Hyprland

This project is independent; no affiliation or upstream endorsement is claimed.
