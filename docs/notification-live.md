# Explicit original-notification live session

## Scope and approval

Plans 183/185 record the owner's explicit live-test approval, including a controlled
SwayNC stop and shell/GDB restart with recovery. Source/native acceptance is not
itself deployment consent. The switch is a manual session transaction, not
installation of a service, autostart or crash supervision. It adds no normal
component timeout. No package sources, privileged actions, locks or corporate
management settings are involved.

The source remains original Omarchy cards, decks, shaders and input handlers.
Only reviewed Ubuntu backend/state/action/readiness adaptations and Plan 184's
height-feedback guard differ. Native synthetic tests do not prove production
application behavior, Hyprland policy, locked/clipboard privacy, broad adversarial
security or the cause of the separate live crashes.

## Admission

`notification_session.py` issues a private, one-use proof binding the complete
release/capability digests, exact shell argv, boot/compositor socket/session and
nonce. The real shell's child helper validates it and atomically claims it for
that parent's PID/start identity. Ordinary manager launches provide no proof and
leave both host admission flags false. An environment path only locates the
proof; it does not bypass validation. A second consumption, changed artifact,
wrong session, wrong parent or unsafe file is refused without retries/queueing.
This is local integrity/consent routing, not authentication against arbitrary
same-user code.

The server waits for validated live/history/quiet loading before registration.
The metadata-only `omabuntuNotificationRole status` IPC returns admission,
readiness and DND, never notifications or history. Failed admission exits the
shell; it never starts a competing provider.

## Minimal overlay and preservation

`notification_deployment.prepare` starts from the verified installed release,
not all pending development changes. It imports the exact verified notification
closure, required shared palette/translations and host/DND integration. It
refuses unknown baseline/runtime/UI witnesses and unrelated deltas. Existing
audio, microphone, DSP, monitor/profile, fonts, assets and normal shell settings
remain from the base.

The already installed screenshot binary moves from `runtime/bin/omasnap` to
`helpers/omasnap`, with only the two corresponding manager path literals adapted.
Its hash is preserved. This keeps the notification runtime exactly equal to the
private-bus-tested artifact without unreviewed runtime attachments. All deltas,
base/review hashes, third-party notices and complete release seals are retained.
The prepared artifact remains inactive until separately granted for the session.

## Transaction and recovery

`notification_live.py` defaults to plan-only. Explicit `--apply` takes the normal
control lock and rechecks exact base/capture/SwayNC identities, systemd-backed
D-Bus activation, native/checker/source/helper evidence and immutable artifact
integrity. It backs up selectors/launcher, running/log/capture records and prior
quiet metadata privately, preserving hashes/modes.

The ordered operation is:

1. Stop only the exact owned shell, allowing its current debugger to finish.
2. Establish a runtime-only SwayNC user-unit mask, then stop its exact unit owner.
3. Install/select the verified minimal overlay, preserve prior DND, issue a fresh
   session grant and start the shell through the reviewed GDB capture adapter.
4. Verify the actual bus owner PID, claimed parent identity, original store/quiet
   readiness, DND and real GDB/supervisor ownership before claiming success.

The short owner-free transition is not atomic delivery: requests in that gap may
fail. No queue, replacement or hidden competing fallback is allowed. The previous
DND state is preserved, so an already quiet desktop remains quiet during the test.
No synthetic notification is sent into the live session by verification.

A startup/verification failure runs explicit sequential recovery: stop only the
owned attempt, revoke its proof, restore permitted selectors/launcher and prior
quiet/activation state, restore SwayNC only when no unknown provider competes,
then restore the previous shell under a fresh GDB capture. Unknown ownership,
external edits or damaged backups cause refusal rather than arbitrary overwrites
or kills. Recovery failures are surfaced and journals retained, not reported as
success. No automatic recovery loop continues after the command exits.

```sh
python3 -B tools/notification_live.py --bundle work/user-releases/<overlay>
python3 -B tools/notification_live.py --bundle work/user-releases/<overlay> --apply
# Explicitly restore the pre-test provider/release/capture:
python3 -B tools/notification_live.py --bundle work/user-releases/<overlay> \
  --recover ~/.local/state/omabuntu/notification-migrations/<transaction> --apply
```

The runtime mask lasts for this login session or explicit recovery; it does not
disable the previous enabled unit persistently. No notification autostart is
added. The grant is one-use and session-bound: manually restarting a notification
release without this explicit producer is not a supported substitute. Use the
recorded recovery command to end the test, especially after an independent shell
failure; there is intentionally no racing provider fallback.

## Verification

Synthetic units cover grant bindings/unsafe files/one-use refusal, transaction
ordering and every injected mutation failure, recovery failure visibility,
external edits/unknown ownership, preserved frozen modes and evidence tampering.
A real isolated native host test exercises the actual helper/host/server parent,
original card ingestion and duplicate/session/artifact refusals. The fixture
root is explicitly not production TrialShell; full-shell startup and actual
owner/DND/capture are separate live checks. Canonical original rendering on one/
two outputs, pointer, cross-process and full-history runners remain strict gates.
All lab children are owned/reaped and immutable inputs checked. Reports, failure
attempts, synthetic captures and backups stay only under ignored work/private
state. No commit or publication is implied.
