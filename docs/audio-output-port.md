# Audio output port and source fidelity

The first authored output popup was rejected as below Omarchy quality. Reusing
individual buttons and a slider was not sufficient. The current output frontend
is now **derived directly from original audio/Panel.qml**, not independently
laid out. This still is **not the complete original audio panel or shell**.

## Source and rendering boundary

Pinned Omarchy source: 03ff1eff3812933f7088484533784d2f63eaf19a. The original
Model.js, PanelSlider.qml, Panel.qml, KeyboardPanel.qml, PanelKeyCatcher.qml,
CursorSurface.qml, ToggleSwitch.qml, PanelToolTip.qml, PanelSeparator.qml and
PanelSectionHeader.qml were fetched individually from the public repository,
matched against the pinned tree/reference bytes and reviewed before import.
Full MIT notices and per-file Git blobs/hashes remain enforced by
upstream/clock-preview.json. Vendor parents are unchanged.

The deterministic extraction in tools/audio_frontend.py requires unique exact
witnesses and an enforced derived-content hash. The generated frontend mirror
at config/shell/preview/AudioOutputView.qml must match the extraction exactly.
It is not a second editable layout. Tests check these source relationships:

- The complete original hero markup is byte-identical: speaker glyph, title,
  mood/status label, switch, tooltip, original typography and anchors.
- Output section markup/spacing is preserved, adding only drag-target identity
  capture. Device-row markup adds a name check alongside the original ID check.
- Original CursorSurface, ToggleSwitch, section header/separator, slider,
  tooltip and PanelKeyCatcher execute, rather than replacement controls.
- The original adaptive 380px keyboard panel, lazy content and scroll container
  are used. No panel subtree is instantiated until requested/opened.
- Passive style tokens now use upstream defaults for popup padding (14), control
  gap (8), control height (28), row spacing (10), title/display sizes (14/24),
  normal fill (0.04) and selected fill (0.18). This also corrects the shared
  controls. The whole original theme/frame is NOT yet integrated.

The retained source parent includes microphone, streams, helpers, IPC, file
watching, OSD and media-service code. Those parts are **not staged into the
frontend**, not merely hidden. AudioPanelController is the narrow output-only
Ubuntu controller; AudioOutputProvider remains the native PipeWire boundary.
Original Panel/PanelController startup and full registry remain excluded.

## Interaction and explicit deviations

- Left click opens the original output layout. Right click toggles output mute.
- Hero switch mutes/unmutes **output only**, unlike original master mute.
- Wheel adjusts 5 percentage points/notch with accumulated partial deltas.
- Slider and keyboard adjustments are bounded to 0..100 percent and never
  silently unmute. Existing amplified values are displayed honestly.
- Original keyboard signal handling reveals a shared cursor, navigates between
  hero/slider/device rows, adjusts the slider with Left/Right or h/l, activates
  with Enter/Space, mutes with m, and closes with Escape. Device-row horizontal
  movement does not unexpectedly alter global volume.
- Tab stays within this output panel; cross-panel registry switching is absent.
- Device clicks request preferredDefaultAudioSink; display uses actual default,
  not an optimistic selection. The server may reject unavailable devices.
- Graph presence is not jack availability. External availability helpers and
  virtual-to-physical sink resolution are not ported; the server default is
  targeted, including virtual sinks, without bypassing session policy.
- Typed input devices are now staged (plan 001): the upstream input section
  markup (separator, `audio.input` header, input slider, peak meter,
  SourceRow) is extracted with unique witnesses; source selection uses the
  native `Pipewire.preferredDefaultAudioSource`; input volume/mute go through
  `source.audio`; the peak meter is the native `PwNodePeakMonitor`, enabled
  only while the panel is open, exactly like upstream's opened gate. Keyboard
  cursor navigation covers the input section per the upstream section model.
