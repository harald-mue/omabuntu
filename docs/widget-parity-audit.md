# Widget parity audit against Omarchy 4.5.0

## Summary and scope

**There are additional omissions.** The highest-priority persistence gaps are
tray pins/hidden entries and calendar preferences other than the label format.
Dock persistence exists, but its QML request adapter can silently drop edits.
Display actions have a similar busy-process problem. A reproducible extraction
and green unit suite do not establish complete behavioral parity.

This audit follows plans 111–112 and compares the checkout, not the live desktop,
with **Omarchy v4.5.0 stable**, commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. It does not compare against quattro or
silently substitute development-only monitor features. No upstream scripts,
provider requests, desktop actions, installed preference reads or restarts ran.
Only repository documentation and private analysis fixtures were created.

`tools/check_clock_preview.py:verified_sources()` passed: 76 upstream target
mappings, 72 unique source parents and 120 staged files, including authored
adapters/module maps/notices. It checks recorded vendor Git blob identities,
SHA-256 values, derivations and authored seals. The pin also agrees with
`upstream/omarchy-source.json`. This establishes the existing mapped-source
baseline, not an independent fresh download of every upstream shell/helper.
Some original services/helpers are intentionally not vendored; their complete
behavior cannot be inferred merely from a panel's call site.

Mounted bar widgets were traced through `TrialPanel.qml`, `TrialShell.qml`, the
extraction modules and native/Python controllers. App-grid/menu and omitted
full-shell services are covered as scope boundaries, not a claim of an exhaustive
all-applications or compositor-policy audit.

## Follow-up status

The findings below describe the audited baseline. Plan 114 subsequently implements
calendar/tray persistence and host-binding repair, dock/display request queues,
visible failures and fixed-registry keyboard navigation **in source only**.
See [repair details and remaining native-policy gates](widget-preference-repairs.md).
No deployment or complete widget parity is implied; the other exclusions remain.

## Confirmed defects and functional gaps

### 1. Tray: pins and hidden entries are never stored — high priority

Upstream `vendor/omarchy/shell/plugins/bar/widgets/Tray.qml:210` calls
`bar.shell.updateEntryInline()` with both `pinned` and `hidden` arrays.
`config/shell/preview/PortTrayHost.qml:13` initializes empty arrays, and its
`updateEntryInline()` at line 63 only assigns `root.preferences`. There is no
read/write backend. `TrialPanel.qml:226` creates a separate host per output.

**Consequence:** user pin/hide choices disappear when the host/bar is recreated,
and do not automatically synchronize between outputs. The drawer/menu surface
being original does not make this persistence complete. This is the closest
remaining equivalent to the repaired World Clock defect.

Required follow-up: one shared, backed-up preference owner, startup loading,
validated tray identifiers and tests for pin/hide/unhide across restart and
multiple outputs. Do not import the entire upstream shell registry for this.

### 2. Calendar: only label format reaches durable storage — high priority

Upstream clock `Panel.qml:162` persists `weekStartDay`, `birthYear` and
`lifeExpectancy` through the inline clock entry. The derived
`config/shell/preview/CalendarPanel.qml:187` still constructs that full entry.
However, `TrialPanel.qml:137` forwards **only** `entry.format` into
`appearance.set("clock", ...)`. Its `clockSettings` property at line 21 likewise
reconstructs only `{format: ...}`. The appearance registry stores `clock_format`,
not the calendar fields.

**Consequence:** the weekday-start toggle and life-rail values have no durable
write/read path. Saving them can merely resubmit the current label format.
The label format itself does have persistence via
`AppearanceState.qml` → menu helper → `tools/appearance_backend.py:change()` →
`current/bar.json`; it must not be classified as entirely process-only.

There is also a binding problem: `CalendarPanel.qml:193` directly assigns
`hostWidget.settings = entry`, replacing the host's declarative binding to the
shared clock entry. Subsequent appearance changes can cease propagating to that
host. This needs a single coherent clock owner, not an extra disconnected file
that races with the appearance registry.

Required follow-up: preserve all supported clock fields and the shared host
binding; test changing calendar fields, then changing the label via both right
click and Appearance, then restarting/recreating multiple outputs. Treat birth
year as private user state, never repository data.

### 3. Dock: persistence exists, but busy requests are lost — high priority

`FloatingDock.qml:125–153` routes position/autohide/pin-order changes into
`DockState.qml`; `tools/dock_state.py` writes
`$XDG_CONFIG_HOME/omabuntu/dock.json` (normally `~/.config/omabuntu/dock.json`),
with a private file, atomic replacement, a `.previous` backup and a backend lock.
The Appearance menu shares this preference store. Pins, their saved order,
position and autohide are therefore **not generally missing persistence**.
Running-window ordering and transient launch state need not all survive restart.

