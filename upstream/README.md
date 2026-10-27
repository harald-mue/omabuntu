# Upstream provenance policy

Selected unchanged sources under [vendor/omarchy/](../vendor/omarchy/README.md)
are the pure clock model, the spacer/base pair, and the clock label plus its
button/glyph presentation, with full MIT notice and per-file provenance in
[widget-candidates.json](widget-candidates.json), [spacer-candidate.json](spacer-candidate.json),
and [clock-preview.json](clock-preview.json). The sealed clock label is a derived
read-only extraction. The live calendar is a separate derivation of the pinned
clock panel, not the unmodified IPC parent. No original bar, full shell, helpers,
fonts, assets or binaries are included. The [source lock](source-lock.json)
records verified build-source download metadata. Other downloaded source, build
outputs, staged binaries, and logs remain private under ignored work/. They are not automatically licensed under the project's MIT
License; upstream licenses and source obligations still apply.

[Quickshell packaging research](quickshell-packaging.json) records the original
recipe matched to the captured buildinfo hash and its pinned patch/hook hashes.
It is research metadata, not a build input or authorization to apply the patch.
See the [shell audit](../docs/shell-audit.md) for its Qt-version-specific meaning,
original-shell provenance gaps, and unsafe startup/helper boundaries.

[Original Omarchy source metadata](omarchy-source.json) pins the source commit
by matching all captured shell files to its Git tree. The complete upstream MIT
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
