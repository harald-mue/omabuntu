# Cross-process native notification checkpoint (Plan 180)

## What passed

`tools/check_native_processes.py` extends Plans 178–179 on one disposable Labwc
output, using the verified exclusive Quickshell variant and unchanged sealed
Omarchy notification closure at `ac2690cd7be4f47e4a255f5e2e78d904d436b068`.
Original Service/Toast, real NotificationServer, surfaces, input regions and
shaders are retained; no production notification source is edited.

There are three genuinely independent roles:

- The notification service runs in one Quickshell process.
- An owned fullscreen native application window runs in another Quickshell
  process. Its click/key counters are queried with IPC selected by its actual PID.
- An authored QtDBus sender maintains a persistent connection, sends real Notify
  calls and receives its own native ActionInvoked/NotificationClosed callbacks.
  Its reported PID and unique bus name are checked against the private bus.

Four native cases pass:

1. The persistent sender creates and replaces a notification without duplicating
   its native ID. A real pointer click on the original card produces the matching
   `default` callback and dismissed-close callback in that sender. Its own status
   counter reports exactly one action; the click does not reach the separate app.
2. The separate app receives a native A key before original exclusive keyboard
   mode, is excluded during that mode, and receives the next native A after
   Escape **without a refocus click**. This crosses a real process boundary,
   unlike Plan 179's same-process background window.
3. The sender is stopped and the bus confirms its unique name disappeared. The
   original visible snapshot remains. Clicking it closes it without a crash;
   a later sender observes the old action ID but does not count it as its own.
4. The later sender creates a fresh, nonreused ID and receives exactly one own
   action/close callback from the next native card click. Original service and
   application remain responsive.

**Broadcast caveat:** standard native action signals are broadcast, not private
unicast replies. The later synthetic sender explicitly filters IDs it did not
create. This is client-side callback attribution, not a daemon confidentiality,
authorization or adversarial-isolation guarantee. A live privacy/security review
must not reinterpret it as one.

## Implementation and containment

`tests/fixtures/notification_sender.cpp` is authored test code, not imported
upstream code. Python standard library remains the orchestrator. Existing
Qt6Core/Qt6DBus 6.10.2, moc and the compiler are justified test-only dependencies:
they provide the real persistent D-Bus client without adding a Python dependency.
Both package versions must match before compilation. Compilation runs **inside**
the disposable Bubblewrap namespace; generated moc source, binary and compiler
logs stay under the private writable test home. No download, package installation,
runtime rebuild, release selection or host build output is involved.

The sender admits only fixed notify/replace/status/quit commands, bounded input,
fixed synthetic notification text/actions, its own IDs and the verified service's
unique bus owner. It refuses ordinary host bus configuration. It does not launch
applications, URLs or commands from notification hints. The application and sender
are fixtures, not production applications whose behavior has been accepted.

The runner rechecks the existing private nine-package lab, runtime eligibility and
notification source seals, and records fixture, pointer, bootstrap, runtime and
compiled-sender hashes. It reuses the reviewed headless/Pixman/SHM + Qt OpenGL/
llvmpipe namespace without host bus/socket/home/device mounts or inherited display
identity. The new private bus has no activation directories; activation helpers
and Xwayland remain guarded. No live notifications/history, DND or clipboard are
read or changed. Both native graphics contexts report llvmpipe; only the exact
absent-Hyprland warning is accepted for the service and none for the app.

```sh
python3 tools/check_native_processes.py
python3 tools/check_native_processes.py --run \
  --lab-dir work/<verified-private-lab> \
  --candidate work/notification-runtime-builds/<verified-variant>
```

Default behavior is plan-only. The explicit diagnostic has bounded commands,
35-second compilation steps, 35-second QML and 30-second sender watchdogs, and an
85-second outer limit. These bounds do not apply to normal desktop components.
All owned processes are reaped and source/runtime/lab inputs stay unchanged.
One synthetic final capture, event metadata, build commands/logs and failures
remain private under ignored work/.

The first attempt passed native callbacks and cross-process focus but failed the
test-side decoder on D-Bus's lowercase `false`. An exact true/false response
parser corrected that fixture error; no notification, application, native input,
policy or containment source was loosened. The failed evidence is retained.

## Verification and remaining gates

Thirteen new synthetic parser/pipe/fixture regressions and all 1,759 unit tests
pass without launching a compositor, bus or compiler during the unit suite.
All nine clean-source export checks pass without the original lab/runtime/work
inputs. Four existing document backups verify by hash/mode, and final source,
dependency, staged-driver and sender-binary hashes match the native receipt.

The subsequent [history/transience/redaction checkpoint](notification-native-history.md)
is blocked: functional state assertions pass but the full native sequence emits
layout binding-loop warnings. Its clean smaller controls are not acceptance and
no production source has been changed to bypass the warning gate.

The following remain unaccepted: real production application behavior, application
launch/window routing, Hyprland focused-output/fullscreen/focus policy, multi-output
input/scaling/hotplug, complete pointer/scroll interactions, clipboard/code-copy
secrecy, locked-session privacy, adversarial security/recovery, pixel identity and
crash causality. This probe does not implement artifact-bound host admission or
reversible live migration.

No SwayNC, installed release, live compositor/shell or debug capture is inspected
or changed. Current debugger liveness is not inferred. No commit or publication
occurs; a live provider/shell switch still needs separate approval.
