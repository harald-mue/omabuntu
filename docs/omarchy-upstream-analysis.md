# Omarchy upstream gap analysis

Analysis date: 2026-11-05. This is source comparison and update planning, not
permission to import, deploy or execute upstream code. No source pins changed
during this analysis. **Subsequent decision: use v4.5.0 stable only**, not quattro.
Plan 078 and [the stable update report](omarchy-450-update.md) describe the
subsequent source rebase and its validation; the comparison/preflight results
below describe the pre-update baseline, not the current candidate.

## Result

Omabuntu can be brought closer to current Omarchy, but this is a component rebase,
not a Git merge or a version-string update. The comparison baseline was
v4.5.0-rc1. A newer stable release and a divergent development branch both exist.
The primary work is shared UI behavior, component dependency closure, and the
Ubuntu adapters; most upstream file changes are not desktop code we should port.

The already accepted `render.cm_auto_hdr = 0` is consistent with current upstream:
Omarchy commit `f766bfa510711e4c3f84a38190e65c65449d9338` disables automatic HDR
on fullscreen transitions. The setting appears in both target trees below.
Its documented motivation concerns washed-out SDR content on the Pro Display
XDR; that does not establish identical hardware or the same underlying defect
on the user's system. Preserve the tested Omabuntu default from plan 076.

## Immutable comparison points

| Role | Ref | Exact commit | Commits ahead of Omabuntu baseline |
|---|---|---|---:|
| Current Omabuntu provenance baseline | v4.5.0-rc1 | `03ff1eff3812933f7088484533784d2f63eaf19a` | 0 |
| Latest published stable release observed | v4.5.0 | `ac2690cd7be4f47e4a255f5e2e78d904d436b068` | 284 |
| Default branch observed | quattro | `6194f4606c585da8b839b87df9120b7d796afedf` | 410 |

The release API reports v4.5.0 published at 2026-11-05T05:36:53Z. The development
commit is dated 2026-11-05T05:02:13Z. Do not infer ancestry from timestamps:
GitHub reports the stable/development comparison as **diverged**, with 262 commits
unique to the development side and 136 unique to the release side. Their merge
base is `958254e92ab3dba59ebe3257cbbaffd3357be2d5`. This is not simply "stable
plus another 126 commits". The 410 and 284 counts include merges and changes
unrelated to Omabuntu; they are not outstanding feature counts.

Use exact SHAs for a later update. A mutable branch name or a newer release label
is not a reviewed source baseline. If current development behavior is the goal,
the candidate is the recorded quattro SHA, not an assumed superset of v4.5.0.

Sources:

