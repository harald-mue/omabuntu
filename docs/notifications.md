# Original notification port and explicit live session

## Status and origin

Plan 173 imports the original Omarchy v4.5.0 notification closure at
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`: Service, Toast, DeedButton and seven
JS modules. Original vendor bytes are unchanged and individually hash-checked;
`upstream/notifications.json` seals the deterministic staged derivation and
adapters. MIT notices include the service's inherited Omapager attribution to
Neil Jagdish Patel. This is not a SwayNC skin or a replacement authored panel.

**Approved live session active (Plan 185).** After the layout correction and
native/host/refusal checks, the owner-approved minimal overlay was installed and
started through GDB. The actual shell owns the notification bus name, original
state/DND readiness and the exact claimed parent are verified, and SwayNC is
stopped behind a runtime-only activation fence. Prior quiet state is preserved.
This is not new autostart, a timed component or crash supervision. Live pixel/
interaction acceptance remains broader work; the owner subsequently confirmed
basic live popup display. No real messages/history or clipboard were collected
and no synthetic notification was sent into the host by the assistant.
See [the session and recovery procedure](notification-live.md).

Plans 174/175's private runtime and ordinary review packages remain inactive
capabilities, not consent. The live role comes only from the separately approved
artifact/session/parent-bound grant. Preparation alone must not interrupt an
existing capture. Native fixture evidence and exclusions remain documented in
[the bounded probe](notification-native-probe.md).

## Retained original source behavior

The original card/deed UI and pure models are staged byte-for-byte: themed
380-scaled-unit width, source decks, hover expansion/body fitting, shared scene
animation, duration/critical rules, bounded hold during reading, explicit keyboard
selection, replacement identity, deferred insertion/dismissal, native sender
actions, verified-code detection/redaction, history and quiet state. The original
per-output surface, input mask, initial focused-output pinning and fullscreen
step-aside code remain in the service derivation. Plan 178 now renders the original
native surfaces on device-free Labwc and exercises real fixture keyboard events.
Plan 179 adds bounded single-output native pointer/hover/input-region and fixture
focus-handoff checks. Hyprland-specific behavior, multi-output input, real external
application focus and broad privacy/security remain unaccepted. No simpler
authored toasts replace them.

The normal shell palette supplies the original notification role defaults:
background, foreground, accent border/countdown. Shared text size, style and
existing border components remain authoritative. Original arbitrary shell.toml
layers, additional custom glyph fonts and unreviewed theme assets are not added.
The existing English label adapter supplies notification strings; full upstream
locale catalogs are outside this slice.

## Narrow Ubuntu adaptations

- State lives under `OMABUNTU_STATE_HOME/notifications` (default private Omabuntu
  state), never Omarchy's directory or the existing SwayNC state. The Python
  `notification_state.py prepare` helper creates only missing private files and
  refuses foreign, public, symlinked, hardlinked, oversized or malformed state.
  It neither chmods nor migrates existing files. Original atomic FileView writes,
  transient exclusions, redaction and bounded history retention remain. No live
  notification-store contents were collected during implementation.
- The server is not constructed until private state preparation succeeds.
- Standard live sender actions and validated window-address routing remain.
  Arbitrary `omarchy-exec-argv`/command hints do **not** gain execution rights.
  The closed action seam admits only `/usr/bin/xdg-open` with one original-policy
  HTTP(S)/mailto URL, via Qt's external URL handler on an explicit action. Unknown
  command buttons refuse without retry; the ambiguous upstream focus-app helper
  fallback is removed. No unreviewed Omarchy bin directory or login shell is used.
  Native launch/focus, clipboard behavior and provider availability need later
  acceptance; code-copy uses the original sensitive clipboard behavior, not a
  newly accepted secrecy guarantee.
- Fixed Quickshell IPC target: `omabuntuNotifications`; no shortcuts are installed.
- One shared `NotificationHost` presents the original owner as the existing DND
  indicator backend after admission. Before migration it passes through the
  already-existing legacy adapter. Once original admission is requested, failure
  stays unknown; it does not silently fall back or start another daemon. Nightlight
  remains independent. Legacy indicator read probes are not a new service owner.

## Exclusive ownership: built and privately tested runtime

The pinned Quickshell notification runtime watches for a competing owner's exit
and automatically retries registration. A prior `GetNameOwner` check alone cannot
close that race, and destroying the QML object does not undo a process-global
server singleton. Therefore a naive Loader or shell-only preflight is not adequate.

`native/notification-exclusive.patch` is pinned to the exact recorded source in
`upstream/notification-runtime.json`. It removes the retry watcher, uses explicit
`DontQueueService` / `DontAllowReplacement`, and fails the process when registration
or the session bus is unavailable. A 500ms connection-health check fails on bus
loss; it is not a lifetime timeout, autostart or crash supervisor.

`build_notification_runtime.py` uses locked cached source, clean compiler objects
and the verified baseline's staged cpptrace inputs in network-free Bubblewrap.
The result lives separately under `work/notification-runtime-builds/`, never in
the ordinary build namespace. Only the Quickshell executable differs from the
baseline stage; the existing stage and installed runtime are unchanged. Known
upstream build diagnostics remain recorded, not suppressed or declared absent.

`check_notification_runtime.py` proved actual native behavior on disposable buses
with no host sockets, display/GPU/input or service-activation directories:

1. Acquire a free name, receive one synthetic native Notify and release on clean exit.
2. Refuse a foreign replacement request while retaining ownership.
3. Fail immediately on conflict, with no queue, replacement or later takeover.
4. Reproduce the original unpatched late-takeover bug as a negative control.
5. Fail closed when the configured bus is missing.
6. Fail closed on bus loss and remain absent after that private bus is recreated.

Build/test receipts and the full stage manifest bind the eligibility receipt to
the exact binary, patch, inputs and checker. `--verify` rechecks them without
starting a server. The original input pin is deliberately not resealed to update
its historical pre-build status string: current machine-local completion lives
in these receipts. This is local integrity/provenance evidence, not a signed
attestation, broad security acceptance or permission to deploy.

The source host defaults both `deploymentApproved` and
`exclusiveRuntimeVerified` to false. Neither appearance settings nor ordinary
manager launches supply a role. An environment path only locates a proof; the
actual child helper must validate the complete artifact/session/parent and claim
it once. Packaging/installing alone never grants ownership. Supplying booleans
manually is not supported. Plan 175 supplies only capability evidence; Plan 185
connects it to the explicitly approved session role and checked transaction.
This is not an adversarial security boundary against arbitrary same-user code.

Activation contract (implemented for the approved Plan 185 session; broader
acceptance exclusions remain):

1. Preserve/reverify the completed build and six native bus checks. Use the bound
   inactive package capability, never a manual boolean, with the reviewed host
   admission path. Plan 185 supplies its separately approved one-use grant.
2. Preserve Plans 178–180's original native card/keyboard/pointer and cross-process
   sender/focus evidence. Extend beyond single-output synthetic fixtures to the
   still-excluded policies and production-application/privacy acceptance.
   Offscreen cannot instantiate PanelWindow; GPU/live-session exposure is not
   a fallback for missing isolated tests.
3. Use the reviewed backed-up migration and recovery path, including current
   owner/unit/autostart/activation metadata, private state and exact former DND
   state. Do not stop SwayNC without separate approval. Avoid races with its
   restart or D-Bus activation. Do not touch GNOME notification ownership.
4. Obtain explicit approval to switch the owned shell/provider and verify there
   is exactly one ready notification owner, or restore the former owner. The
   owner approved this session and its capture coordination in Plan 183; that
   is not an implicit grant for an unrelated future migration.
5. Perform native multi-output, pointer, keyboard, sender action, redaction,
   locked-session/privacy and crash/recovery acceptance. Original shell-owned
   notifications die with the shell; current SwayNC is an independent process.

## Native graphics prerequisite (Plans 176–177)

The [environment preflight and graphics checkpoint](notification-native-preflight.md)
first identified version-reviewed Labwc/wlroots headless + Pixman. After explicit
approval, nine exact hash-verified Ubuntu package files were extracted only under
private work/, without a system installation or package scripts. The isolated
native graphics smoke test now passes with one and two outputs: actual Pixman/SHM,
Qt OpenGL through llvmpipe, native PanelWindow instances and six positive/negative
colorization/masking captures. Namespace, protocol, linkage, guarded activation,
input immutability and child cleanup checks pass. Initial preparation/pixel-
expectation failures are retained privately, not hidden.

This closes the generic native graphics prerequisite, not notification acceptance
by itself. Plan 178 subsequently runs the actual sealed Service/Toast unchanged
on the same isolated graphics path, with a real private NotificationServer/bus.
One/two-output cards, grouping/replacement/expiry, private DND, original photo mask
and symbolic/raw icon effects, native Escape/Return and a standard native action
signal pass. Qt's 2D software adaptation still cannot validate the shader effects.
See [native fixture evidence](notification-native-probe.md) for retained failures
and exclusions. Plan 179 additionally passes a
[single-output native pointer/focus fixture](notification-native-input.md): hover
hold/leave/resumed expiry, grouped expansion, click-through, native card clicks
and exclusive-keyboard handoff to an owned native background window. Plan 180's
[cross-process fixture](notification-native-processes.md) then passes separate
native app focus handoff, persistent sender action/close callbacks, replacement
and sender-exit/later-ID filtering. Standard action signals remain broadcasts;
this is not confidential delivery or production-application acceptance.
Multi-output input, production application actions/focus, Hyprland routing/
fullscreen, privacy and reversible live admission/migration remain separate.
No live provider, installed shell or debug capture is touched.

## Native history checkpoint: passes after reduction (Plans 181 and 184)

The [native history/transience/redaction probe](notification-native-history.md)
uses sealed original cards/layout with a reviewed service derivation, real
private Notify, private-only fixture restarts and synthetic state. Plan 181's
binding-loop failure is reduced to closing code cards. Plan 184 rejects height
feedback from departing or unreserved rows before it can retarget layout during
layout evaluation. Imported upstream files, close ordering and all visual/input
blocks remain unchanged; warnings remain failures.

The unchanged full runner now passes all seven cases, including transient
updates, code sanitisation, restore/replay and retention boundaries. Rendering,
pointer and cross-process native runners also pass with the new staged digest.
Failed controls and unsealed proposals are retained separately from canonical
acceptance. This does not establish live crash causality or supply the still
missing artifact-bound session producer and reversible migration transaction.
The owner has explicitly approved that controlled live migration (Plan 183).
Plan 185 implements the artifact/session/parent-bound admission, minimal overlay
and explicit provider/capture transaction with refusal/recovery tests. See
[the live session procedure](notification-live.md); implementation or isolated
acceptance alone must not be reported as a successful live switch.

## Explicit inactive review package

The ordinary packager still uses its explicit baseline unchanged. Only
`--notification-runtime` selects an already verified exclusive variant, and that
variant must match the selected baseline's exact report and artifacts:

```sh
python3 tools/check_notification_runtime.py --verify \
  --candidate work/notification-runtime-builds/<verified-variant>
