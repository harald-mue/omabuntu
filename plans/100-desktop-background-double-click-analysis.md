# Assess desktop double-click background interaction

## Goal and evidence

Determine whether Omarchy changes or selects wallpaper on a desktop double
click, and propose a faithful Ubuntu-native integration. Compare the background
plugin, bar gesture, relevant Hyprland bindings and existing Omabuntu image
picker/background ownership backend against Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Distinguish desktop wallpaper from
bar background and cycling from opening a picker.

## Gaps and proposed analysis

Omabuntu uses the original adapted image picker and a reviewed background
backend, but desktop input ownership may differ from Omarchy's original
background layer. Identify the exact event handler, input surface/protocol,
command/IPC path and multi-output implications. Recommend a bounded reuse of
the original component with narrow backend adaptations, or explicitly identify
missing infrastructure instead of inventing an invisible full-screen overlay.

## Safety and exclusions

Analysis/documentation and private source evidence only. Check upstream license
and pinned blob identity before using additional public reference source; do not
import it into the product. No live input capture, wallpaper setting, layer,
key/mouse binding, process start/restart, compositor reload, package/service,
config/PATH, commit or publication changes. Do not intercept application clicks,
claim lock-screen acceptance or silently replace the existing wallpaper owner.
No new component expiry timers or autostart proposals without separate gates.

## Tasks

- [x] Verify pinned background/bar sources and locate actual gestures/actions.
- [x] Compare current wallpaper/picker/input ownership and integration gaps.
- [x] Document feasible approach, exclusions and approval/acceptance requirements.
- [x] Run unit tests and diff checks after documentation changes.

## Outcome

Eleven original blobs match the pinned stable tree, including MIT provenance.
Desktop left double click opens the wallpaper selector; right double click
opens themes. The image-selector IPC bridges to the original image-picker.
A separate bar double click cycles bar appearance, not wallpaper.

The user rejected the proposed integration and explicitly requested removal
of the assessment document. The document was removed; its previous contents
and this plan's pre-edit state were retained privately under ignored work/.
No implementation will proceed from this proposal. The existing menu-based
background selection and hyprpaper ownership remain unchanged.

All 1130 unit tests and `git diff --check` passed. Reference verification and
test evidence remain under ignored `work/desktop-double-click-100/`. No product,
desktop input, wallpaper, binding, service, commit or publication was changed.
