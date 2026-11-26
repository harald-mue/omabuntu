# Original notification native fixture checkpoint (Plan 178)

## What actually passed

The verified exclusive Quickshell variant runs the sealed original Omarchy
v4.5.0 notification closure (`ac2690cd7be4f47e4a255f5e2e78d904d436b068`), with
its real NotificationServer and original native cards, on one and two disposable
Labwc outputs. This advances beyond the earlier surface-stripped model fixture
and generic graphics controls. It does **not** activate the live notification port.

`tools/check_native_notifications.py` compares every staged notification byte
against the sealed frontend before execution. The original Variants, PanelWindow,
input region, Toast/DeedButton, masks/shaders, Hyprland import and IPC remain.
Only the separate test root supplies a synthetic bar context, fixture metrics,
a bounded watchdog and a private palette control. It never replaces a card or
calls a key handler to simulate native input.

Both output cases pass:

- Actual private-bus name ownership belongs to the fixture Quickshell PID; original
  state preparation/readiness completes and all original native surfaces map.
- A real synthetic Notify produces a measured original Toast and a photo card on
  exactly one output. Replacement keeps its native ID without a duplicate;
  two messages from the fixture source form the original grouped deck.
- Native screenshots prove the synthetic photo loads, its original mask rounds
  all four corners, and notification painting stays in the expected deck area.
- A private icon theme contains two identical authored red SVG squares. The
  `-symbolic` name exercises the original monochrome MultiEffect path with a
  distinct green fixture foreground; its square becomes green. The nonsymbolic
  control stays red. The fixture restores the normal fallback palette afterward.
  This checks operation/hue and raw preservation, not exact pixel identity or
  a hand-derived opacity formula.
- Original DND IPC changes **only this isolated service's** quiet state and
  suppresses a synthetic ordinary card; no SwayNC/host DND adapter is instantiated.
- `wtype` delivers real virtual-keyboard Escape/Return events through the private
  compositor. Escape changes original keyboard mode to off. Return invokes the
  standard `default` action and emits exactly one matching native ActionInvoked
  signal on the private bus, then releases original keyboard mode. A private
  gdbus observer receives the signal; no real application is launched or focused.
- Original low-urgency expiry honors its 5-second minimum. Read-only final state
  validation finds empty live state, quiet off and schema-valid synthetic history,
  including silenced/expired records; it does not create/reset missing files.
- Qt reports llvmpipe. Only the exact unavailable-Hyprland warning is expected;
  other warning/error diagnostics and QML assignment/binding failures refuse.
  Read-only source/runtime/lab inputs stay unchanged; all owned children are reaped
  and the private execution sentinels remain untriggered.

Four rendered states per output (photo, grouping, symbolic, raw icon) plus empty
references are retained privately: twelve card-state captures and three empty
references across the two cases. Captures, commands, source/runtime/checker hashes,
state-validation metadata, logs and failures live only under ignored work/.

## Reproduction and containment

The tool is plan-only unless explicitly requested with both verified inputs:

```sh
python3 tools/check_native_notifications.py
python3 tools/check_native_notifications.py --run \
  --lab-dir work/<verified-private-lab> \
  --candidate work/notification-runtime-builds/<verified-variant>
```

No dependency download/build/install is performed. The tool reuses Plan 177's
verified nine-package extraction and reviewed Bubblewrap graphics sandbox:
private user/PID/network namespaces, minimal /dev without GPU/input, no host
runtime/home/config/socket/bus mounts, fresh private state and cleared environment.
Labwc uses headless/Pixman/SHM; Qt uses OpenGL/llvmpipe, not its 2D software
adaptation. Activation-environment updates remain disabled; Xwayland/systemctl/
activation helpers remain guarded. The dedicated bus config has no activation
service directories and exists only inside the disposable namespace.

Each test has bounded readiness/command/lifetime limits, including a 35-second
fixture watchdog and 65-second outer case deadline. These are disposable
**diagnostic** bounds, not lifetime wrappers for normal desktop components.
No installed release, SwayNC process, live shell, debugger or desktop session is
readmitted, restarted, stopped or reconfigured. Notification host admission flags
remain false; this private test root is not a host deployment-role producer.

## Retained failed controls

Failures were preserved rather than reclassifying them as passes:

1. The first metrics fixture checked `liveEntries` for a photo, but those are
   deliberately persistable records with image fields excluded. Metrics now read
   original layout rows instead; no original service/store code was changed.
2. An immediate short-lived virtual keyboard did not deliver the expected Escape.
   A documented `wtype -s 500` warm-up and short post-event hold keep the owned
   device present while the private seat/client settles. Actual native events
   then pass; this is not a direct handler-call fallback or an established crash
   diagnosis.
3. Initial private icon-theme setup missed a parent directory and failed before
   any native child started. Parent creation was corrected within the fixture.
4. A pale-gray icon expectation assumed a simple 85% RGB mix and failed despite
   actual tinting. The corrected control uses a distinct green private palette
   and identical symbolic/nonsymbolic red source assets to discriminate tinting
   from raw painting without assuming the combined shader's numeric transfer.
   The shader, source icon loader and production palette adapter remain unchanged.

## Source verification

Seventeen new synthetic harness/refusal regressions pass without launching a bus
or compositor. The full `python3 -m unittest discover -s tests -v` suite passes
1,732 tests. All nine clean-source export checks pass without the original work/
lab, runtime or images. These source checks do not execute the native probe or
substitute for its separately retained native receipts. Existing document/plan
backup hashes and modes are preserved privately; no commit was made.

## Subsequent native input checkpoint (Plan 179)

The separate [pointer/focus fixture](notification-native-input.md) now proves
single-output native hover hold/leave/resumed expiry, grouped deck expansion,
idle/outside-deck click-through, right-click dismissal, left-click standard action
signal and exclusive-keyboard handoff to an owned native background window.
Original source and this Plan 178 checker remain unchanged. That background is
another native window in the same fixture process, not a real external app.
Plan 180's [cross-process fixture](notification-native-processes.md) subsequently
adds a separate native app and persistent sender, verifying own action/close
callbacks, focus handoff and sender-exit behavior. Those remain synthetic actors;
production application policy and confidentiality of broadcast signals are not
accepted by that evidence.

## Still explicitly unaccepted

- Multi-output pointer behavior, scaling/hotplug, scrolling/dragging, precise
  rounded-corner input behavior, full interaction coverage and keyboard focus
  handoff to an underlying real external application.
- Actual application callback/lifecycle behavior: a private observer receiving the
  native action signal is not a real sender application or launch/focus test.
- Hyprland focused-monitor/window-address routing, fullscreen/direct-scanout and
  policy-specific focus behavior. Labwc exercises the original absent-Hyprland
  output fallback only; output numbering is not focused-monitor acceptance.
- Clipboard, code-copy secrecy, locked-session privacy, full native redaction/
  recovery/security acceptance, visual/pixel identity, and crash causality.
- Artifact-bound live host admission, provider/autostart/activation/DND backups,
  reversible SwayNC migration and a separately approved shell/provider switch.
  Session GDB capture was not inspected or interrupted; no claim about its current
  liveness is inferred from these isolated tests.