python3 tools/package_user.py --version <new-review-version> \
  --build-dir work/builds/<verified-parent> \
  --notification-runtime work/notification-runtime-builds/<verified-variant>
python3 work/user-releases/<new-review-version>/helpers/notification_admission.py \
  --bundle work/user-releases/<new-review-version>
```

This prepares only a local private release under ignored work/. It never installs
or starts it. The package contains the exact patch, source pin/profile and native
build/test/eligibility receipts. Its offline validator checks those hashes and
relationships, the full relocated runtime and original notification source
closure. The only runtime relocation change is the reviewed relative `qs` alias.
Additional runtime artifacts such as an optional Omasnap attachment are excluded
from this exact-manifest review path. Notices still come from the verified
baseline source parent. The descriptor and provenance both state inactivity;
verification returns `runtime_verified: true`, **`deployment_approved: false`**.

The validator does not execute a helper/runtime, inspect any host bus, read user
notification state or acquire a notification name. Normal packages without this
explicit variant selection have no capability descriptor. Changes to evidence,
runtime, sources or verifier invalidate the proof. Exact private receipts can
contain workspace paths: this package is not cleared for publication. The
capability is not a substitute for the release manifest or future migration grant.

## Verification

`python3 -m unittest discover -s tests -v`: 1,704 tests pass at the Plan 175
checkpoint. This covers seals, unchanged original card sources, fail-closed
transforms, inactive admission, state-file safeguards, error-output privacy,
variant refusal and offline package-proof tampering alongside project regressions.
The real inactive review package passes all 469 release-file seals and its own
capability verifier. Contained notification/card, 42 audio, 39 frame, desktop and
five clock checks pass; the nine-check clean-source export excludes private work
and images. No native surface or live provider acceptance is inferred from those
earlier source/model checks. Plan 178's separate native fixture evidence is linked
above; it does not grant live deployment or broader acceptance.

`python3 tools/check_notifications.py --run --build-dir work/builds/<verified>`
runs the original engine and actual Toast against synthetic notification/Hyprland
providers in Bubblewrap with no host bus, display, GPU or input devices. Only the
fixture removes native surface ownership and substitutes the server/IPC boundary.
It checks default inactivity/two-proof gating, DND delegation, original duration,
deferred arrivals/dismissal, replacement updates, deck grouping/hold, original
keyboard release and live sender-action invocation, code DND bypass/redaction,
and actual private state readback. It never invokes a real URL, clipboard or app.
Passing this is not a visual, native-server, exclusive-owner or security verdict.
