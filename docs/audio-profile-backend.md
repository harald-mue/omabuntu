# Manual ALSA profile backend (plan 140, source only)

This is a manual backend, not a new profile panel and not profile parity. It is
not installed, registered in the command menu, imported by QML or added to the
user-release payload. Plans 136–140 remain undeployed; Plan 135 is still the last
verified installation. This request performed no host audio query/change,
installed-path/PID check, package action, restart or service activation.

## Why a separate backend

Pinned Quickshell's QML interface has no device-profile setter. Original Omarchy
v4.5.0 ac2690cd7be4f47e4a255f5e2e78d904d436b068 has output selection, but no
profile selector in its original audio Panel.qml. Its original UntypedInput.qml
uses wpctl and a pactl subscription. Those dependencies, event ownership and
untyped-input behavior are not silently imported or activated here.

The new Python standard-library code uses the optional Ubuntu `/usr/bin/pactl`
executable. The protocol was reviewed against official PulseAudio v17.0 commit
1f020889c9aa44ea0f63d7222e8c2b62c3f45f68, src/utils/pactl.c and
man/pactl.1.xml.in: JSON info/card/profile fields and symbolic set-card-profile.
The source/license research stays private under ignored work/. No PulseAudio
code/binary is copied or linked into this MIT project, and no Omarchy helper is
executed. A missing executable is reported, never installed automatically.

## Closed local transport

`tools/audio_pactl.py` has only info, list cards and set-card-profile requests.
No shell, arbitrary executable/server options, subscription, module loading,
recording, playback, graph/default/volume mutation or management command is
admitted. It requires a normal non-root user, rejects sudo/effective-UID mismatch
and custom PulseAudio endpoint/config/cookie environment overrides. A noncanonical
XDG_RUNTIME_DIR also refuses. The child receives a fixed C locale, PATH and
nonexistent HOME/config home, not inherited loader, PulseAudio or credential
variables. Python does not open authentication-cookie files. Native libpulse may
still use system configuration/authentication internally; it is not a sandbox.

Before connecting, read-only filesystem/proc checks require:

- A canonical non-symlink /run/user/UID directory, owned and mode 0700.
- An owned, non-symlink pulse directory without group/world write, and an owned
  Unix native socket; no TCP, abstract, remote or alternate endpoint fallback.
- One listening stream-socket record and exactly one already-running owned
  pipewire-pulse process holding that kernel socket FD.
- Its executable inode/device must equal the root-owned, non-group/world-writable
  /usr/bin/pipewire-pulse binary. Deleted/replaced binaries refuse.
- Stable PID/start time, executable and socket inode/device/listener identity
  around every command, plus matching local PipeWire-Pulse info before/after
  the card read and immediately before the setter.

Only PID stat/executable/FD ownership metadata is examined, not command lines or
environments. Missing permissions, stopped/unproven services, oversized process
inventories or ambiguous ownership refuse without trying another transport.
The server-instance magic cookie in pactl info is not an authentication-cookie
file; only its SHA-256 fingerprint is retained. Raw native stdout/stderr,
usernames, hostnames, ports and arbitrary properties are not returned or journaled.

These are best-effort observed-identity fences, **not** atomic server binding or a
no-activation proof. A daemon can stop after inspection; connecting to a retained
socket can trigger socket activation before the next guard detects replacement.
Every connecting CLI operation consequently requires separate explicit
`--allow-local-socket-activation-risk` consent, in addition to the query or audio
write grant. Do not approve that risk or run native checks without the separately
required service/native-operation approval. Neither a flag nor this source plan
constitutes approval for the assistant to perform those operations now.

Both stdout (2 MiB) and discarded stderr (64 KiB) are bounded while the child runs.
Each client request has an eight-second deadline and bounded cleanup; only that
child PID may be killed, never a daemon/process group. No automatic retry. This
is a per-action deadline, not a lifetime limit for a desktop component. No live
component, timer subscription, autostart or supervisor is introduced.

## Admitted cards and profiles

Only alsa_card.* entries with device.api=alsa and a positive object.serial are
eligible. Bind index, name, serial, daemon context and server fingerprint. Typed
JSON bounds reject duplicate identities/keys, unknown active profiles, unknown
availability types, missing identities and oversized catalogues. Bounded ASCII
profile identifiers include spaces/parentheses for UCM names, passed as one argv
value. Bluetooth/network/other cards are intentionally excluded, not controlled.
Malformed eligible cards mark the inventory partial and block all mutations.

Normal choices must be present, boolean-available and advertise at least one
sink or source; off is excluded. These counts/booleans do not prove jack/link
health, physical hardware identity, policy acceptance or future availability.
Unsupported/zero-endpoint dynamic profiles and unrecognized schemas fail closed.
No arbitrary first matching card/profile, DSP gain or substitute-device fallback.

