# Cross-process native notification actions and focus

## Goal and compared evidence

Extend Plans 178–179 using the unchanged sealed original Omarchy notification
closure at `ac2690cd7be4f47e4a255f5e2e78d904d436b068` and verified exclusive
Quickshell `2b4501a282689792b62e94f3fb30d8f512324fe6` runtime. Compare existing
single-process native input evidence, original sender-action/lifecycle handling,
and the pinned FloatingWindow API and private-bus fixtures already in the project.

## Current gaps and proposed shape

The background receiver currently shares the notification process, and a generic
bus observer is not a persistent notification sender receiving its own callback.
Compose separate native service and application roots/processes, retaining all
notification surface/card/input bytes. Add a small synthetic QtDBus sender that
maintains the actual Notify connection, validates action IDs and reports callback
counters. Existing QtDBus/compiler tools are justified test-only dependencies:
Python standard library remains the orchestrator; no Python D-Bus dependency,
download or package installation is introduced. Compile the authored fixture only
inside the disposable namespace and keep its binary/build logs under private work/.

Test native pointer actions with the persistent sender; original exclusive
keyboard suppression and Escape handoff to the separate application; and sender
exit while a card is pending. Verify real process/bus identities and refuse broad
claims about real production applications, routing or security.

## Safety and exclusions

No host socket/bus/device mounts, real notifications/history/clipboard, live DND,
application launches outside the owned test namespace, installed release/provider
changes, SwayNC stop, shell/GDB action, session/security changes, downloads,
packages, commit or publication. Reuse the verified private lab/runtime, disabled
activation and bounded diagnostics. Back up edited existing project paths with
hashes/modes. Preserve failures, synthetic captures and owned child cleanup.

One Labwc output only. Hyprland routing/fullscreen/focus policy, multi-output input,
clipboard/locked-session privacy, arbitrary sender behavior, crash causality,
artifact-bound host admission and reversible live migration remain excluded.
No normal component receives a timed lifetime or automatic admission.

## Tasks

- [x] Reverify lab/runtime/source and inspect available test-only compiler/API.
- [x] Implement separate application/service roots and persistent synthetic sender.
- [x] Execute actual cross-process native action/focus/sender-exit cases.
- [x] Add synthetic refusal/regression tests and run full units/source checks.
- [x] Verify backups/inputs, document bounded results and remaining acceptance gates.

## Results and limits

The unchanged original service runs independently from a fullscreen native app
and persistent authored QtDBus sender. Four native cases pass: same-sender
replacement/native action/close callbacks, cross-process exclusive-keyboard
suppression and Escape handoff without refocus, sender disconnect/orphan card
activation with later-client ID filtering, and fresh later-sender own callbacks.
Private bus PID/unique-owner checks distinguish the real actors. Sender status
counters prove own callback counts; all actions/input travel through real native
interfaces rather than direct original handler calls.

Standard action signals are broadcasts. The later fixture observes the orphan ID
and explicitly ignores it: this is client callback attribution, not daemon
confidentiality, unicast routing or adversarial isolation. Both app and sender are
synthetic, not accepted production applications; Hyprland routing is not faked.
The source/runtime/lab remain unchanged and owned children are reaped.

Existing Qt6Core/Qt6DBus 6.10.2, compiler and moc are present and the helper compiles
only inside the disposable namespace. Binary/build logs/commands, callback event
metadata, process identities, final capture and exact fixture/source hashes stay
private. The first run passed action/focus cases but the test-side Python literal
decoder rejected D-Bus lowercase false after sender exit. An exact bounded boolean
response decoder fixes that fixture error; no production or containment changes.
Failed source/logs/results remain preserved.

Thirteen new synthetic regressions and all 1,759 unit tests pass, as do all nine
clean-source checks without original lab/runtime/work inputs. Four existing
backups verify by hash/mode. Final checker/sender/pointer/bootstrap/staged-driver
and compiled-binary hashes match the successful private receipt; native callback
status counters and real process identities verify. Existing edited documents
were backed up before changes. No dependency installation, download, live app/notification/clipboard/DND access, provider/release/
SwayNC/shell/GDB action, session/security change, commit or publication occurred.
Current debugger identity/liveness was not inspected. Privacy/security, real
production apps/Hyprland/multi-output input and reversible artifact-bound host
admission/migration remain separate approval and acceptance gates.
