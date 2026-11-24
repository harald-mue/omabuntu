# Owned Bluetooth pairing and action completion

Plan 158 completes the admitted C **source** integration. The owner-approved
Plan 159 now installs its narrow derivative and restarts only the managed bar,
with session lifetime and wallpaper restoration disabled. Plan 157 is the
verified immediate fallback. No agent was started/registered by deployment;
activation still requires an explicit UI device action. Hardware
pairing/authentication, keyboard/pointer input,
real error/hotplug behavior, corporate and security acceptance remain unverified.
Existing owner acceptance of everyday Bluetooth controls is not acceptance of
this new agent. Source completion, packaging, deployment and native acceptance
are separate checkpoints.

## Evidence, source ownership and dependencies

Retain the MIT original Bluetooth Panel/Model at Omarchy v4.5.0
`ac2690cd7be4f47e4a255f5e2e78d904d436b068` and Quickshell
`2b4501a282689792b62e94f3fb30d8f512324fe6`. No new upstream code/assets are
imported. The agent, protocol, build tooling and fixtures are authored project
code under the project MIT license. Contract research compared official BlueZ
5.85, tag commit `f6f6abf8d5ccf3c4bc42cf578c4ef7ab6c2ec9d9`:

- [Agent1](https://github.com/bluez/bluez/blob/5.85/doc/org.bluez.Agent.rst)
- [AgentManager1](https://github.com/bluez/bluez/blob/5.85/doc/org.bluez.AgentManager.rst)
- [Device1](https://github.com/bluez/bluez/blob/5.85/doc/org.bluez.Device.rst)
- [Qt 6.10 QDBusVirtualObject](https://doc.qt.io/qt-6.10/qdbusvirtualobject.html)

Python standard library orchestrates builds, packaging and isolated tests. A
small native QtCore/QtDBus helper is justified because the standard library
cannot export Agent1 and pinned Quickshell has no owned-agent or structured
operation-result API. It dynamically uses existing Qt 6.10 libraries; no new
package source, dependency installation, privileged action or service activation
is performed. A missing compiler/development metadata/helper reports unavailable
or timed out and never installs a fallback.

## Original surface and shared owner

`BluetoothPanelController.qml` and `BluetoothControlView.qml` remain strict
extractions from the pinned original panel. Original grouping, sections, device
rows, discovery lease, radio controls and toolkit/navigation remain. Authored
`BluetoothPairingPrompt.qml` adds original Button/TextField/Divider controls only
while an operation needs authentication, cancellation or uncertainty handling.
One nonvisual `BluetoothSession.qml` is shared across outputs. Another panel
cannot start a concurrent action or turn off/change the managed adapter during
an owned operation. Ordinary panel closure cancels its outstanding prompt; merely
opening the panel never starts an agent.

Primitive device rows carry output-local owner/generation/path/adapter proofs;
a live wrapper is never placed in delegate model data. Stale rows cannot resolve
a newly created same-address/path wrapper or another output's owner. The session
then captures the actual current device/adapter objects and a fresh operation
and process scope. Replacement, disappearance, adapter power-off, owner loss,
process loss, invalid frames and deadlines cannot retarget or replay that action.
This is not server-side compare-and-swap, a physical peer identity guarantee or
proof against every external-writer/same-path ABA race.

## Native protocol and admitted operations

The helper requires explicit owned-agent/system-bus-risk grants and a bounded
scope argument. Production admits only the fixed existing system-bus socket,
checks root peer/BlueZ ownership and disables D-Bus service autostart. It registers
only its own `KeyboardDisplay` agent, never requests default-agent ownership,
and originates Pair on the same connection so BlueZ uses that application agent.
Only callbacks from the captured BlueZ owner for the captured device are admitted.
Unknown callers, signatures, interfaces, devices, scopes, replayed tokens and
extra request keys refuse. No generic D-Bus, argv, shell or profile method exists.

| Operation / callback | Behavior |
| --- | --- |
| Connect an unpaired/unbonded device | One owned Pair; one Connect only after successful reply and proved paired readback |
| Connect paired/bonded, disconnect | One method with current identity/state proofs and result/property readback |
| Forget | One explicit RemoveDevice and absent-object readback; no automatic disconnect/re-pair/compensation |
| RequestPinCode / RequestPasskey | Transient masked original input, bounded PIN or six decimal digits; invalid input stays local; input cleared on submit/change/close |
| RequestConfirmation | Show the supplied six-digit code and device name/address; explicit Confirm or Reject; initial focus is Reject |
| RequestAuthorization | Explicit Allow/Reject for the current locally initiated device only |
| AuthorizeService | Explicit decision only for fixed audio/HID services; unknown/network/file-transfer services refuse |
| DisplayPinCode / DisplayPasskey | Plain-text supplied code, entered-digit progress for passkey; no answer or automatic confirmation |
| Cancel / Release | Clear transient prompt; own cancellation or agent release cannot advance to Connect |
| Error / timeout / owner loss | Structured sanitized error, confirmed cancellation or explicit uncertainty; never optimistic success |

The service UUID allowlist is limited to audio/headset/AVRCP services
`1108, 110a, 110b, 110c, 110e, 110f, 1112, 111e, 111f` and classic/HOGP HID
`1124, 1812` in the Bluetooth base UUID. No authorization creates persistent trust.
Dialog values stay in transient UI/stdin/D-Bus messages, never command-line
arguments, reports, persistent project state or application logs. Fixtures use
fixed synthetic values and export only status/counters, not prompt values.

Actions, input, buffers, tokens and prompts are bounded. Prompt/action/startup
watchdogs bound an individual RPC or uncertain outcome; they do not expire an
idle component. The helper remains for the enabled explicit session scope,
without timed lifetime, autostart, supervision or automatic reconnect. Cancel
uses the originating connection and never cancels an unrelated device. Dropping
the connection releases only its own registration; an unconfirmed in-flight
outcome is retained as uncertain. Acknowledgement only lifts the local fence
following a human state check: it is not restoration, success, cancellation or
an automatic retry. New actions always require fresh user intent/proofs.

When the helper is absent, existing already-paired typed controls and discovery
remain available, with their older bounded observations rather than invented
structured errors. New unpaired pairing refuses with a visible missing-helper
message instead of silently delegating authentication to an unknown agent.

## Private build and opt-in packaging

These are source preparation commands, not installation or desktop activation:

```sh
python3 -B tools/build_bluetooth_agent.py --output work/bluetooth-build/bluetooth-agent
python3 -B tools/package_user.py --version bluetooth-source-check \
  --build-dir work/builds/REVIEWED-RUNTIME \
  --bluetooth-build work/bluetooth-build/bluetooth-agent
```

Use a fresh output path. Production/test builds are distinct; packaging checks
native-source and binary hashes, metadata and absence of test-bus capabilities.
The optional executable is manifested at `helpers/bluetooth-agent`, with source/
binary/Qt provenance. The manager exports its absolute path only for a bundled
regular executable, using its existing closed child environment. No external
helper is inherited. Package verification is integrity/provenance evidence, not
independent cryptographic attestation of a compiler or functional/security proof.

The source-check bundle was verified for all **152 sealed shell files**, exact
production helper bytes and immutable manifest. Its sandboxed production
`--contract` reports no test bus; production rejects the test-bus argument, and
the test artifact is rejected by the packager. The generic source-check bundle
itself is not installed: Plan 159 installs a ten-file narrow derivative of the
existing release. All 152 installed seals/helper bytes/manifest match; settings,
native/audio receipts, runtime/assets/menu/unrelated helpers are preserved.
The managed bar is healthy with zero new warnings or unresolved journals; no
Bluetooth helper process was started. Deployment preserves unrelated state and
backups; any future deployment must likewise preserve state and create
backups and use the existing drift-guarded narrow manifest update. Any approved
managed-bar start, including recovery, must use `restore_background=False`.

## Verification and remaining acceptance

- **1,597 unit tests**: source/function contracts, stale scope/row/recreated-object
  refusal, duplicate and hidden actions, acknowledgement without replay,
  build separation, seals and package/manager gates.
- **22 isolated native scenarios**: PIN/passkey/confirmation/authorization/service,
  both displays/progress, daemon cancellation/release, reject/invalid input,
  explicit cancel, prompt/action deadlines, method failure, owner loss, wrong
  device/caller/signature, unsupported service, connect/disconnect/forget.
- **Seven actual contained QML/Process/prompt scenarios**: PIN submit/clearing,
  confirmation, display-only progress, reject, cancel, uncertainty acknowledgement,
  device disappearance; no startup/open agent, duplicate operation or stale scope.
- Original desktop checks, **43 audio**, **39 frame**, **8 tooltip**, clock and
  clean-source regressions pass without warnings admitted as successes.

All native scenarios use an isolated private bus/fake BlueZ in a filesystem and
network namespace with no host buses, devices or live agent registration. QML
uses the actual source components and a synthetic stdio helper, not hardware.
No offscreen test proves native keyboard/pointer behavior, pixels, real radio
pairing, authenticated peer identity, calls, hotplug, security or corporate fit.
Plan 159 deployment is complete. Owner-operated native authentication/device
and visual/input/security acceptance remain separate, unperformed gates.

## Explicit exclusions (not unfinished implicit promises)

No incoming unsolicited/default-agent takeover; incoming requests remain with
the existing system/session owner. No automatic trust/Trusted writes, persistent
rfkill/radio retention, auto-reconnect or connection/profile policy, audio-default
routing, ConnectProfile/DisconnectProfile, PAN/tethering/file-transfer approval,
service/package activation, daemon restart, permission/security-policy changes,
GNOME changes, credentials in chat/logs, new bindings/autostart, topology rollback,
commit, publication or claimed hardware/security acceptance. Native BlueZ is the
authoritative state owner; the helper never snapshots key material or rewrites
BlueZ storage. No new policy is required to implement the admitted C workflows.
