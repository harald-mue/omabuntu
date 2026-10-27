# Bar tooltip clipping investigation and activated correction

## Report and evidence

User report: element hover is rendered but only partly visible. No screenshot or
native pointer reproduction has been collected, so the exact visible artifact is
not yet confirmed. There is a concrete defect in the authored bar owner:
showTooltip ignored the hovered item and forced a normal Qt Quick Controls
ToolTip visible even for empty text. It supplied neither the original target
anchor nor an independent Quickshell popup surface. An incorrectly placed
in-window popup in the 26px bar can explain the clipped hover. This is not proof
that every reported hover artifact has that cause.

The prior behavior is retained in sealed stage
work/bar-session/20261024T161308.276025Z. After user approval, the fix was activated
at work/bar-session/20261024T165402.318224Z and retained in the subsequent
[section layout run](bar-frame.md). No pointer was injected. Actual visible
hover correction still requires acceptance; startup success is not that proof.

## Prepared source correction

Fetched/reviewed original public shell/plugins/bar/Bar.qml at Omarchy commit
03ff1eff3812933f7088484533784d2f63eaf19a. All 104979 bytes matched the pinned
Git tree blob and reference. Vendor source remains unchanged, with full MIT
notice. The bounded read allowance is 128KiB only for this exact parent;
other source limits remain 64KiB.

The closed profile stages two deterministic reviewed extractions:

- BarTooltipHost.qml: original hover validation, empty-text rejection, request
  generation, stale-exit ownership guard, 400ms delay and 100ms invalid-target
  check. Item-typed references clear when targets are destroyed.
- BarTooltip.qml: original PopupWindow, target-window lookup, centered placement
  below the item with 6px separation, PopupAdjustment.Slide at screen edges,
  border/palette/typography and plain-text label. Root references become the
  restricted host; no whole original bar startup is loaded.

PortTrayHost now delegates to this host/window instead of creating a bare
Controls ToolTip. Empty-label elements no longer request an empty rectangle;
leaving an older element cannot dismiss a newer element's tooltip. Vendor code
is not edited. Exact parent/derived hashes and notices are checked in
upstream/clock-preview.json. No focus-grab behavior, pointer automation, helper,
bar-off probe, file watcher or theme-service startup is imported.

## Verification boundaries

206 unit contracts now pass, including the later section-layout contracts. Seven actual isolated Qt cases cover empty text,
400ms admission, rapid A-to-B hover with stale A exit, leaving, target deletion,
original bubble measurement/plain text and deliberate assertion failure
(exact exit 42). No real hover is injected into the desktop.

Offscreen cannot validate a native xdg-popup or its compositor anchoring.
The geometry case executes the original BorderSurface/text independently,
not a visible native popup. Its measured 133x26 bubble also corrected an early
incorrect test assumption that tooltip height must exceed the bar height.
Independent placement, not a mandatory larger height, is the relevant boundary.
The initial FloatingWindow offscreen mask warning, unavailable native-popup
measurement and earlier geometry assertions remain in failed private reports;
no warning filter or production workaround was added to make them pass.

Other isolated audio/network/tray/clock regressions passed on the new closed
profile. These results establish prepared code/source/lifecycle contracts,
not the visible correction on the user's monitors.

## Activation and rollback

User approved activation and continued work. Only the verified bar process was
replaced through tools/bar_session.py stop/start, with the session-lifetime grant
and no expiry. Prior sealed stages retain the earlier source state. The current
run is work/bar-session/20261024T170636.340422Z, PID 414781. No Hyprland reload,
logout, active config edit or audio/network/service mutation occurred.
Do not use uwsm stop. After activation, check startup logs, all bar surfaces,
empty-label hover, network/tray hover, fast icon switching, monitor edges and
leaving an element. If an artifact remains, obtain a cropped bar-only screenshot
rather than assuming the original diagnosis covers it.
