# Isolated original notification pointer and focus handoff

## Goal and evidence

Extend Plan 178's original Omarchy notification closure at
`ac2690cd7be4f47e4a255f5e2e78d904d436b068` using the verified exclusive
Quickshell `2b4501a282689792b62e94f3fb30d8f512324fe6` runtime and Plan 177's
private Labwc/Pixman/SHM and Qt OpenGL/llvmpipe lab. Compare the unchanged native
surface/input-region code, existing native keyboard evidence, and the installed
private wlrctl/wtype manuals. No upstream code/assets are newly imported.

## Gaps and proposed shape

Plan 178 proves native cards and keyboard-mode changes but not pointer dispatch,
hover lifetime, input-region click-through or actual background key delivery.
Add a separate test root with the sealed original service and an owned native
background window which counts actual pointer/key events. Implement a small
standard-library Wayland virtual-pointer fixture with a persistent connection,
using the existing protocol's registry, absolute motion, button and frame
requests; no devices, dependencies or generated upstream code are required.
Keep all service, card, mask and shader bytes unchanged. First use one output
with verified dimensions; report multi-output pointer policy as excluded.
Exercise empty/outside-deck click-through, actual hover expansion/hold/leave,
original native card click dismissal and keyboard delivery before/during/after
original exclusive keyboard mode. Handler calls are not native input proof.

## Safety and exclusions

No downloads, packages, host sockets/buses/devices, live clipboard/history/DND,
application launch, real user input, installed-release changes, live compositor/
shell/GDB/provider actions, SwayNC stops, security/session changes, commits or
publication. Use only newly owned disposable namespaces and fixed synthetic
notifications. The bus has no activation directories. Bound fixture commands and
lifetime; reap only owned children and preserve failures. Back up existing edited
paths with hashes/modes before changes. No normal component lifetime wrapper,
live admission or automatic provider migration is introduced.

Labwc cannot establish Hyprland focus/output/window/fullscreen behavior. A native
background fixture is not a real application. Locked-session/clipboard/privacy,
broad security/crash acceptance, multi-output input, native scrolling and full
interaction acceptance remain outside this step.

## Tasks

- [x] Verify lab/runtime/source inputs and record before-state.
- [x] Implement persistent private pointer transport and synthetic refusal tests.
- [x] Compose native background event receiver and unchanged original service.
- [x] Execute bounded native pointer/hover/focus cases; preserve exact failures.
- [x] Run full units and clean-source checks and verify unchanged inputs/backups.
- [x] Document bounded acceptance and unresolved gates without live changes.

## Results

The original sealed service/cards/surfaces remain unchanged. Six native checks
pass on one verified output: idle and outside-deck click-through to an owned
fullscreen native window; actual hover hold past low-urgency minimum lifetime,
leave/collapse and resumed automatic expiry; grouped-deck hover expansion;
right-click dismissal without background leakage; native left-click standard
action signal without background leakage; and exclusive-keyboard suppression
followed by real background key delivery after Escape without a refocus click.
The native background window is in the fixture's same Quickshell process, not
a real external application. This does not establish cross-process/Hyprland
focus policy or full native interaction acceptance.

A standard-library persistent Wayland pointer supplies real compositor requests.
The first attempt failed on a skipped client object ID before any input checks;
contiguous ID allocation fixes only the fixture transport. That failed report,
source bytes and compositor logs remain private. No production source, native
handler, input mask or containment setting was weakened. The Plan 178 checker
is unchanged and its exact bootstrap dependency is recorded explicitly.

Fourteen new in-memory wire/guard/fixture tests and all 1,746 unit tests pass.
All nine clean-source export checks pass without original work/lab/runtime inputs.
All four existing document backups verify by hash/mode; final native checker,
pointer and unchanged bootstrap hashes match the successful receipts.
Read-only source/runtime/lab inputs stay unchanged, diagnostic children are reaped
and activation guards remain untriggered. Existing edited documents were backed
up with hashes/modes before changes. Native commands, three synthetic captures,
reference hashes, failure evidence and event counters remain under ignored work/.

No packages/downloads, live input/clipboard/DND/history collection, SwayNC stop,
installed shell/provider selection, live shell/debugger action, session/security
change, commit or publication occurred. Current debugger identity/liveness was
not inspected. Multi-output input, scrolling/dragging/corner precision, real-app
focus/actions, Hyprland policy, locked privacy/security, crash acceptance and
artifact-bound reversible live migration remain separate gates.
