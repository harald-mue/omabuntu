# Capability matrix

This is an implementation/evidence matrix, not a blanket functional acceptance
record. The current release is [v0.2.5](releases.md#v025-release-scope), including
the earlier [v0.2.4 additions](releases.md#v024-release-scope);
publication does not make optional configuration automatic or establish native
acceptance beyond the explicitly recorded observations. The owner subsequently
confirmed the everyday and VM tests in plan 133; see
[current acceptance and remaining feature differences](project-status.md).
These reports do not add unperformed security or failure-injection tests.

| Capability | Source behavior | Target evidence | Next action | Acceptance |
|---|---|---|---|---|
| Lua configuration | Version-specific Hyprland Lua APIs | Workspace integration reviewed against Hyprland 0.57.0 sources and exercised through an approved config reload | Prefer native Lua; review each imported helper/version | Current workspace config loads without errors; not general native/plugin/security acceptance |
| Core bindings | Original workspace factories plus broader shell/application bindings | All 45 monitor-workspace chords registered exactly once after the approved migration; callback discovery/replay supported by the keybindings menu; unrelated existing shortcuts preserved | Review remaining upstream bindings individually; do not expose original helper PATH | User reports tried workspace and cross-monitor operations working; no config errors; remaining shortcuts are not blanket-accepted |
| Application activation focus | Original global `misc.focus_on_activate = true` | Fresh defaults and dedicated managed module shipped in v0.2.5; installer/updater rollout uses separate confirmation, backups and guarded recovery | Existing profiles require the disclosed desktop grant; fresh-machine helper/login acceptance remains open | Owner confirmed local Chrome interaction; 1,297 tests and signed source/bundle checks pass, not every application's activation-token behavior; see [scope](browser-launch-focus-parity.md) |
| Terminal | Ghostty and Omarchy launch helper | Prototype binds Ghostty directly | Preserve existing terminal configuration; no provisioning inferred | Ghostty is used locally and padding behavior was confirmed; the private configuration is not shipped |
| Tiling and decoration | Dwindle; gaps 2/10; border 2; rounding 8; blur off; shadow on | Prototype uses these values and parses natively | Back up target before any application; test behavior | Parser accepted; runtime untested |
| Workspaces | Per-monitor helper logic and persistent modes | Original allocation/widget with narrow Ubuntu state adapters, ten local slots per monitor, real-ID modes/minimized tags and journaled adoption; shipped in v0.2.4 | Explicit opt-in/migration for existing profiles; owner reports docking/hotplug and fresh-login checks working (plan 133) | Local migration preserved windows/output geometry/layouts; tried operations received positive user feedback; see [boundaries](monitor-local-workspaces.md) |
| Input | German layout and custom Shift+Caps Compose | Bar mounts the original keyboard-layout widget with upstream visibility: hidden on this single `de` layout and no input-method indicator; xkb cycling stays allowlisted; `xkbcli` 1.13.1 is installed | Use German layout; evaluate XKB extension separately; a second kb_layout is a separate approved config edit before the label appears and click-cycling does anything | Widget unit-tested; native click acceptance pending |
| Displays | Original monitor panel and source-specific helpers; no authored profile page in that panel | Plan 162 withdraws rejected Plan 161 profile navigation/automation owner; restores the single original-derived brightness/text/scale/output surface and guarded direct output switches; text remains shell-local | Legacy profile code/data retained dormant; no layout/text mutation or automation activation by deployment; GNOME/global text and full rule/window rollback excluded; see [monitor controls](display-profiles.md) | Earlier brightness/scale owner-accepted; 15 new fake-native cases and actual contained QML pointer-signal/keyboard/text readback pass; corrected visual/native output behavior still requires owner acceptance |
| Desktop shell | Original Quickshell shell | Pinned runtime built/staged with warnings; original tray integrated, five isolated tray fixtures pass; left side is the menu mark and workspaces, with no Apps button or focused-window title; keyboard-layout widget follows upstream visibility; Elsewhen sits to the right of the clock; shared persistent cities/preferences locally deployed with clean startup (plans 111–112); watched theme palette with the original color behaviors, background looks and bar-off flag | Complete the [original bar port](bar-port.md); do not start the full original shell | Multiple timed three-output trials, app grid and workspace clicks confirmed; tray/calendar/dock/World Clock persistence and existing navigation accepted by owner (plan 133); full shell incomplete |
| Themes and fonts | Original appearance choices and theme/font services | Reviewed Ubuntu theme/font backends, palette watching and curated/staged resources are implemented | Preserve notices and review further imports; full original services remain excluded | Source/backend tests; individual native choices require acceptance |
| Notifications/Polkit | Shell-owned services | Current GNOME session must remain intact | Inspect agent ownership before shell tests | Not tested |
| Clipboard/capture | Shell helpers, Omasnap, portals | Omasnap 1.24.0 (`a432f40`) installed at `~/.local/bin/omasnap`; Print and Super+Shift+S call the reviewed wrapper; the Omasnap layer is excluded from screen sharing | The user takes the first capture. Recording, OCR, and the color picker stay out | Bound and reloaded; not captured |
| Audio/network | Original audio/network sections | Output, typed-input/peak and application-stream controls; derived network surface and Ubuntu-native extensions; Plan 163 disables the authored Advanced audio entry/page and its cursor/invocation routes | Optional bridge stays ungranted with no normal UI consent entry; no implicit virtual-input fallback access; backend/recovery records retained; full parity/live acceptance remains separate | Owner reports earlier audio/microphone/network interaction working (plan 133); contained normal-layout/disabled-entry and backend fixtures pass, not current native/pixel acceptance |
| Bluetooth | Original grouped device panel | Original surface/discovery; Plan 158 source adds shared owned PIN/passkey/confirmation agent, structured actions/cancel and uncertainty fences | Plan 159 locally installed with managed-bar-only restart; default-agent/trust/radio/routing/profile policy excluded | Existing interaction owner-accepted (plan 133); new source: 22 private-bus native and seven contained QML cases, not live authentication/security acceptance; see [completion](bluetooth-completion.md) |
| Power | Original battery/profile panel | UPower and native Ubuntu power-profiles-daemon interface, no session controls | Native battery/profile acceptance | Isolated construction/mock actions tested |
| Floating dock | Original app dock on floating workspaces | Original window/pure model; confirmed floating grants/restoration; persistent position/autohide/pins; plan 114 queue repair deployed under plan 117 and published in v0.2.4 | Full original service/screen-remap parity remains separate | Owner reports everyday dock/persistence tests working (plan 133); not full source/pixel parity |
| Manual screen lock | Standalone Hyprlock substituted for the unadmitted original lock UI | Installed v0.9.6 config shows the recorded still through `~/.local/state/omabuntu/current/lock-background`, three blur passes, no clock and no wordmark; explicit `lock --apply` and SUPER+CTRL+L remain | Keep idle/suspend separate; wrong-password and policy checks remain open | Lock, unlock and all three outputs accepted earlier; the new surface is installed and was not locked |
| Idle/suspend | Quickshell idle, sleep integration | No approved idle or sleep policy | Preserve existing mechanism; separate safety gate | Not activated |
| Optional widgets | Weather, agents, live wallpaper, dictation | Separate original weather panel with city editing, approved wttr.in IP location and Open-Meteo city search/forecast | Verify native city editing/select/clear; agents, live wallpaper and dictation stay out | Location-parity update deployed with clean startup; IP lookup and city search checked, native UI acceptance pending |
| Updates/provisioning | Arch-specific management | Not a project capability | Do not expose these routes in menus or PATH | Excluded |

The shared application-button setting is separately implemented and locally
accepted by the owner; see [Window Controls](window-controls.md). It deliberately
affects this user across desktops, including GNOME, after confirmation, without
changing hyprbars. Fresh GNOME-login/universal application coverage is not claimed.

Plan 114 adds calendar/tray shared persistence, dock/display queues and fixed
keyboard panel navigation; plan 117 locally deployed these and the original
Network surfaces with a backed-up, verified bar-only restart. See
[repair status](widget-preference-repairs.md) and the
[deployment record](network-original-surface.md#approved-local-deployment-plan-117)
for tests and remaining native interactive/policy acceptance boundaries.

Before applying any configuration: verify target backups, record path-by-path
changes and rollback, and obtain application approval. Matching version/commit
does not establish native plugin ABI compatibility or validate enterprise security.