But `DockState.qml:17` does `if (backend.running) return` without a queue.
`setPosition()`, `setAutohide()` and `setPinned()` update visible state before
calling it. A second edit, or an edit during initial `get`, can appear to work
without ever producing a helper request. A previous response may then overwrite
it. `onExited` also silently ignores nonzero/error/invalid responses.

Required follow-up: serialize/merge pending edits, preserve the latest requested
values, report failures and distinguish pending from confirmed state. Test edits
during load, rapid pin/reorder/autohide changes, backend failure and restart.
The Python file lock alone does not fix requests discarded before Python starts.

### 4. Display: clicks can be dropped during status collection — medium priority

`DisplayPanelController.qml:24` has the same busy-process early return and shares
one process between status, brightness and scale requests. While the popup is
open, status polling occurs every two seconds. A slider release/scale choice can
therefore be dropped while a read is running. Brightness previews can transiently
show a value that was never applied.

This is distinct from intentionally omitted persistent monitor configuration.
The local backend explicitly changes runtime scale only; it does not save
per-output scale rules or restore them at login. Output-enable actions are
unavailable (`canToggle: false`, empty `toggleDisplay()`), and the upstream
text-size section is removed by `tools/desktop_frontends.py:surface()`.
The stable source's panel delegates scaling to
`omarchy-hyprland-monitor-scaling`; this audit did not inspect that unvendored
helper and does not invent its exact persistence contract. Mirror/rotation/layout
features discussed in the older quattro analysis are not attributed to stable.

Required follow-up: prioritize/coalesce user mutations over polling and show
confirmed results/errors. Persistent display settings, output enabling and text
size remain separate design and backed-up deployment approval gates.

### 5. Cross-widget keyboard switching is absent — medium priority

Stable `vendor/omarchy/shell/plugins/bar/Bar.qml:873` implements
`switchPanelFrom()`. Original panel key handlers route Tab through that API.
Neither `TrialPanel`'s bar API nor `PortTrayHost.ownerApi` provides it.
`Ui/Panel.qml:34` falls back to false, the network controller's switch is empty,
the shared desktop controller merely enables its cursor, and the audio
controller instead alternates local sections.

**Consequence:** source-derived Tab handlers do not provide original adjacent
widget navigation. Shared popout dismissal/card tracking already exists; that is
not equivalent to having the switching registry. Display cursor navigation is
also narrower than the stable panel's section model.

Required follow-up: a reviewed fixed registry of mounted widgets with consistent
Tab/Shift+Tab behavior, not arbitrary source/plugin loading. Verify focus and
multi-output behavior without reintroducing unconditional Exclusive focus.

### 6. Bluetooth power has a different persistence contract — explicit deviation

Stable `bluetooth/Panel.qml:628–638` explicitly avoids `adapter.enabled`, explaining
that BlueZ Powered is not its persistent off-state mechanism; it delegates to
`omarchy-bluetooth-power`/rfkill instead. The local
`BluetoothActions.qml:26` writes `adapter.enabled` directly.

**Consequence:** the local toggle does not implement upstream's persistent rfkill
off-state contract; whether Ubuntu restores a particular radio state is not
established by this source audit. Existing BlueZ pairing records are a different
kind of state and should not be duplicated in an Omabuntu JSON file.

Automatic Bluetooth-to-default-audio routing, the upstream helper's action/error
handling, animated status phrases and a pairing-agent integration are also not
fully ported. Basic pair/connect/disconnect/forget and owned discovery are present.
The omissions are documented safety boundaries, not permission to add rfkill,
services, trust changes or automatic audio routing now.

## Per-widget disposition

