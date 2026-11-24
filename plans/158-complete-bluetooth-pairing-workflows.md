# Complete Bluetooth pairing and asynchronous action workflows

## Goal, evidence and gaps

Implement the remaining C Bluetooth source scope without further design questions:
owned PIN/passkey/confirmation/authorization UI, structured asynchronous action
errors, explicit cancellation, stale identity/owner fencing and bounded recovery.
Compare existing BluetoothActions/Discovery and original licensed Bluetooth
Panel/Model at Omarchy v4.5.0 ac2690cd7be4f47e4a255f5e2e78d904d436b068, pinned
Quickshell 2b4501a282689792b62e94f3fb30d8f512324fe6 and official version-appropriate
BlueZ 5.85 Agent1/Device1/AgentManager1 contracts at
f6f6abf8d5ccf3c4bc42cf578c4ef7ab6c2ec9d9 and Qt 6.10 virtual-object documentation.
Pinned Quickshell exposes pair and
cancelPair but no agent export or structured operation-result signals. Current
pairing depends on another session agent and deadlines cannot distinguish errors.

## Proposed shape and dependency justification

Retain original panel/device layout and narrow adapters. Use Python standard
library for build/test/package orchestration; justify a small QtCore/QtDBus helper
because Python standard library cannot export a BlueZ D-Bus agent and the pinned
runtime already depends on Qt/QtDBus. No new package is installed. The helper must
use a fixed existing system bus, reject service activation/default-agent takeover,
register only its own agent and originate its own Pair calls on that connection.
Expose only bounded closed JSON requests/events with device/adapter/owner/scope/
operation tokens; agent requests must come from the proved BlueZ owner and target
only the locally initiated device. Secrets stay in transient UI/stdin, never argv,
logs, plans or persistent state. UI input is implemented, not requested in chat.

Action RPC and prompt deadlines bound uncertainty, not component lifetime. Handle
all supported Agent1 request/display/cancel/release methods, explicit rejection,
structured method failures, owner/device/adapter loss and late callbacks without
replay or optimistic success. Cancel pairing via its originating connection and
never advance a cancelled generation to connect. Preserve existing typed
observation/discovery ownership and independent paired-device operation. No
automatic trust, reconnection, profile/audio routing, rfkill or policy changes.
Unsupported/security-sensitive profile authorization must refuse rather than
invent approval. All additional policy remains explicitly excluded.

## Safety and verification

Back up affected source paths with existence/hash/mode and retain all unrelated
uncommitted audio work. Research/license review before new upstream imports; do
not import new upstream code when authored closed seams suffice. Native helper
integration is opt-in and source-only: no live Bluetooth probes, agent registration,
pair/connect/disconnect/forget, desktop deployment/restart, package/service,
security-policy, GNOME, bindings/autostart, commit or publication. Component
lifetime is the visible approved session scope, with no expiry/reconnect loop.
Exercise private isolated buses/fake BlueZ and actual original QML with no host
system/session buses, validate production/test-build separation and package seals.
Tests are not native hardware/authentication/corporate/security acceptance.

## Tasks

- [x] Record official contracts, dependency/source/license evidence and source backups.
- [x] Implement bounded owned-agent/action transport and reproducible private builds.
- [x] Integrate original-component prompts, cancellation and structured action state.
- [x] Cover all supported agent methods, stale/loss/error/timeout/cancel flows in isolation.
- [x] Wire source seals, optional packaging and explicit missing-dependency reporting.
- [x] Pass full units and contained Bluetooth/desktop/frame/audio/clean-source checks.
- [x] Document admitted behavior, exclusions and separate deployment/native acceptance.

## Source checkpoint

The authored native bridge, shared session/dialogs and primitive row-generation
proofs are integrated without changing vendor parents or the accepted audio UI.
1,597 units, 22 private-bus native scenarios, seven actual contained QML/Process
cases and desktop/audio/frame/tooltip/clock regressions pass. Production/test
artifacts are distinct; an opt-in source-check bundle verifies all 152 shell
seals, exact production helper bytes and manifest. No host Bluetooth operation,
agent registration, package/service action, desktop deployment/restart, commit
or publication occurred. Native authentication/hardware/security acceptance is
unperformed, not inferred from mocks. See `docs/bluetooth-completion.md` for the
closed supported surface, build instructions and explicit exclusions. Private
source prestate/backups, protocol/QML/build/package and regression evidence stay
under ignored `work/bluetooth-completion-158/`.

The owner's subsequent installation request is fulfilled separately by Plan 159:
a ten-file narrow derivative is installed with a wallpaper-disabled managed-bar
restart and Plan 157 fallback. No agent/native Bluetooth action was started;
source evidence does not become native authentication/security acceptance.
