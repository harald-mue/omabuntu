# Complete the original indicator backend scope safely

## Goal and evidence

The user requests the remaining work for all indicators listed under item 1.
Compare the original seven indicator parents and the admitted original reveal UI
from Omarchy v4.5.0 commit ac2690cd7be4f47e4a255f5e2e78d904d436b068,
with existing project services, the pinned Quickshell source and documented lock
readiness. Original MIT licensing/tree/blob evidence is retained privately under
work/research/bar-indicators-145/. Plan 146 installs the UI but instantiates no
indicator. No new original code/assets or dependencies are imported here.

## Current gaps and required distinctions

| Indicator | Native integration needed | Required boundary |
| --- | --- | --- |
| DND | Existing notification-owner identification and a supported status/control API | Never take over the notifications bus or silently change GNOME's global preferences; absence/unknown is not inactive |
| Nightlight | Actual compositor-compatible gamma controller with status/readback and owner identity | A GNOME preference alone does not prove that Hyprland outputs are tinted; controller installation/start needs approval |
| Stay-awake | Explicit inhibitor scope, process/session ownership and release/recovery | Original setIdleEnabled changes idle locking, not just an icon; do not bypass lock, lid, suspend or corporate policy |
| Reminders | Reviewed Ubuntu-native data store, original interaction flow and delivery owner | No Arch helper execution, unapproved notification daemon or unreviewed terminal command; reminder contents are private |
| Recording | Reliable ownership of explicitly supported recorder activity and its stop action | A process name or portal presence does not prove recording; do not start/stop/capture anything implicitly |
| Remote session | Read-only authority for explicitly supported remote-session providers | Never start remote access, collect peer inventories or claim complete detection from a missing process |
| Passwordless sudo | No implementation in this project's current scope | Original widget probes and modifies sudo policy; do not run even its status helper, inspect credentials or alter security configuration |

The pinned Quickshell has notification-server and idle-inhibitor APIs, but using
them would introduce real ownership/behavior changes. No gamma-control API was
found in its source tree. Existing project code supplies none of the seven
native status owners. Read-only source inspection therefore cannot choose safe
live backends or justify fabricating inactive states. An authored placeholder row
would not meet the original-component fidelity requirement.

## Proposed staged shape and approvals

First obtain permission for a narrowly bounded read-only host/session capability
and ownership inventory, with sanitized private reporting under ignored work/.
Do not collect notification bodies, reminder contents, remote peer addresses,
recorded media, environment dumps, authentication state or credentials. Bound
all probes; distinguish unavailable, unsupported, timeout and partial failure.
This inventory itself grants no installation, activation or mutation.

Then specify per-backend contracts against version-appropriate official APIs,
including owner/generation proofs, known/unknown status, actions, readback,
uncertainty/no-replay behavior and recovery. Keep native state service-owned;
use the already admitted original components/layout, not replacement panels.
Any required dependency, service start, desktop change, recording/inhibitor or
session-sensitive behavior needs a named, separate approval and verified backup.
Passwordless-sudo remains excluded under project safety rules. Native indicator
status must not be conflated with complete recording/remote/security detection.

## Safety and explicit exclusions

No native host capability query, installed-path/PID probe, desktop edit,
installation/restart, package/source/service/agent activation, notification-bus
claim, gamma/inhibitor/recording/remote action, security/sudo/PAM/boot/kernel/
corporate-policy change, commit or publication is performed by this source-only
assessment. Preserve existing GNOME, login, user applications and the session.
Normal approved components retain session lifetime, never a silent expiry wrapper.
All current dirty work and unchanged licensed vendor parents are preserved.

## Tasks

- [x] Compare original indicator behavior, current source owners and safety gates.
- [x] Identify all seven backend gaps without inventing live inactive statuses.
- [x] Separate read-only inventory from named native activation/mutation approvals.
- [x] Obtain explicit permission for the bounded read-only host ownership inventory.
- [ ] Collect sanitized, bounded evidence and choose supported native backends.
- [ ] Specify and implement version-reviewed adapters with backups and tests.
- [ ] Integrate only supported known-state indicators into the original registry.
- [ ] Pass units, contained original-UI/backend regressions and clean-source checks.
- [ ] Obtain any named dependency/activation/deployment approvals and verify recovery.
- [ ] Complete owner acceptance without claiming excluded security-policy parity.

## Checkpoint

The user explicitly approved the bounded read-only inventory; Plan 148 records
its completed owner/capability findings and existing SwayNC/Hyprsunset API
candidates. Live-state snapshots remain private and do not grant native action,
activation or deployment approval. Other owners/semantics remain unresolved;
item 1 is not complete. No placeholder interface or disconnected backend
scaffolding was added in place of resolving the native owner decisions.