- Untyped (virtual) sources remain excluded: upstream routes them through its
  process wrapper and a default-helper; neither is admitted. All capture
  devices on this machine are typed ALSA nodes (work/audio-input-diagnosis).
- Per-app streams, profiles, media transport and original OSD remain excluded.
  No test sound is played. The hero switch stays output-only in this slice;
  upstream master mute across both channels is a separate review.
  Authored input errors mirror the output ones ("Input device is no longer
  available", "No audio input available").
- Title, output and mute labels use the pinned English catalog strings in the
  passive locale adapter. Mood labels use the same catalog strings. Authored
  errors are "Output device is no longer available" and "No audio output available".
- KeyboardPanel is staged with OnDemand only, **never Exclusive**, and unmaps
  immediately on logical close so a fade-out does not retain focus. Its original
  retained prime timer gates bar click forwarding only, not keyboard ownership.
  Hit testing delegates to the restricted owner, not the full Util singleton.
- The original other-output dismissal surfaces remain; real pointer, focus,
  rapid reopening and cross-output dismissal need interactive acceptance.

No native QObject reaches visual delegates: display rows contain frozen
primitives. Every write resolves the current graph by ID+name and requires a
ready non-stream audio sink. Removed/reused IDs with different names fail.
Dragging retains its starting target. Construction, state publication and popup
opening do not write audio state. This is not a general QML security sandbox.

## Tests and native observation

191 Python contracts pass. Source-fidelity assertions do not claim pixel parity.
Eight actual isolated Qt fixtures cover no-output, glyphs/labels, wheel/mute,
selection, invalid/clamped values, hot-unplug/ID reuse, keyboard/cursor flow,
lazy content construction and the deliberate negative exit 42. They load the
original visual content and controls using fake nodes and a synthetic surface
owner: Qt offscreen has no native PanelWindow backend. Neither a host audio bus
nor native focus/pointer behavior is tested by those fixtures.

The first attempt to instantiate native KeyboardPanel offscreen failed with
"No PanelWindow backend loaded"; the failed report is retained. The fix replaces
only surface ownership in fixture copies. Production staging retains the reviewed
native KeyboardPanel derivation. Earlier unit failures (missing generated mirror
in test copies and outdated source/control expectations) are also retained.

Final reports, all staged-runtime artifacts unchanged:

- work/audio-port/20261024T161209.038468Z/report.json (eight fixtures)
- work/network-port/20261024T161216.270570Z/report.json (seven regressions)
- work/tray-port/20261024T161222.463033Z/report.json (five regressions)
- work/clock-preview/20261024T161226.655311Z/report.json (five regressions)
- work/audio-fidelity-unit-tests-final.log (191 contracts)

Live run: work/bar-session/20261024T161308.276025Z, PID 393392. Configuration
Loaded and no-expiry markers observed, three 26px bar surfaces, configerrors
empty. Only the existing portal app-ID warning remains at startup. This is not
interactive acceptance of the opened native popup.

Private read-only baseline: work/research/audio-fidelity/baseline/. Default
output inspect and get-volume outputs were identical before/after launch.
No audio change, sound playback, service restart or configuration reload was
performed by the assistant. The active Hyprland Lua retains its October 22 mtime.

## Scope and rollback

The native PipeWire API was reviewed at the pinned Quickshell source: the
tracker binds device properties; audio.volume/audio.muted are writable;
preferredDefaultAudioSink is a session-manager hint, defaultAudioSink reports
actual state. No package, helper, daemon configuration or installed file changed.

The prior staged UI is retained at work/bar-session/20261024T154411.383363Z.
Only the verified bar process was replaced through tools/bar_session.py stop/start.
Stop the current UI with tools/bar_session.py stop, never uwsm stop. This leaves
Hyprland, applications, PipeWire and intentional user audio choices running.
The diagnostic baseline is not an automatic audio restore script.

Normal operation remains session-long without expiry; login persistence is still
separately gated. The full bar frame/theme and other panels are unfinished.
