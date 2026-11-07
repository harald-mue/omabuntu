# Appearance: Menu Bar and Dock controls

## Scope and provenance

The repository now implements the first Appearance batch from
[the stable-menu assessment](appearance-menu-assessment.md): the original
Omarchy v4.5.0 Menu Bar and Dock hierarchy, labels and icons from commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Existing MIT provenance/notices
remain in place. Upstream shell actions are replaced with a closed Python
preference registry; no upstream scripts or additional panels are imported.
The implementation and contained evidence are distinct from deployment and
native acceptance. A separately approved local deployment is recorded below;
complete visual/interaction acceptance is still outstanding.

Under Appearance:

- **Menu Bar:** Hide Bar / Show Bar; Bar Background > Opaque Bar, Glassy Bar,
  Clear Bar; Bar Indicators > Show/Hide Battery % and the ten original
  horizontal clock presets, including seconds, date, week and ISO variants.
- **Dock:** Autohide / Always On and the four original positions. The menu
  branch is shown only for a persisted floating workspace, matching the
  existing workspace/dock model. These are the same position/autohide
  preferences used by the existing dock context menu, not a second dock.

Battery rows require a detected present battery. Checked marks and inverse
visibility come from read-only preference guards. The original clock right-click
cycle and battery right-click percentage toggle now use the same persisted
preferences as the menu. A shared shell adapter updates all bar outputs and
refreshes dock preferences after successful requests. Failed menu mutations keep
the menu open with an error; widget mutations retain the previous value and
record `OMABUNTU_APPEARANCE_FAILED` in the shell log.

Glassy means the existing translucent bar background; it does not enable blur
or alter user-owned compositor settings. Clear removes the bar background, not
the widgets or menu registration. Bar hiding removes neither the independent
menu shortcuts nor the shell/dock process. There is no expiry timer, autostart
change, compositor command or reload in this backend.

## Storage and recovery

`tools/appearance_backend.py` is called only through reviewed
`tools/menu_model.py` actions. It accepts predefined choices, never arbitrary
shell commands, paths, QML or clock strings. Mutations require a Hyprland
Wayland identity with no mixed GNOME desktop identifier. This is an environment
safety gate, not authentication or proof of a working compositor.

- Bar preferences: `$OMABUNTU_STATE_HOME/current/bar.json`, otherwise
  `~/.local/state/omabuntu/current/bar.json`, schema version 1.
- Dock preferences: the existing `$XDG_CONFIG_HOME/omabuntu/dock.json`,
  honoring the existing `OMABUNTU_DOCK_CONFIG` override.
- Prestate receipts: `<state-home>/appearance-transactions/<token>/`, private
  directories with exact prior bytes, mode or absence, target and before/after
  digests. A receipt is prepared before the preference file is replaced.

Reads/guards create no preference directories. Invalid schemas, unsupported
values, oversized or non-owned files and symlink paths are refused rather than
replaced. Unknown existing fields and dock pins are preserved. New files are
private; writes are atomic. Appearance changes serialize through an operation
lock; dock context writes and Appearance writes additionally share `.dock.lock`
so their read/modify/write sequences do not discard each other's settings.
The pre-existing dock context helper retains its `.previous` backup behavior.

Legacy `toggles/bar-off` is only a fallback when the new JSON has no explicit
`hidden` value. Show Bar records an explicit false without deleting the legacy
flag. Reversing that transaction restores the exact prior fallback behavior.
No automatic state migration is performed.

For an approved deployed session, use its packaged `menu_model.py` helper:

```text
python3 <packaged-helper>/menu_model.py appearance-state
python3 <packaged-helper>/menu_model.py appearance-set hidden off
python3 <packaged-helper>/menu_model.py appearance-rollback <transaction-token>
```

The first command reads only; the latter commands mutate preferences and are
not diagnostics. A change returns its transaction token as JSON. Rollback
requires the same target configuration and an unchanged recorded after-state;
reverse multiple changes to one file in reverse order. It refuses later edits
or changed backups. An originally absent file is removed, but newly created
parent/lock directories and audit receipts are retained. A failed final change
receipt triggers restoration of that request's original preference file.

Before any live deployment, verify an approved keyboard route to the independent
menu (normally Super+Space), including Show Bar while hidden. Persistent binds
and deployment/restart remain separate approval gates. The helper command above
is an additional recovery route; this work does not add or change keybindings.

## Verification and remaining work

`tests/test_appearance_controls.py` exercises temporary homes only: read-only
missing state, closed actions, schemas, GNOME/mixed-session refusal, exact
rollback, absence/modes, later edits, damaged journals/backups, legacy flags,
unknown fields/pins, guards, clock presets, failed receipt restoration,
packaging and QML binding contracts.

