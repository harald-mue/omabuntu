# Isolated real popup lifecycle probe

## Goal and evidence

Attempt a disposable reproduction of network/audio popup switching using the
actual sealed Ubuntu KeyboardPanel, not the lightweight Item fixture. Follow
Plan 164's confirmed kernel fault and static lifecycle findings. Original popup
provenance is Omarchy `ac2690cd7be4f47e4a255f5e2e78d904d436b068` with the existing
Ubuntu derivation. Compare synchronous and queued closure only in disposable
probe copies if the real popup can be constructed under containment.

## Gaps and proposed shape

Existing contained tests replace PanelWindow. First establish whether the real
component can run using the installed software/offscreen diagnostic environment.
Use verified staged runtime and sealed sources, synthetic owners/content and the
existing Bubblewrap boundary. Record unsupported backend behavior as blocked,
not a passing lifecycle test. Do not substitute Item and call it native coverage.

## Safety and exclusions

No host session sockets, buses, network, GPU devices or live provider actions.
No package installation, host compositor startup, desktop change, service,
restart, focus-policy change, implementation fix or commit. Explicitly disposable
probes have bounded timeouts and private evidence under ignored work/.
If offscreen cannot support the actual popup, stop and report the missing
isolated compositor prerequisite rather than connecting to the owner session.

## Tasks

- [x] Verify staged runtime and prepare private, sealed real-component probe.
- [x] Run backend feasibility control and classify backend support.
- [ ] Compare synchronous and queued closure on a supported isolated backend.
- [x] Record results, limitations and next steps; run repository unit tests.

## Result: blocked before popup construction

The sealed staged runtime and all 154 source files verified. A nonvisual
ShellRoot baseline passed within the existing Bubblewrap sandbox (exit 0,
Configuration Loaded and explicit completion marker). The real derived
KeyboardPanel was not replaced or altered. Its construction failed with exit
255: `Type KeyboardPanel unavailable`, caused by `No PanelWindow backend loaded`.
This is the expected missing offscreen backend, not a reproduced segmentation
fault or evidence that popup switching is safe. The synthetic owner/open/close
sequence was never reached, and no audio/network provider was instantiated.
Queued versus synchronous closure therefore remains untested.

Private runner, component copies, exact component hash, logs and report are
under `work/popup-lifecycle-165/`. All 1,640 unit tests pass; their output is
retained there. The disposable runner used a 15-second subprocess limit; it did
not impose a lifetime limit on any live component.

A private Wayland compositor with layer-shell support and isolated outputs is
required for the next stage, including real pointer-event delivery. Weston,
Cage and Labwc were not found during availability checks; Hyprland and GDB are
present, but no additional compositor was started. An isolated headless
Hyprland setup would need separate design/version-documentation review and
approval; no installation or fallback to the owner display was attempted.
No production source, desktop, services, settings or running shell was changed.