| Widget/area | Durable state or backend | Remaining boundary/gap versus stable source |
| --- | --- | --- |
| Clock/calendar | Label presets persist in `current/bar.json` through Appearance | Calendar fields are dropped; host binding can be broken; privileged timezone picker and IPC intentionally omitted |
| Tray | No durable store; per-output arrays only | Pin/hide loss and no shared preference owner |
| Dock | Position/autohide/pins/order in config `omabuntu/dock.json` | Busy writes can disappear; errors hidden; screen-remap guard omitted; no full original dock service |
| Weather | Chosen location/name/coordinates in state `settings/weather.json`; file is watched | Unit is fixed to metric in `TrialPanel`, refresh defaults to 15 minutes; no dynamic widget-settings registry; upstream geo endpoint, notification action and IPC deliberately replaced/omitted |
| Battery/power | Percentage preference persists via Appearance `current/bar.json`; active profile goes to native `PowerProfiles` | No upstream AC/battery-specific helper policy; cycle/threshold readings incomplete; no policy/charge-limit writes; daemon durability is not proven by a QML property assignment |
| Audio | Volume/mute and preferred defaults go to native PipeWire; no local JSON is required merely for widget restart | Per-app stream section, untyped-source helper fallback, physical-output resolver and original helper/OSD paths omitted; WirePlumber/login retention requires separate acceptance |
| Network | Existing profiles plus DNS/band changes go through NetworkManager; `network_nm.py` uses connection modifications | Enterprise creation/credential policy differs; Ubuntu connectivity portal and added Ethernet/VPN profile rows; no original Tailscale integration or upstream command directory |
| Bluetooth | Native BlueZ records/actions, no local preference file | Radio persistence differs, no automatic audio routing or owned pairing agent; see finding 6 |
| Display | Native backlight and runtime monitor scale only, with previous-reading backups | Busy-action loss; no per-output config persistence, text-size slider or output enable/disable |
| Keyboard layout | Uses compositor XKB state and fixed command allowlist | Input-method cycling is inert (`InputMethodState.qml:cycle()` returns false); no fcitx service; switching configured layouts is not saving a new keyboard configuration |
| Workspaces | Saved layout modes in state `current/workspace-layouts.txt`, read through `TrialDesktopState` | Global slots 1–10 instead of original per-monitor blocks; native mode/layout adaptations remain distinct from full original helper semantics |
| Menu/frame/app grid | Appearance registry persists reviewed choices; source-derived controls and Ubuntu action registry | No full shell/plugin registry, draggable persistent bar layout or arbitrary modules; management actions adapted/excluded; app search/hover/selection is appropriately transient |
| World Clock (reference) | Fixed by plans 111–112: shared `settings/elsewhen.json` | Globe-only jump destinations intentionally transient; weather/profile fetches, notification and system-timezone actions still excluded |

The network, audio, battery and Bluetooth rows deliberately distinguish native
service-owned state from preferences that Omabuntu itself must serialize. A
missing Omabuntu JSON file alone is not evidence of lost settings. No claim of
native/session/reboot acceptance is made for those service-owned settings.

## Documentation and test gaps

Several documents retain historical descriptions that are now misleading:

- `docs/desktop-panels.md` still names the rc1 pin and calls battery percentage,
  dock pins/position/autohide and clock label format session-only. Those statements
  predate the corresponding implementations. Its claim that dock launch-pulse
  and minimize/restore behavior is excluded also conflicts with current code.
- `docs/bar-port.md` still lists Bluetooth/monitor/power and workspace modes as
  unimplemented and says audio input is unported, despite mounted controllers and
  the current microphone section. Its tray persistence warning is still accurate.
- `docs/capability-matrix.md` retains global workspaces 1–6 and older theme/font
  status even though source now shows slots 1–10 and implemented appearance paths.
- `upstream/clock-preview.json` includes historical review/limit prose (e.g.
  passive-only Commons and memory-only calendar fields). Machine-enforced hashes
  do not make every old descriptive sentence current.

The current tests verify many source witnesses, backend round trips and safety
exclusions. Calendar tests check that the life/week-start controls exist, not
that each field survives the real shared adapter. Dock tests exercise Python
persistence and source contracts, not the busy QML request path. Consequently
these defects coexist with a green suite.

Private source-logic reproductions under `work/widget-parity-audit-113/` execute
the actual extracted JavaScript functions with fake backends: the calendar
adapter forwards only a label-format request, dock writes disappear while busy,
and display mutations disappear while status is busy. They run no helper,
network or desktop action and are not full QML/native acceptance.

## Recommended implementation order

1. Repair calendar entry persistence/binding and tray shared persistence, with
   end-to-end startup/restart/multi-output regression tests for every setting.
2. Repair the dock request queue/error path and the display user-action queue;
   distinguish requested and committed values and prioritize writes over reads.
3. Implement consistent fixed-registry keyboard panel switching and close the
   remaining cursor/navigation differences.
4. Reconcile current capability documentation and make the setting/action matrix
   an acceptance checklist, not just a list of imported QML files.
5. Review Bluetooth radio retention, AC/battery profile policy, persistent monitor
   settings and other system-backed deviations separately. These are not silently
   authorized by a parity audit and must preserve existing Ubuntu/corporate policy.

No functional repair, deployment or commit is included in this audit request.
