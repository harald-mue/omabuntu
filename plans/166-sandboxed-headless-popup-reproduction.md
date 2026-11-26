# Sandboxed headless popup reproduction

## Goal and evidence

Continue Plans 164–165 using a private Wayland compositor so the real derived
KeyboardPanel can be instantiated. Installed Hyprland is 0.57.0 at
`0aa6745f705f2c4b0a5004eb019ef76e5bbdb426`. Review the official example Lua
configuration and hyprtester launcher at that exact commit, plus the official
monitor documentation. Review popup provenance at Omarchy
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`.

## Gap and proposed shape

Offscreen cannot load PanelWindow. First launch the existing Hyprland binary in
Bubblewrap with HYPRLAND_HEADLESS_ONLY, synthetic outputs, software rendering,
private HOME/runtime and no host sockets/devices. If supported, use synthetic
popup owners/content and actual layer-shell popup code to exercise switching,
dismissal and synchronous versus deferred closure with recorded witnesses.
Stop on unsupported renderer/backend requirements; do not weaken containment.

## Safety and exclusions

Owner approved this disposable sandbox compositor, not a second host-session
compositor. No GPU/input device exposure, real session/bus access, packages,
services, desktop edits, reloads, login/session transitions, native network/audio
operations, security policy changes or commits. Bound only disposable tests;
terminate and reap owned probe children. Research and logs remain ignored under
work/. Upstream downloads are private review evidence, not published imports.

## Tasks

- [x] Check installed version and version-matched official source examples.
- [ ] Establish private headless compositor readiness with recorded isolation.
- [ ] Exercise real popup click/lifecycle cases if backend readiness succeeds.
- [ ] Record results and limitations; run repository unit tests.
