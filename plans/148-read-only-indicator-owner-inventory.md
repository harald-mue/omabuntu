# Read-only native indicator capability and owner inventory

## Goal and authority

The user explicitly permits the bounded read-only host inventory requested by
Plan 147. Identify installed candidate programs and existing session owners for
notifications, nightlight and idle behavior before choosing Ubuntu adapters.
Keep Omarchy behavior pinned to ac2690cd7be4f47e4a255f5e2e78d904d436b068;
no upstream import or runtime integration is part of this inventory.

## Evidence and gaps

Source inspection found no admitted native indicator owners. A Wayland Hyprland
session and availability of standard busctl/gdbus/systemctl/dpkg-query/hyprctl
clients were confirmed without invoking desktop changes. Program availability,
running processes and service ownership must remain separate findings: absence
from a finite allowlist does not prove no recorder/remote/inhibitor exists.
Existing server state must not be replaced with an invented inactive status.

## Bounded approach

Use a Python standard-library collector under ignored work/ with explicit process
and output bounds. Query exact package/program candidates. Inspect /proc comm/exe
only for exact allowlisted process names; never argv/environ. Resolve exact D-Bus
names through the already-running bus daemon, with owner identity rechecks; query
properties/introspection only through resolved unique names and do not activate
services. Inspect only exact user-unit metadata (not ExecStart or logs). If needed,
query the compositor's version/global protocol capabilities without collecting
window titles, clients, bindings or output geometry. Store sanitized private
results and distinguish unavailable, unsupported, timeout and partial errors.
Never store raw inventories, notification/reminder bodies, media, addresses,
credentials, unrestricted process/bus/unit lists or configuration contents.

## Safety

No package/source, service start/reload/restart/activation, bus-name claim,
notification or global GNOME preference change, gamma/inhibitor, idle/lock/lid/
suspend, recording/remote access, sudo/security/corporate policy, desktop update,
installed-file mutation, commit or publication. Doctor remains read-only except
private reports. Source planning and private collector/report files are the only
writes. This inventory is not functional/security acceptance or approval for any
later installation, integration, activation or desktop operation.

## Tasks

- [x] Record explicit read-only permission and the finite evidence/privacy scope.
- [x] Collect bounded candidate package/program and exact running-owner evidence.
- [x] Resolve notification/nightlight/idle service ownership without activation.
- [x] Verify probe outcomes and record missing/unknown/race limitations.
- [x] Summarize viable next adapters and their separate approval requirements.

## Inventory outcome and next adapter choices

The inventory identified existing owners suitable for narrow SwayNC DND and
Hyprsunset colour-temperature/identity adapters, without replacing a daemon or
installing another controller. Concrete installed versions, process identities,
unit states, observed values and machine paths remain only in private evidence.
The SwayNC control object's typed GetDnd getter was resolved and invoked through
its already-owned unique bus destination with an owner recheck. Notification
bodies/actions were never requested; no toggle/set/inhibitor method was called.

Hyprsunset v0.4.0 official source/license was reviewed privately before its exact
getters were used. temperature, gamma and identity get are read-only request
branches. Bare identity changes state and profile can request a matrix update;
neither was invoked. Future writes must preserve existing temperature, gamma,
identity and scheduling semantics, not replace them with a hardcoded default.
Observed IPC fields are not per-output visual/colour acceptance or atomic owner
proof for a future setter. Official research bytes/hashes are retained privately,
not imported as runtime source or executed.

The finite inventory did not find a supported running idle owner/recorder. A
residual package configuration is not an installed or running daemon. An inactive
known remote-desktop unit does not prove no other remote access exists. No agent,
remote peer/address, media, notification/reminder body, argv/environ dump or
credential inventory was collected. Reminders still need reviewed storage,
interaction and delivery integration. Stay-awake scope/security interactions,
recording ownership and supported remote providers need separate decisions.
Passwordless sudo remains excluded; no status or mutation helper was invoked.

## Private evidence and limitations

Private sanitized capability and API reports, bounded collector scripts and
verification are under work/indicator-inventory-148/. Root report files use mode
0600 under a 0700 directory. Each child has a five-second deadline and combined
stdout/stderr bound of 64KiB, with stderr discarded rather than logged. API calls
also disable D-Bus auto-start and use unique destinations after owner lookup.
No timed-out or output-bound probe occurred. The exact-package query exited
nonzero because some candidates were absent; returned installed/residual records
were preserved as partial collection, not treated as universal absence.
The transient process scan had no reported race/permission failure, but remains
non-atomic and limited to same-UID allowlisted executables.

The second private script initially lacked its reused function definitions and
stopped before probing; those definitions were added explicitly. Its decimal
parser was corrected and pure-tested; the collected integer gamma response had
already parsed successfully. Existing reports were retained, not overwritten.
No production code, native state, installed file, service, package, session,
security policy, commit or publication was changed. This checkpoint supplies
backend-selection evidence, not native functional/security acceptance or approval
to wire/start/toggle/deploy those backends. Source planning is the only tracked
change; no new disconnected implementation scaffold was added.
