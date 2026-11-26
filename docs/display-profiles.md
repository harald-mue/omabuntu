# Monitor controls and withdrawn profile integration

## Current source boundary (Plan 171; not deployed)

Normal monitor actions now import `display_common.py`, not the profile workflow
or model. It owns the reviewed Hyprland 0.57.0 session/inventory client, private
bounded state I/O, shell text state, shared lock and pending-recovery fence.
The offline profile backend reuses these primitives; its apply/restore/guard
workflow remains separate and available for explicitly reviewed recovery.

Compatibility paths are intentionally unchanged: `display-profiles/control.lock`,
`display-profiles/pending.json` and `current/text-size.txt`. A pending legacy
transaction still blocks normal text/output/scale changes; recovery and normal
controls cannot acquire different locks. Old profile stores/history/backups and
receipts are neither deleted nor migrated.

Normal text changes no longer call profile `overview()` or read saved profiles
and transaction history. They retain the native-session precheck, private durable
previous text bytes/mode, and locked pending-transaction refusal. New previous-text
records live under `desktop-actions/text-<token>.json`; old profile backups stay
where they were. Existing `current/` directory permissions are not rewritten.
Normal status/output geometry, partial monitor commands, last-active-output
protection, bounded observation and before/outcome records remain unchanged.

The unused profile helper environment export is removed.
`DisplayProfilesState.qml` and `DisplayProfilesView.qml` remain sealed offline
sources but are excluded from normal shell staging/packaging. Recovery Python
helpers remain packaged, not started automatically. No profile watcher, migration,
native setter or desktop restart was activated by this source cleanup.

The installed release still contains the earlier Plan 162 correction via Plan
163; the active GDB-supervised shell has not been replaced. Deployment and live
acceptance require separate approval; these changes do not prove crash freedom.

## Installed correction (Plan 162)

The owner rejected the Plan 161 profile interface: duplicate Back navigation,
a permanent technical paragraph and capture refusing an existing layout gap.
The profile page and shared profile/automation owner have been removed from the
normal shell. This is a withdrawal, not a claim that profile capture now accepts
that layout. Named profiles and their review/apply/keep/automation workflow were
Omabuntu-authored extensions, **not original Omarchy monitor-panel behavior**.

The single original-derived popup again exposes brightness, shell-local text
size, runtime scale and direct output rows. An output click or keyboard activation
switches that output, not a navigation page. Last-active-output protection is
retained. A fresh owner/topology observation, shared pending-recovery fence,
private durable before/outcome records and bounded readback guard output changes;
there is no replay or automatic compensation. Existing gaps are not normalized or
rejected by status/output switches. Disabling an output can move windows and
workspaces, as in the original; re-enabling does not promise placement recovery.
An exact connector rule merges existing fields; a new rule may use defaults
rather than inherit a wildcard rule. This is not full configuration rollback.

The text-size slider uses the normal display helper without starting a profile
owner/watcher. Unlike the upstream CLI, it deliberately does not change GTK/GNOME
or application text. Startup, opening and polling remain read-only. Legacy profile
code and private data are retained dormant for recovery/history, not exposed in
the popup or started automatically. No legacy transaction/data is cleared.

Automated checks cover the source-derived surface, contained actual-QML pointer/
keyboard signal paths, text-file creation/readback and fake-native refusal/outcome
cases. They are not physical display, pointer, visual, login, hotplug, recovery
or security acceptance. See Plan 162 and the current project status for deployment
verification; Plans 160–161 below describe the withdrawn implementation.

Plan 162 is now installed locally as
`original-shell-162-20261124T064224.047865Z`: exactly three shell files, the display
helper and provenance changed. All 154 installed shell seals and helper/manifest
bytes match; runtime preflight, 1,640 units, contained original controls, desktop,
audio/frame/tooltip/clock and clean-source checks pass. The owned session-lifetime
bar alone restarted with wallpaper restoration disabled and zero new warnings.
Read-only before/after checks confirm unchanged monitor geometry and text state;
settings, native/audio receipts and dormant profile state are preserved, with no
open update/deployment/display transactions. The installed read-only status works.
Plan 161 remains the verified immediate fallback; Plan 159 is also retained and
verified. No live output/brightness/scale/text setter, profile action or watcher
was run for verification/deployment. Corrected owner visual/native acceptance is
still separate.

## Historical profile contracts and ownership (Plans 160–161)

The original MIT monitor Panel at Omarchy v4.5.0
`ac2690cd7be4f47e4a255f5e2e78d904d436b068` remains the visible parent. Its text-size
surface was restored through a narrow Ubuntu controller; an authored
profile-management page was added to the same popup. That page also redirected
original output switches into profile editing. Plan 162 removes both changes. No new upstream code/assets or dependencies are
imported. Python standard library implements the backend and orchestration.

