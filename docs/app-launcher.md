# App launcher: first-open catalog publication fix

## Report and cause

User reports that the first Super+Alt+Space opening is empty, while closing and
opening again shows applications. The authored launcher sampled
DesktopEntries.applications.values only in open()/filter changes and copied
those rows to its own ListModel. It did not subscribe to catalog publication.

Verified pinned Quickshell source, not an assumed delay:

- core/desktopentry.cpp: DesktopEntryManager construction calls the scanner.
- DesktopEntryScanner::run (350-371) queues onScanCompleted with
  Qt::QueuedConnection, including for that initial scan.
- onScanCompleted fills the model and emits applicationsChanged (506-587).
- DesktopEntries forwards that signal (590-598).

The first snapshot can therefore be empty even after the initial file scan has
run. Nothing rebuilt the already-visible panel when the queued publication
arrived. Reopening happened to sample the now-populated catalog.

## Minimal correction

config/shell/preview/AppLauncher.qml now connects to DesktopEntries and calls
rebuild() on applicationsChanged only while shown. This also initializes the
catalog singleton during launcher construction. The visible panel refreshes in
the same opening even if publication is late; hidden updates do not open the UI,
and open() still samples the latest catalog. Current search text is preserved.

No arbitrary wait, polling, retry-open, hidden launch or extra timeout was added.
The grid geometry, icon sizes, style, keyboard shortcut, focused-screen route,
OnDemand focus and DesktopEntry.execute() semantics remain unchanged. Existing
execution limitations are not fixed by this data-publication change.

## Red/green evidence

Actual isolated Qt red report:
work/apps-port/20261024T171425.913098Z/report.json. The original launcher fails
with exit 42 and the exact assertion "first opening refreshes after publication".
The test publishes the catalog after the first open without closing/reopening.

Green report:
work/apps-port/20261024T171814.962430Z/report.json. Seven fixed cases cover cold
publication, a typed filter before publication, warm data, hidden publication,
removal, native cold publication and the deliberate negative exit 42. The actual
launcher GridView and its first delegate are checked, not just a copied model.

Offscreen fixture ownership replaces PanelWindow with a normal Qt Window and
removes native layershell/screen/shortcut registration only in the private copy.
The model/rebuild/grid code remains real. Most cases use a fake catalog with a
lookup/execution tripwire. Native-cold uses the actual Quickshell DesktopEntries
singleton with only two private generated .desktop files; XDG_DATA_DIRS points
to a nonexistent directory so host applications are not read. Neither desktop
entry is executed, no host shortcut is injected, and native Wayland focus is
not proved by this test.

212 unit contracts pass: work/app-launcher-unit-tests-final.log. Clock/lifetime
regression passed at work/clock-preview/20261024T171608.229347Z/report.json.
Runtime artifacts and staged test inputs remained unchanged. Earlier successful
synthetic reports are retained. The existing SVG warnings from the host btop
icon, observed in the old live log after opening, were not hidden or changed;
they are distinct from missing catalog refresh.

## Activation and recovery

Only the verified bar process was replaced through tools/bar_session.py stop/start
within the ongoing approved bar work. Prior source state remains sealed under
work/bar-session/20261024T170636.340422Z; no installed path was edited.

Current run: work/bar-session/20261024T171842.505322Z, PID 420968. Configuration
Loaded/no-expiry markers, three 26px surfaces, app shortcut registration and empty
configerrors observed. Only the known portal app-ID startup warning remains.
No active Hyprland edit/reload (October 22 mtime retained), logout, package,
service/autostart, audio/network mutation, pointer injection, app execution,
commit or publication. Normal bar operation remains session-long, not reboot
persistence. Stop only the bar with tools/bar_session.py stop, never uwsm stop.

The user's first native hotkey opening after this restart still needs acceptance;
offscreen queued-publication success is not native visual/focus acceptance.
