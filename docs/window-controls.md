# Window Controls: shared application buttons

## What this setting does

Super+Space > Setup > Window Controls controls the user's shared application
button layout. **It intentionally affects GNOME and other desktop sessions for
this user, including concurrently running sessions.** The user explicitly chose
this scope in plan 131, replacing the earlier partial launch-wrapper approach.

- **Hide Buttons … → Hide in All Desktops:** set the layout to `appmenu`, the
  original mechanism used before the alternative experiments.
- **Show Buttons … → Show in All Desktops:** set
  `appmenu:minimize,maximize,close`, with those three buttons on the right.
- **Restore Previous Layout … → Restore in All Desktops:** restore the most
  recent change's exact previous layout, or remove the explicit user override
  if the original value was inherited from the desktop default.

Entering a submenu does not change anything. The second, explicitly labelled
confirmation row changes the one shared key. Menu checks reflect the **actual
setting**, including external changes; no saved launcher mode is treated as
proof of application behavior. Changes are disabled when the setting is locked,
required commands are unavailable, or an interrupted operation needs review.

The Omabuntu menu itself still runs only in Hyprland. The selected layout also
applies when using GNOME, without installing an Omabuntu bar in that session.
The command-line interface can restore/show the buttons from GNOME too.

## Application coverage and immediate behavior

The one key is:

```text
org.gnome.desktop.wm.preferences button-layout
```

GTK applications and applications consulting the corresponding desktop setting
can update their buttons regardless of whether they were opened from the app
grid, a keybinding, a terminal or another application. There is no new launch
wrapper or requirement to use a special launcher. Existing applications may
observe changes live; others may read the setting only on startup. No automatic
application restart or logout is performed or required by the helper.

This is the broad mechanism reported as working previously, **not a promise that
every program obeys it**. Application-specific/custom titlebars can override the
layout or draw controls independently. GNOME Files 50.2.2 was the reported failing
case with the old GTK3/Qt process-variable implementation. After the corrected
shared-setting version was installed locally under plan 132, the owner reported
that the menu behavior works. This is local user acceptance in the reported Files
test context, not verification of every application or a fresh GNOME login.

Omabuntu's hyprbars decorations are a separate owner. They are not changed by
this setting, so floating-workspace controls remain governed by the existing
hyprbars rules. Hiding client controls does not remove the entire headerbar,
its navigation buttons, menus or application actions.

Only the one key above changes. There are no CSS modifications, GTK module
injection, browser-profile edits, app restarts, private binding changes, systemd
or D-Bus environment exports, or login/logout toggle-and-restore hooks.

## Prerequisites and read-only review

The optional feature uses existing `/usr/bin/gsettings` and `/usr/bin/dconf`
(`dconf-cli`) with a persistent dconf backend. It needs a normal user's desktop
session bus for writes. It does not install packages or bypass managed locks.
Missing tools, command failures, timeouts, malformed output and incompatible
backend selection are reported, not treated as successful changes.

From the repository, these commands create no state and change no settings:

```sh
python3 -B tools/window_controls.py status
python3 -B tools/window_controls.py plan hide
python3 -B tools/window_controls.py plan show
```

A real CLI change requires an explicit user-wide flag:

```sh
python3 -B tools/window_controls.py set hide --apply-user-wide
python3 -B tools/window_controls.py set show --apply-user-wide
python3 -B tools/window_controls.py restore --apply-user-wide
```

These are usage examples, **not commands executed during implementation**.
Installed release bundles carry the helper as `helpers/window_controls.py`;
use the helper from the selected release if operating it manually. Immutable old
releases do not acquire new code until a reviewed application update.

## Backups and recovery

Before any key write, the backend records the effective value and the dconf
user value or its absence under:

```text
~/.local/state/omabuntu/global-window-control-transactions/<transaction>/
```

`OMABUNTU_STATE_HOME` can override the state root. The backend stores a private,
hash-checked prestate before writing; changes are serialized, bounded, and reject
linked/unowned state files. Restoring an inherited value uses `gsettings reset`
rather than creating a new permanent override. Showing the standard layout is
not the same operation as restoring a user's custom ordering/default inheritance.

Restore refuses unrelated later changes or corrupt backups. It handles only the
latest transaction, never walks back through older history, retains backups,
and can recover a prepared transaction. Unfinished changes block further
show/hide operations until explicitly restored/reviewed. A failed final receipt
attempts to restore the key only while it still matches this operation's value;
external changes are not overwritten by automatic recovery. Filesystem/power-loss
durability and atomicity against other settings editors are not guaranteed.

Changing system defaults during a transaction may prevent exact effective-state
recovery and requires review. Never delete journals or overwrite unrelated values
to make verification pass.

The installer's historical GNOME-button repair recognizes a verified intentional
Hide transaction and does **not** offer to undo it as the old accidental damage.
An unfinished global transaction defers that repair for manual recovery.

## Superseded behavior and acceptance

Plans 128–129's process-variable policy (`GTK_CSD` and Qt Wayland decoration
variables) is replaced, not activated or migrated to a global hide automatically.
Its old saved files/backups are left untouched and are not used as the live
button state. The unfinished plan-130 launch adapter was archived without
installation; original application-launch semantics are preserved.

Automated tests use fake GSettings/dconf commands. They verify one-key scope,
confirmation routes, actual-state menu checks, prior override/absence recovery,
managed locks, failed writes, interrupted journals and the legacy-repair boundary.
These automated tests do not establish native visual acceptance. Separately,
the owner confirmed the local menu test works after plan-132 deployment. Fresh
GNOME login, concurrent desktop sessions, browser-specific behavior and universal
application coverage remain unverified. Installation itself did not toggle the
shared setting; the user tested the switch manually.