- [Stable release](https://github.com/omacom/omarchy/releases/tag/v4.5.0)
- [Baseline to stable](https://github.com/omacom/omarchy/compare/03ff1eff3812933f7088484533784d2f63eaf19a...ac2690cd7be4f47e4a255f5e2e78d904d436b068)
- [Baseline to development](https://github.com/omacom/omarchy/compare/03ff1eff3812933f7088484533784d2f63eaf19a...6194f4606c585da8b839b87df9120b7d796afedf)
- [Upstream fullscreen color fix](https://github.com/omacom/omarchy/commit/f766bfa510711e4c3f84a38190e65c65449d9338)

## Coverage and size

All three recursive Git tree responses were non-truncated. Comparing blob paths
and hashes, including passive symlink blobs but without following links, found:

| Change scope from the baseline | Stable | Development |
|---|---:|---:|
| Added, removed or modified blob paths | 2475 | 2768 |
| Paths under manual/ | 1452 | 1600 |
| Paths under test/ | 433 | 457 |
| Paths under shell/ | 109 | 125 |
| shell/ paths excluding assets/ | 76 | 89 |
| Changed existing source parents mapped by Omabuntu's shell profile | 22 | 26 |

These are path changes, not rename-aware Git diff counts. Many manual and default
changes are translation content. The GitHub compare API returned at most 300
file records; those records alone were **not** used as a complete inventory.
The development comparison's full 410 commits were retrieved across five pages.
Stable commit subjects were sampled, not all individually audited.

`tools/check_clock_preview.py` maps 75 staged targets to 71 unique upstream source
parents. All 71 current vendor parents matched their baseline Git blobs. Thus the
starting vendor content is reproducible; the gap is not unexplained local vendor
drift. Hash comparison does not cover every transitive dependency of new code.

Selected changed shared components, panels, Lua defaults and package lists were
retrieved as review text and checked against the corresponding tree blob hashes.
They were not executed or imported into vendor/. Existing Python extraction
functions were exercised on selected candidate bytes without running QML, Lua,
helpers or external commands from those bytes.

## Findings mapped to Omabuntu

### 1. Shared frame, panels and motion: highest visual priority

Both targets change `Bar.qml`, `PopupCard.qml`, `KeyboardPanel.qml`, buttons,
slider behavior and tooltips. Upstream adds panel growth/closing behavior,
transitions between popout panels, immediate tooltip handoff, and widget drag-off
removal. `Style.qml` adds `easeOut`, and updated controls use it. Omabuntu's authored
`config/shell/preview/Style.qml` currently has `duration()` but not `easeOut`.

Updated `PopupCard.qml` calculates available geometry from painted bar thickness,
not the dimensions of the bar's now full-screen window. Taking that component
without its bar API/geometry changes can therefore break placement even when a
text extraction still succeeds. `PluginBarApi.qml` also adds popout-card tracking.

Update the original shared component/layout closure coherently, with narrowly
reviewed Ubuntu backend adaptations. Do not create another replacement panel.
Do not blindly adopt the full upstream root, registry, mutable layout writes or
service discovery just to obtain the visual changes. Test panel anchors, input
regions, outside clicks, reduced motion and mixed-output scaling together.
Widget drag removal requires separately designed persistence/rollback, not just
a copied animation.

### 2. Clock: small functional fix with a new dependency

Both target trees add `WallClock.qml` and use it instead of Quickshell's
`SystemClock` in the clock UI. The model adds `msUntilNextTick()`, calculated from
epoch time to avoid negative scheduling delays during the repeated DST hour.
Development history includes `48fcf5fe3a982338ef87477f2848e1fd825a8484`.
The bar clock also disables icon-like press shrinking.

Omabuntu's `ClockControlView.qml` and `CalendarPanel.qml` still instantiate
`SystemClock`. Merely replacing their parent source would leave `WallClock`
unmapped/unpackaged. Admit the new QML file and its model dependency explicitly;
test minute/second changes, DST boundaries, calendar rollover and popup anchoring.
Elsewhen's mapped source parents did not change directly, but shared Panel/UI
changes still affect its dependency closure.

### 3. Tray, tooltips, dock and workspaces

Updated tray code paints the foreground through symbolic icons' alpha rather
than retaining the source icon lightness, and rounds icon positions. This is a
useful correction for dark symbolic icons. Development tooltip changes address
output-scale readiness and monitor movement; workspace history fixes monitor
teardown reconciliation. These matter on multi-monitor Ubuntu systems too.

Dock motion now follows the shared easing/reduced-motion rules. Development
removes `ScreenMoveRemap.qml` and uses a new `PopupMenuRow.qml`; Omabuntu's dock
transform still expects the old remap block and menu structure. Rebase the dock
as a dependency closure, preserve its Ubuntu launch/actions and approved
session-lifetime behavior, and verify hotplug, focus grabs and context menus.
Do not introduce timed wrappers or unapproved crash supervision.

### 4. Display panel: largest functional rebase

Development changes the monitor model and substantially rewrites its panel:
one selected output, layout map, drag placement, refresh rate selection,
rotation, mirror/extend and persisted per-output settings. It also adds
`default/hypr/monitors.lua` and associated helper integration. Stable already
changes the older display panel, but not with the same development rewrite.

Omabuntu's `tools/desktop_frontends.py` and `tools/display_backend.py` currently
provide a much narrower reviewed surface/backend. The development surface
extractor fails on the new source structure. This is not a safe drop-in update.
The new source invokes additional `omarchy-hyprland-monitor-*` commands and
serializes layout operations; those need native Ubuntu implementations, validated
arguments, state ownership and rollback rather than PATH exposure to upstream bin/.

Import the original target UI/model with narrow backend adaptations. Keep private
monitor profiles authoritative; do not migrate or replace them during analysis.
Persistence, output disable, mirror, rotation and layout actions require explicit
backed-up approval before any live application. Do not add lid/suspend behavior
as a hidden dependency of the display update.

### 5. Network, weather, power and menus

- **Network:** new connectivity presentation avoids misleading ping/loss numbers
  without internet. Captive-portal handling and DNS pending-state behavior change.
  Keep NetworkManager-native operations. Do not import DNS changes or Tailscale
  exit-node handling automatically, especially on managed/VPN machines.
- **Weather:** automatic location changes to `geo.omarchy.org`; the source model
  adds auto/effective-location handling. Omabuntu currently uses its approved
  wttr.in/Open-Meteo backend. Updating UI does not authorize a new external
  location service; preserve the current backend unless separately agreed.
- **Power/battery:** upstream improves fully-charged wording, missing values and
  fallback to UPower's battery rate; panel timing changes are small. Do not
  import notification service ownership, idle inhibition or power-policy changes.
- **Menu:** upstream keeps prior menu rows on malformed/mid-write reads, and moves
  appearance/navigation items. Omabuntu has its own menu model/action allowlist;
  compare semantics there rather than copying the full new management menu.
  Bindings also change: do not overwrite Omabuntu's accepted screenshot chords
  to follow upstream's unrelated application mappings.

### 6. Runtime, provenance and excluded features

The root LICENSE is byte-identical at all three commits (same SHA-256 as
`upstream/omarchy-source.json`). This does not clear newly added branded SVGs,
third-party code, datasets or dependencies. The shell delta includes 33 asset
paths for stable and 36 for development, largely in the agents area. No such
assets were imported. Upstream also changes notification architecture, agents,
local-model integration and the lock implementation; those are not implicitly
admitted by an update to the currently ported components.

The package list replaces stock power-profiles-daemon with an Omarchy fork and
adds/removes other integration packages. Do not translate that list into Ubuntu
install commands. Omabuntu's pinned Quickshell, Qt compatibility work, and
reviewed Hyprland/hyprbars ABI pairs remain independent gates. This review did
not establish a new package recipe or a minimum Qt/Quickshell requirement; no
runtime upgrade is justified solely by selecting the newer Omarchy commit.

The latest development commit introduces an **Apple Silicon-specific** wide-gamut
monitor wrapper, whose own comments warn that applying the same conversion on a
PC would convert twice and wash colors out. Do not apply that workaround on the
Ubuntu PC as part of generic color parity. Keep the shared Auto-HDR exclusion.

Exclude Arch provisioning/migrations, package sources, kernel/boot management,
PAM/fingerprints, sudo/firewall/security policy, realtime-service changes,
corporate-browser policies, SSH activation and system power-management changes.
Preserve GNOME and existing login, VPN, certificates and keyring behavior.

## Concrete extraction blockers

These are pure transformation smoke checks, not compiled/runtime acceptance:

| Existing Omabuntu extraction | v4.5.0 source | Recorded quattro source |
|---|---|---|
| Clock host and calendar | Completes; new dependencies still need admission | Completes; new dependencies still need admission |
| Bar frame and both tooltip extractions | Completes; shared geometry/API review still required | Completes; shared geometry/API review still required |
| Bluetooth and power surfaces | Completes | Completes |
| Network surface | Fails an extraction witness | Fails an extraction witness |
| Weather surface | Fails the old wttr.in location-command witness | Fails the old wttr.in location-command witness |
| Display surface | Completes; backend review still required | Fails an extraction witness |
| Dock | Completes; shared dependencies still need admission | Fails an extraction witness |

The fail-closed behavior is desirable. Do not relax witnesses, remove forbidden
command checks, or overwrite staged digests just to make a new pin pass.

## Recommended update sequence

1. **Freeze the selected stable target.** Use v4.5.0 at
   `ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Quattro is comparison evidence
   only, not a source-update target or a presumed superset of stable.
   Record deliberately deferred features and approved Ubuntu deviations.
2. **Rebase provenance and the shared UI closure in a private candidate.** Update
   byte-identical vendor parents, notices, new dependencies, transforms and their
   expected hashes together. Extend Style and bar/popout contracts from original
   target source. Keep mutable upstream loaders and services outside admission.
3. **Bring clock, tray, tooltip, dock and workspace fixes across.** Include the
   new stable WallClock dependency and deterministic regressions, not only copied
   parent files. Test the shared frame and interactions before visual approval.
4. **Retain the reviewed Ubuntu display backend and stable UI.** The larger
   development display rewrite is not selected. Handle stable
   network/weather/menu/power deltas with existing Ubuntu services and explicit
   endpoint/action exclusions.
5. **Verify and deploy separately.** Full unit suite, clean-source checks,
   provenance/closure checks, compatible QML construction and native multi-output
   acceptance precede any backed-up install. Obtain separate approval for builds,
   installs, service changes, reloads or session transitions. Review fresh install
   and existing-user update behavior; do not update the reference package.

The selected v4.5.0 target is the smaller port: 22 rather than 26 mapped parent
changes, and fewer extraction failures. It is still not a trivial pin update.
Neither candidate should be claimed as full-shell or pixel parity after only
updating the currently mapped components.

## Evidence location and limitations

Raw API responses, hash-checked review text, full tree inventories, selected
source diffs and transformation smoke-check results are private under ignored
`work/research/omarchy-sync-077/`. They are intentionally not committed.

No upstream scripts, QML/Lua, installers, services or migrations were executed.
No installed configuration, source/dependency pin or reference package changed.
Current capability/compatibility documents contain historical observations and
are not treated here as a fresh live functional inventory. No graphical, plugin
ABI, lock/authentication, dependency-build or next-login acceptance was performed.
This is a bounded review of changed relevant source, not a security audit of all
410 development commits or all upstream content.