## Review, apply and recovery

`tools/audio_profiles.py` implements the manual CLI/API. Its JSON review contains
normalized current state, a target profile, explicit shared-user scope/interruption
notice and a canonical SHA-256 approval digest. It does not mirror service state
into a startup preference. Review/inspect do not create transaction storage;
unchanged apply creates no state either. History only reads existing receipts and
never connects to audio. QML and the running original shell are unchanged.

Apply requires `--apply-user-audio`, a private bounded review file, its exact
`--approve-digest`, and the separate connection-risk consent. A successful review
command's complete JSON envelope is accepted directly as the review file; the raw
review object is also accepted. Keep it owned, non-symlink, single-link and mode
0600. Review again after any observed state/capability/default-card replacement;
never patch a digest to bypass drift. Example interface shapes for a **future,
separately approved** native review (not commands executed in this request):

```text
python3 tools/audio_profiles.py inspect --query-running-user-audio --allow-local-socket-activation-risk
python3 tools/audio_profiles.py review CARD PROFILE --query-running-user-audio --allow-local-socket-activation-risk
python3 tools/audio_profiles.py apply --review-file PRIVATE_REVIEW_JSON --approve-digest REVIEW_SHA256 --apply-user-audio --allow-local-socket-activation-risk
python3 tools/audio_profiles.py restore TRANSACTION --apply-user-audio --allow-local-socket-activation-risk
python3 tools/audio_profiles.py history
python3 tools/audio_profiles.py acknowledge TRANSACTION --acknowledge-unresolved
```

The operator must save the complete review output privately and inspect its
notice/target/digest, not blindly pipe a live inventory into apply. Profile names
with spaces must be quoted by the caller's shell. Applying/restoring can interrupt
inputs, outputs and calls across concurrent GNOME/other sessions for the same user.
No source implementation, existing everyday acceptance or previous deployment
approval grants that new native action.

Cooperating writers use a private nonblocking advisory lock. Apply rechecks the
exact review under the lock and after a prepared receipt. Before one native
setter, it writes/fsyncs private before.json and transaction.json, including hash,
mode, review digest and monotonic receipt sequence, and fsyncs created directory
entries. Journal recovery order uses the sequence, not wallclock timestamps.
Ordinary status success says only profile-observed after active-profile readback;
it is not native functionality, full topology restoration or security acceptance.

A failed/ignored/timed-out/interrupted request remains prepared and blocks later
changes. Failed finalization best-effort retains a pending receipt without native
compensation. Explicit restore handles the latest unclosed transaction first:

- Require the original daemon/server/card identity, never a same-name replacement.
- If the original profile is already observed, finalize without a native write.
- Otherwise require exactly the recorded target active and the prior profile
  still available. Persist restore-prepared before one explicit restore request.
- Other active profiles, changed identities and unavailable original profiles
  refuse; no automatic retry, compensating change or alternative profile.
- A prior off state can be restored from its reviewed backup, but cannot be a
  normal requested off action. All backups are retained after recovery.

Restoration covers **only the prior active-profile name**. PipeWire/WirePlumber
may change topology, defaults, application streams, device nodes or policy as a
consequence; none is restored or claimed unchanged. Other catalogue/availability
changes are not replayed from the backup. There is no native CAS, protection from
unobserved ABA, hostile same-UID writers, or proof that a timed-out server operation
cannot complete later. Recovery is explicit, not a background convergence loop.

An irrecoverable old daemon/device can instead receive an explicit, latest-first,
no-native-write acknowledgement. Its result says unresolved, restored=false,
and preserves the backup/receipt. It does not silently clear uncertainty or claim
rollback. Corrupt/incomplete journals, unexpected files, symlinks, hardlinks, unsafe
modes and broken sequence/hash/review integrity refuse and require separately
reviewed manual recovery; the helper never deletes or repairs them automatically.

## Verification and remaining integration

Tests cover strict protocol/projection, missing commands, bounded streams/timeouts,
private synthetic listener proofs, ownership/identity churn, UCM argv boundaries,
all CLI grants, read-only/no-op state absence, before-write receipts, cooperating
locks, review drift, single requests, interruption/uncertainty, write/fsync failures,
latest-first recovery with backwards wallclock, unavailable/drifted recovery,
corrupt backups/sequences/modes/links and explicit unresolved acknowledgement.
Runners and process metadata are synthetic; short-lived Python subprocess tests
exercise pipe bounds, not host pactl or a real audio service.

No profile UI, installed helper/dependency, native protocol/hardware/hotplug/call
acceptance, untyped-input controls/subscription, Bluetooth profile/agent/radio
policy, comprehensive custom routing, OSD or remaining A/C/D/E completion is
claimed. These need separate implementation, deployment and native approval.