The runtime gate is Hyprland **0.57.0**, reviewed against pinned source
`efb50993780079460b0cbed1363e2166a2de1d9f`, its VERSION, monitor-rule Lua parser,
monitor report and instance-selection interfaces. Official wiki research is
pinned privately at `8a914cdfce28b332961778816c967467afd76a18` and compared to that
version's source, not blindly treated as an older-version contract:

- [Monitor fields](https://github.com/hyprwm/hyprland-wiki/blob/8a914cdfce28b332961778816c967467afd76a18/content/configuring/core/monitors/_index.md)
- [Modes](https://github.com/hyprwm/hyprland-wiki/blob/8a914cdfce28b332961778816c967467afd76a18/content/configuring/core/monitors/modes.md)
- [Positions/transforms](https://github.com/hyprwm/hyprland-wiki/blob/8a914cdfce28b332961778816c967467afd76a18/content/configuring/core/monitors/positioning.md)
- [hyprctl/eval](https://github.com/hyprwm/hyprland-wiki/blob/8a914cdfce28b332961778816c967467afd76a18/content/configuring/core/advanced-configuration/using-hyprctl.md)

Only generated `hl.monitor` calls for fixed connector strings, advertised numeric
modes, numeric positions/scale/transforms and enabled state are admitted. No
arbitrary Lua, shell, config include, reload, global rule or service command.
Every native call selects the captured instance. Socket ownership, SO_PEERCRED,
pid/start time/inode and version bind the helper to the existing same-user
Hyprland session; GNOME/ambiguous/foreign sessions refuse. Missing commands,
timeouts, failed acknowledgements and incomplete readback are errors, not success.

Hyprland merges a partial rule with an existing exact connector rule. A newly
created connector rule can instead use defaults rather than inherit a wildcard
rule. The UI discloses this limitation; this is not a full monitor-rule ownership
or configuration rollback system. Reported active mirroring, advanced color,
10-bit formats, non-default SDR adjustments and VRR refuse before profile changes.
Unknown wildcard rules and unreported future color policy cannot be proven
preserved. Do not treat geometry recovery as full HDR/VRR/ICC/rule recovery.

## Historical profiles and authored UI

The withdrawn integration instantiated one nonvisual `DisplayProfilesState.qml`
for the helper and optional watcher across outputs. Its `DisplayProfilesView.qml`
used original licensed toolkit controls, but its page/layout/workflow were authored
for Omabuntu, not extracted from Omarchy. It offered:

1. **Capture** a named current layout or select an existing profile.
2. Edit per-output width, height, advertised refresh, scale, X/Y and transform;
   enable/disable is draft-only. Advertised modes are displayed. Set the profile's
   shell text size independently. Editing never changes the desktop.
3. **Save draft** privately, then **Review saved profile**. Unsaved edits cannot
   be reviewed/applied. The review spells out target outputs and text size.
4. **Apply reviewed layout**, then **Keep** only after checking the displays.
   **Restore** is available while a transaction is pending.
5. After Keep, previous transaction layouts remain available as recovery drafts:
   save/review/apply them as fresh operations, not blind old-command replay.

Profiles contain a closed schema, not programs: name, output identities/geometry
and shell text size. A unique make/model/serial may follow a connector rename;
missing serials bind to the connector plus make/model. Duplicate identities,
unknown/disappeared outputs, changed connected sets or unsupported modes refuse.
Serials are advisory physical identity, not cryptographic device authentication.

Validation requires at least one active display, integral logical pixels after
scale/rotation, no overlaps and a connected edge/corner layout with no unreachable
gap. At most sixteen connected outputs and 64 named profiles are admitted. Numeric
scales are 0.5–4; transforms are the documented 0–7. Custom modelines and arbitrary
mode strings refuse. Disabled outputs still need an advertised restorable mode.
The original device row opens reviewed editing rather than directly disabling.
Disabling an output lets Hyprland move its windows/workspaces; restoring geometry
**does not restore window/workspace placement** or rewrite workspace ownership.

## Apply, confirmation and recovery

State is owned/private below `OMABUNTU_STATE_HOME/display-profiles/`; shell-local
text state is `current/text-size.txt`. Files reject symlink/traversing/foreign
paths and bounded malformed state. Plan 161 corrects admission of an existing
owned legacy `current/` directory behind its owned private 0700 state root,
without chmod of existing preferences. Missing ancestor directories are created
privately rather than inheriting public intermediate-directory defaults. An
unprotected state root or symlink/foreign directory still refuses. Profile
changes retain private previous-store
and text existence/bytes/mode snapshots. Mutations share a control lock. The older
runtime scale helper also takes this lock and refuses a pending profile action;
queued scale actions are discarded when the shared profile owner becomes busy.

A review binds the store/profile digest, compositor owner, complete observed
layout, connector binding and text-file prestate. Apply rechecks it under the
lock, journals durable intent **before** writes, and admits enabled outputs before
disabling others. Each step checks prior readback; the final target is observed
before it is presented for confirmation. This is sequential, **not atomic**: a
transient intermediate arrangement is possible. Native peer proof/readback are
not compositor-side compare-and-swap, external-writer exclusion or ABA proof.

An independent recovery child must acknowledge readiness before the first
monitor write. It survives loss of the panel/RPC parent and has the durable
transaction's **25-second** monotonic confirmation deadline. This is an apply
transaction deadline, not expiry of a normal desktop component. After the
boundary it attempts restoration only for the same session/identity/topology
and recorded before/intent/readback states. It waits out the cooperating action
lock, restores geometry and the text file's exact previous bytes/mode/absence,
and records completion. Durable text-write and reverse-write intent cover crashes
between file replacement, readback and journal update.

Keep requires the matching token, unexpired deadline, exact target readback,
unchanged text/store and same owner. Failed/partial writes, lost sessions, changed
identities, unknown geometry or a foreign text edit retain recovery evidence and
refuse blind overwrite. A visible pending transaction blocks new cooperating
writers. **Acknowledge uncertainty** only clears that fence following a human
check; it does not restore, cancel a server operation, replay, prove success or
claim a missing screen has recovered. Native restore can fail: this is not an
unconditional black-screen rescue guarantee. Receipts are not pruned/replayed;
capacity refusal requires explicit private archival, not silent truncation.

## Login and hotplug reapplication

**Use at login/hotplug** is a separate explicit UI opt-in, available only after
this exact saved profile was manually applied and kept. Editing it revokes both
acceptance and automatic selection. Only one automatic profile per exact output
identity set is selected. **Stop automatic** revokes the selection.

The already-approved bar's shared session owner can then start one persistent
watcher when it starts at login or the component becomes enabled. This introduces
no new service, binding, session entry, autostart registration or supervisor.
The watcher has no lifetime timeout. It debounces observed topology changes over
two samples, selects only a unique previously kept exact match, rechecks all
modes/digests/owner proofs, journals recovery and confirms only matching readback.
Absent/new/unknown/ambiguous topologies and pending recovery do not apply a
partial layout. A stable topology is not rewritten repeatedly, so manual/external
layout changes are not fought. Reapplication occurs at startup or an observed
stable topology change, not every scale change or compositor reload. Two-second
polling can miss very short unplug/replug cycles. Unexpected watcher exit is not
automatically crash-restarted; disabling the component stops its session watcher.

## Text sizing scope

The original text-size stops (9, 10, 11, 12, 14, 16, 20 px) now drive watched
shell-local Style tokens without a restart. The default 12-px appearance stays
unchanged. File readback, including first creation/deletion, governs presentation;
a successful helper response reloads the existing watcher instead of asserting
optimistic success. Text is persisted/backed up and included in profile recovery.
This deliberately does **not** call the upstream GTK/global text-scale helper,
change GNOME, terminal/application fonts or claim universal app text sizing.

## Verification and packaging

- **1,624 units**, including 27 focused pure/fake transaction cases: validation,
  stale/edited review, owner/identity changes, durable prewrite guard, failures,
  text bytes/mode/absence restore, deadlines, readback drift, partial prefixes,
  acknowledge-without-replay, automatic acceptance and no override loop.
- **Seven isolated real-process fake-IPC scenarios**: parent death after apply,
  death after a partial prefix, death after text replacement, Keep, explicit
  Restore, external drift refusal and approved startup/hotplug reapplication.
  These execute the real Native/guard/watch code against a private fake socket,
  never the host compositor.
- Actual contained original-popup/profile QML/Process controls: read-only startup,
  draft editing/save/review/apply/keep, explicit automation enable/disable,
  page reset and watched first-create text-size readback.
- Audio/frame/tooltip, original desktop/clock and clean-source regressions pass.
  All **154 sealed shell files**, three display helper modules, manager bytes,
  immutable manifest and runtime preflight are verified in a private source-check
  bundle; the existing Bluetooth production helper is retained.

Private fixtures are sandboxed without host displays, buses, sockets or network.
Automated results are not native login/docking/hotplug, GPU/driver recovery,
physical readability, pixel fidelity or security acceptance. No source checker
runs a live profile action. Installation requires a separately reviewed narrow,
backed-up derivative; every normal/recovery managed-bar start must use
`restore_background=False`. Plan 161 deployment changes thirteen manifested files and verifies all 154
installed seals, exact helpers/manager/updater and retained runtime/assets/menu/
Bluetooth/audio/settings/receipts. Fresh **1,625 units** (28 focused profile cases,
including legacy permissions), seven private fake-IPC scenarios, contained QML
and runtime preflight passed. The installed status RPC passes read-only; no
profile/text state was created, watcher/guard started or geometry changed. Zero
new warnings or unresolved journals; existing permissions preserved. An initial
private prepared candidate was not installed after a test exposed ancestor
permission handling; the verified revised candidate is installed. No live
profile/text change, automatic selection, package/service activation, commit or
publication occurred.
