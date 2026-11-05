# Omarchy 4.5.0 stable component update

## Scope and provenance

Plan 078 updates admitted desktop-component source from v4.5.0-rc1
(`03ff1eff3812933f7088484533784d2f63eaf19a`) to **v4.5.0 stable**
(`ac2690cd7be4f47e4a255f5e2e78d904d436b068`). Quattro/development is not selected.
This is a component rebase, not an Arch installation, full-shell migration or
claim of complete Omarchy feature/pixel parity.

The original 71 mapped source parents were compared with the immutable stable
Git tree; 22 changed. Those unchanged vendor parents were refreshed byte-for-byte
and the original `WallClock.qml` dependency was added. The profile now maps 76
staged targets to 72 unique source parents. Git blob SHA-1, SHA-256, size, pinned
URLs, stage transforms and staged hashes are recorded together in
`upstream/clock-preview.json`; verification rejects drift and unknown witnesses.
The upstream MIT notice is unchanged and preserved. No new artwork, fonts,
datasets or independently licensed dependencies were imported.

Existing tracked candidate paths were backed up with hashes/modes under ignored
`work/backups/` before editing. Raw tree responses, selected source comparisons
and validation logs remain private under `work/research/omarchy-sync-077/`.
The separate rc1 reference package was not modified; its provenance evidence and
old lexical-closure counts are explicitly historical. Runtime, plugin, artwork
and build-source pins were not relabeled or upgraded.

## Included changes

- Original stable shared buttons, glyphs, sliders, tray, tooltip and keyboard
  panel source, including symbolic tray-icon and warm tooltip-handoff behavior.
- Stable easing and 250 ms theme transitions in the compatibility surface.
- Shared painted-bar/popout geometry contracts: center/right section owners
  report their card geometry separately instead of using full-screen windows.
- Original stable `WallClock.qml` and DST-safe tick scheduling in the clock host
  and calendar, with tick-boundary and timezone regressions.
- Stable dock, power, Bluetooth and display surface updates, retaining existing
  Ubuntu controllers and approved action boundaries.
- Stable network frontend extraction and pending-DNS presentation property,
  without enabling upstream DNS policy/actions.
- Stable weather panel/model and city editing, with an explicit adapter from
  the existing location helper's plain city response to the stable model shape.
- Appearance hierarchy and position before Trigger. Legacy `style*` aliases
  continue to work for menu routes and image-picker provider/action requests.
  Malformed or partially written menu definitions cannot replace the surface's
  last complete menu with empty/partial rows.

Source-derived mirrors are regenerated, not independently redesigned panels.
Fixture-only copies explicitly substitute native window ownership; the tooltip
bubble geometry fixture bypasses only the native output-scale reveal gate.
Production tooltip scale gating remains original upstream source.

## Retained adaptations and exclusions

- Network remains NetworkManager-native. No upstream DNS/Tailscale changes,
  new VPN policy, speed tests, QR tools or new 802.1X profile creation are
  enabled. Imported dormant model command strings are not execution authority.
- Weather retains the bounded wttr.in/Open-Meteo helper. The new upstream
  `geo.omarchy.org` endpoint and raw curl commands are not staged. No new
  location service, notification ownership or IPC route is admitted.
- The frame remains fixed, top-only and slot-based. Stable auto-hide/peek-window
  tracking and its `BarModel` dependency are removed from that extraction;
  widget registry, arbitrary command/QML loading, drag-layout persistence,
  notch policy and full upstream startup remain excluded.
- Keyboard panels keep the reviewed on-demand focus, unmap/close and hit-testing
  adaptations rather than unconditional upstream exclusive focus.
- Full audio/backend parity and full service/plugin ownership remain outside
  this update. Existing output/input limits and native device gates still apply.
  See [audio output](audio-output-port.md), [desktop panels](desktop-panels.md)
  and [bar boundaries](bar-port.md) for the existing per-action exclusions.
- The larger development-only display rewrite, dock dependency changes and
  Apple Silicon wide-gamut wrapper are not stable update requirements.
- No AI/agent assets, distribution provisioning, boot/kernel/security policy,
  authentication/lock/idle/suspend activation, corporate browser changes or
  private monitor-layout changes are included. GNOME isolation is unchanged.
- The accepted `render.cm_auto_hdr = 0` default is preserved, not reverted.

## Verification and remaining gates

The final unit suite passes **1079 tests**. The clean-source candidate export
passes its isolated source/unit/CLI checks without reusing private build inputs.
`git diff --check` passes.

Using the existing verified runtime stage, contained checks pass for:

- clock content/render/policy and deliberate rejection controls;
- clock mathematics in UTC, Berlin, Havana and Santiago, plus a deliberate
  assertion control (229 assertions in each positive timezone case);
- tray, all eight tooltip cases (including warm handoff), all seven fixed-frame
  cases, network, Wi-Fi, audio, applications and keyboard-layout fixtures;
- original desktop-panel construction, spacer geometry, command-menu navigation,
  and image-picker theme/background helper round trips.

These are synthetic/offscreen construction and behavior checks, **not native
Wayland visual or functional acceptance**. Fractional-scale popup mapping,
multi-output placement, real focus/dismissal, tray interaction, live hardware
and network/device actions still need separate backed-up deployment and native
acceptance. No new runtime package was built or installed for these checks.

During the source-only work in plan 078, no installed configuration was edited,
service started/restarted, Hyprland reloaded, session transitioned, upstream helper
executed, commit created or remote published. Deployment/build/install and Git
commit approval are separate steps; session-lifetime grants must not become
silent timed wrappers.

## Subsequent approved local deployment

Plan 079 records the user's separate packaging/install/reload/restart approval.
A distinct stable component bundle was prepared using verified existing runtime
and screenshot stages, preflighted and deployed through the transactional updater.
The previous application release remains available for rollback; launcher and
selector prestate were backed up before switching. Only the owned Omabuntu shell
was restarted, with session lifetime and optional wallpaper restoration disabled.
Hyprland configuration was reloaded, not the compositor or login session.

Post-start checks confirm the stable source commit, a new owned running process,
no Hyprland configuration errors, unchanged existing Hyprland entry/managed
snippet hashes, and `render.cm_auto_hdr = 0`. All 1079 unit tests pass.
Startup has no ERROR/FATAL/CRITICAL diagnostics; five warnings remain for portal
application-ID registration and the unresolved `system-reboot-symbolic` icon.
Private deployment evidence is under ignored `work/deployment-079/`.

This establishes local packaging, installation and native startup, not visual,
popup/focus, multi-output or real device/action acceptance. No system packages,
plugins, services/autostart, personal configuration, wallpaper settings or GNOME
policy were changed. No reboot, logout, commit or publication was performed.
