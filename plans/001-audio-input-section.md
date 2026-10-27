# Audio panel input section (source selection, input volume, input mute)

Status: analysis only. This plan does not approve a bar restart, a release
installation, a Hyprland binding, package installation, or execution of any
Omarchy helper.

## Goal

Extend the derived audio panel with Omarchy's input section: the source device
list with click-to-set-default, the input slider, and input mute, so the panel
offers input source selection like Omarchy at commit
`03ff1eff3812933f7088484533784d2f63eaf19a` (v4.5.0-rc1). The user confirmed
today that only output devices are selectable; the original does have input
selection.

## Evidence compared (pinned upstream vs this project)

All upstream evidence is from the pinned tree under `vendor/omarchy` and the
private snapshot; no upstream code ran.

- Upstream `shell/plugins/panels/audio/Panel.qml` (1363 lines) renders three
  sections: `output`, `input`, `streams` (cursor model near line 214). Our
  derived view is output-only.
- Input section markup: `PanelSeparator`, section header `audio.input` with a
  percent label (shows a dash when the level is unknown), `inputSliderRow`
  (`PanelSlider`, step 0.05, range 0..1, right-click mutes), a peak-meter
  rectangle driven by `inputPeakMonitor.peak` (definition near line 667, not
  yet reviewed), and a `Repeater` of `SourceRow` over `displayAudioSources`
  (rows near lines 1190-1245; click calls `setDefaultSource`).
- Upstream source list: `candidateSources` filters `Pipewire.nodes` by
  `Model.isAudioSource` or `Model.isUntypedSource(n, sourceAvailability)`,
  hides the `quickshell` node and platform-hidden nodes; the default source is
  `Pipewire.defaultAudioSource`, and raw lists fall back to cached lists while
  the panel is closed.
- Upstream `setDefaultSource` (near line 557): typed nodes use the native
  `Pipewire.preferredDefaultAudioSource`; untyped nodes additionally execute
  the helper `omarchy-audio-input-set-default` (an Omarchy execution route).
- Upstream volume/mute: typed sources go through `source.audio.volume/muted`;
  untyped (virtual, e.g. EasyEffects) sources go through the `UntypedInput`
  Commons singleton (152 lines) that shells out to `wpctl` and re-subscribes
  `pactl`, using `Quickshell.Io` processes.
- The upstream hero switch is a master mute across both channels
  (`anyAudible`, `toggleAllMuted`); our derived hero is output-only (documented
  deviation in docs/audio-output-port.md).
- Upstream `Microphone.qml` bar widget also depends on `UntypedInput`; bar
  widget parity is a separate gap, not part of this plan.
- This project: `tools/audio_frontend.py` deliberately cuts the extraction at
  `// ---- Input ----` and at `// Input device row`; `AudioOutputView.qml`
  header states input is not admitted; tests forbid `Process {` and `omarchy-`
  in derived surfaces. `AudioOutputProvider.qml` already uses the native
  PipeWire boundary (`Pipewire.nodes`, `defaultAudioSink`,
  `preferredDefaultAudioSink`), and the pinned Quickshell build
  (2b4501a282689792b62e94f3fb30d8f512324fe6) provides the same API for sources.
- `Model.js` (vendored byte-identically) already contains the needed logic:
  `isAudioSource`, `sourceGlyph`, `nodeLabel`, `rowSnapshot`, `isUntypedSource`.

## Current project gaps

1. No input section in the derived view: no source list, no input slider, no
   input mute, no input keyboard navigation.
2. No source-selection path at all; users cannot pick a microphone from the
   panel.
3. No `UntypedInput` equivalent; virtual sources are unsupported.
4. `docs/audio-output-port.md` and the extraction comments describe input as
   excluded; this plan supersedes that for the typed part.

## Safety constraints

- Diagnose before changing: verify on this machine, read-only, that Quickshell
  types the internal microphone (`PwNode.audio` present, `defaultAudioSource`
  set), and cross-check the source list against a native listing. Record
  findings under `work/`, not in Git plans.
- Never execute `omarchy-audio-input-set-default` or any Omarchy helper.
- No `Process {` in derived panel surfaces (test-enforced). Typed sources only;
  untyped/virtual sources stay a documented exclusion until a separately
  reviewed helper exists.
- The extraction must keep unique witnesses and the derived-content hash
  contract; the generated mirror is not hand-editable.
- The peak meter is included only if `inputPeakMonitor` turns out to be native
  PipeWire; if it shells out, it stays excluded with a comment.
- Hero switch semantics change (output-only to both channels) requires its own
  review against the original markup; default is to keep the current
  output-only hero and document it.
- Release packaging, bar restart, and installation each need explicit approval;
  this plan authorizes none of them.
- English only; no commits without asking.

## Proposed shape

1. Extend `tools/audio_frontend.py` to also extract, with exact witnesses, the
   input `PanelSeparator`, header + percent row, `inputSliderRow` (without the
   peak rectangle if that proves process-based), and the `SourceRow`
   component; the output extraction stays untouched.
2. Extend the controller boundary with: source row snapshot via
   `Model.rowSnapshot` + `isAudioSource`, `defaultAudioSource` display,
   `setDefaultSource` limited to typed nodes (native
   `Pipewire.preferredDefaultAudioSource`), input volume/mute through
   `source.audio`. Untyped rows are not offered.
3. Keyboard: add the `input` section to the shared cursor model exactly as
   upstream (slider row -1, device rows 0..N-1, h/l volume, m/Enter mute),
   reusing the existing key catcher path.
4. Keep the hero output-only in this stage; record the deviation against
   upstream master mute.
5. Update `docs/audio-output-port.md` (scope, remaining exclusions: virtual
   sources via wpctl, peak meter if excluded, streams, OSD, helper route) and
   the WORKLOG.

## Explicit exclusions

- `UntypedInput`/wpctl singleton and virtual-source control.
- The `omarchy-audio-input-set-default` helper route.
- Per-app streams section (separate gap), OSD, IPC, MPRIS, media transport.
- The upstream `Microphone.qml` bar widget.
- Any change to the user's Hyprland configuration; no new bindings.

## Tasks

- [x] Live read-only diagnosis: confirm `Pipewire.defaultAudioSource` and
      `node.audio` typing for this machine's microphone; snapshot the source
      list; store findings under `work/`.
- [x] Review upstream `inputPeakMonitor` (Panel.qml near line 667) and record
      whether it is native PipeWire or process-based; decide peak-meter
      inclusion.
- [x] Extend `tools/audio_frontend.py` extraction with input-section
      witnesses and the enforced derived hash; regenerate the mirror.
- [x] Extend the controller/provider boundary for typed sources (list,
      default, volume, mute) with fixtures; no Process, no helper calls.
- [x] Extend keyboard navigation to the input section per the upstream cursor
      model; keep the hero output-only and documented.
- [x] Add Python tests: extraction mirror equality, controller fixtures,
      forbidden-route checks, upstream `audio.input` label use.
- [x] Update `docs/audio-output-port.md` and `WORKLOG.md`; list remaining
      input deviations (virtual sources, peak meter if excluded, hero scope).
- [ ] Package a release; ask before install and bar restart.
- [ ] User acceptance on a real microphone: select source, slider, mute,
      keyboard path; only then treat input parity as achieved.