The contained command-menu fixture additionally instantiates the real shared
adapter, serializes three preference writes, checks menu state and executes
Hide Bar / Show Bar through the real helper. It uses a synthetic Hyprland
identity **inside Bubblewrap with a private home and no host compositor**.
The existing contained clock and desktop-panel fixtures also pass. These
contained checks do not establish native layershell behavior, shortcut
availability, multimonitor visuals, real battery behavior, GNOME interaction,
or fresh-machine acceptance. The contained checks themselves did not change
real user preferences, packages, services or the desktop.

### Approved local deployment (plan 095)

A new private, narrowly adapted local release was deployed with an explicitly
approved bar-only restart and session lifetime. Existing runtime/assets/native
artifacts were retained. No compositor reload, keybinding edit, wallpaper
restore, package/service change or publication was performed.

The first native diagnostic found that exact rollback to an absent `bar.json`
left stale in-memory bar settings: the file watcher's load-failure path did not
refresh the shared adapter. That path now refreshes on removal/missing files
and honors `OMABUNTU_STATE_HOME`. The extended contained fixture exercises the
actual production watcher and verifies restoration of defaults after deletion.
The corrected private release was deployed through another reviewed update.

Live checks verified successful preference persistence without shell errors,
bar hiding/recovery geometry on all three outputs, and the independent named
menu shortcut route while bars were hidden. Diagnostic changes were reversed
to the fresh baseline, preserving an independent background selection made
between diagnostic phases rather than overwriting it. Private prestate,
transaction receipts and failed/successful diagnostic evidence remain under
ignored `work/appearance-deployment-095/`.

This proves neither physical Super+Space handling nor visual correctness,
clock/battery right-click interaction, dock edge/autohide behavior, real battery
hardware, GNOME coexistence or fresh-machine acceptance. Those require separate
observation/user feedback; successful persistence is not functional acceptance.
The complete 1105-test suite passed after the correction.

### Background surface correction (plan 096; deployed and user-confirmed)

A subsequent user report found no visible difference between the three
background choices. The pinned Quickshell API requires
`surfaceFormat.opaque: false` for a window that begins opaque and later
becomes transparent; its surface format is fixed at creation. The bar starts
with the Opaque default before loading persisted preferences, so changing the
color alone was insufficient. The repository now explicitly requests an
alpha-capable bar surface, while preserving the three existing color bindings.
This does not force a transparent appearance when Opaque is selected.

The old surface could not be repaired by merely reselecting a menu entry:
the corrected shell needed to create new bar windows. Following explicit user
approval, a new private local release was deployed with a bar-only restart.
Only TrialPanel and provenance changed relative to the verified installed base;
runtime/assets/native artifacts and preferences were preserved. Manifest/startup
checks passed, three bar outputs and the independent menu registration are
present, and no shell error markers were detected. There was no compositor
reload, wallpaper restore or package/service change. The previous release is
retained as the rollback target.

After deployment, the user confirmed that switching the three background
options now works. This closes the reported Bar Background issue for the current
session; it does not establish acceptance of unrelated Appearance interactions,
GNOME coexistence or fresh-machine behavior. These choices affect the menu bar,
not the command-menu card background.

### Battery percentage layout correction (plan 097; deployed and signed off)

The user reported crowded/overlapping battery content when percentages were
enabled. The static Ubuntu bar Row allocated the power view's inherited 26 px
implicit width even though the original power button requested a wider slot.
The adapted power view now follows its button's implicit height and reserves
the greater of its original slot width and the measured label/icon group.
This also covers three-digit percentages without changing the original shared
button, readings, label order, percentage toggle or power-profile behavior.

The contained desktop fixture now uses production-style implicit-size Row
allocation, toggles percentage display and checks 1%, 63% and 100%, measured
content containment, neighboring placement and contraction back to icon-only
width. The old layout is deliberately rejected by that geometry check.
These synthetic checks are not native visual acceptance. Following explicit
user approval, a new private local release was deployed with a bar-only restart,
changing only PowerControlView and provenance. Startup/manifest checks passed;
three bar outputs and the independent menu registration are present, with no
shell error markers. Preferences and the active power profile are unchanged.
There was no compositor reload, wallpaper restore or package/service change.
The previous release remains available for rollback. After being asked to check
the corrected appearance, the user requested closure of all tasks and a commit;
this is recorded as sign-off for the deployed battery correction, not as evidence
of additional automated native visual tests or acceptance of unrelated features.

Still excluded: bar positions/stacked clocks, full Glassy/GTK/terminal changes,
window gaps/corners/ratios/animations/transparency, default workspace layouts,
branding, screensaver/idle/lock, and Unlock/Plymouth/boot changes. These are not
silently mapped to partial substitutes.
