# Guarded manual ALSA profile backend

## Goal and evidence

Continue B with a functioning manual profile review/apply/recovery backend, not
an invented profile panel or a catalogue presented as an integrated UI. Keep the
original shell/UI unchanged and the running installation untouched.

Omarchy baseline: v4.5.0 ac2690cd7be4f47e4a255f5e2e78d904d436b068. Re-reviewed
its audio output switch and complete Commons/UntypedInput.qml privately against
pinned tree/blob/size, with the existing full MIT notice preserved. UntypedInput
uses wpctl plus a pactl subscription; that dependency, serialization and lifetime
contract is not silently enabled here. Original audio Panel.qml has no profile
selector and the pinned Quickshell QML API has no profile-switching interface.

Protocol evidence: official PulseAudio v17.0 commit
1f020889c9aa44ea0f63d7222e8c2b62c3f45f68, src/utils/pactl.c and
man/pactl.1.xml.in, including JSON info/cards/profiles and set-card-profile.
pactl.c SHA-256 is
9db452b5071e8018df0afb856d121ff1dc89d72614eaa584a4c14c69c8a28ef2.
The PulseAudio license summary was reviewed privately; no PulseAudio source,
binary or license is imported/shipped. The new Python standard-library adapter
invokes an optional separately supplied Ubuntu pactl executable, not upstream
Omarchy scripts. No package installation is approved.

## Current gaps and proposed shape

Add a closed local PipeWire-Pulse transport and manual ALSA-card backend. Before
connecting, require a normal user, canonical private runtime directory, owned
native socket and one already-running owned pipewire-pulse process holding its
listening FD; bind PID/start-time/executable/socket identity around every command.
Use fixed /usr/bin/pactl, fixed local server, C locale, sanitized environment,
bounded command time/output and no arbitrary command/server/executable overrides.
Python must not open authentication-cookie files or print raw server/device
inventories, stderr, usernames/hostnames or the server's non-authentication magic
cookie. Native libpulse may still use system configuration/authentication;
do not claim a client-library sandbox or a no-credential-read guarantee.
Hash only that server-instance magic for comparison. Missing/stopped/unreadable
services, unsupported schemas and partial collection fail closed for mutations.
These checks reduce, but do not eliminate, socket/daemon races after inspection;
they are not an atomic unique-server binding or a no-activation proof under races.

Admit only local PipeWire-Pulse ALSA cards with name/index/object.serial and
strict profile metadata. Exclude Bluetooth/network/other cards, missing identities,
unknown profile availability and ordinary requests to turn a card off. A read-only
review binds exact normalized current state and target to an approval digest.
Apply requires that digest plus explicit user-audio consent covering concurrent
GNOME/other sessions and input/output interruption. Every connecting CLI operation
also requires separate explicit local-socket-activation-risk consent; the existing
query/write grant alone does not accept that race. Serialize cooperating writers,
recheck fresh state, persist/hash a private before record and prepared receipt
before one native setter, and confirm active-profile readback. No startup write.

Rollback restores only the previous active-profile name, not topology, application
streams/defaults/volume or policy. Require exact identity and expected active
profile; never overwrite drift or choose a substitute profile. Interrupted or
uncertain writes block further changes until explicit recovery. Recovery writes
also get a prepared receipt; there is no automatic retry or compensation. Retain
all backups. Provide an explicit no-native-write acknowledgement for unrecoverable
old identities, labelled unresolved, never restored. Keep latest-first recovery.

## Safety and exclusions

Back up affected existing implementation/documentation paths before edits, with
existence/hash/mode under ignored work/. Preserve previous dirty-tree changes.
Only fake runners/runtime fixtures are executed in this request: no host pactl,
wpctl, audio probes or mutations, installation/restart, packages/sources,
service/agent/radio/trust activation, desktop/security/session changes, privilege,
commit or publication. No unreviewed bin PATH, normal-component expiry, autostart
or supervisor. No new QML/profile menu, packaging/installation route, untyped input
control/subscription, Bluetooth profiles, off action, topology/default/stream
restoration, OSD or A/C/D/E completion. Native protocol, recovery, hotplug, corporate
policy and failure acceptance remain separate deployment/activation gates.

## Tasks

- [x] Diagnose original untyped/profile gaps and official protocol/license evidence.
- [x] Back up affected paths and record prior states.
- [x] Implement bounded local-running-server transport and strict ALSA projection.
- [x] Implement digest-reviewed profile apply, durable receipts and explicit recovery.
- [x] Test command/protocol/context failures, drift, interruption, corruption and CLI gates.
- [x] Document manual-only integration/dependency/safety limits without parity claims.
- [x] Pass complete unit/contained/clean-source regressions and backup verification.
- [x] Record that no native/deployment/activation operation was performed.

## Completed source checkpoint

Added tools/audio_pactl.py and tools/audio_profiles.py, 48 synthetic unit cases
in tests/test_audio_pactl.py and tests/test_audio_profiles.py, and the manual-only
contract in docs/audio-profile-backend.md. Existing audio/status documentation now
distinguishes this backend from still-missing profile UI/native acceptance.
No QML, vendor parent, component map, seal, package payload or installed path was
changed. Existing sealed runtime sources remain the 134-source Plan-139 set.

Private verification: work/guarded-audio-profiles-140/verification.json.
Seven prestate records verified under
work/backups/plan-140-20261122T112547421651Z/; original dirty-tree changes preserved.
Full units: 1,468 passed (48 new), work/plan-140-units-final.log. Contained
regressions: audio 28, frame 24, tray 5, network 7, tooltip 8, clock 5 and desktop
compile passed, reports dated 20261122T114958. Clean-source export passed at
work/clean-source/20261122T115239.755567Z/report.json; whitespace checks passed.

The first clean-source attempt exposed AF_UNIX sun_path limits in the deeply
nested private test copy. The fixture now binds its own socket by a short relative
name inside its private directory; production transport and no-host-bus boundaries
are unchanged. The failed report is retained at
work/clean-source/20261122T114958.677985Z/report.json. An earlier fixture mode was
also corrected to explicit private permissions, rather than weakening the guard.

Tests include post-rename/fsync failure receipt retention, explicit uncertain
recovery without replay/compensation, native/profile drift, UCM argv boundaries,
locked final preflight, backward-wallclock recovery order and malformed/linked
journals. These do not establish native protocol, hardware, hotplug, corporate
policy, power-loss or security acceptance. Profile-name-only recovery is narrower
than restoration of a complete audio graph.

No host pactl/wpctl, audio query/mutation, installed-path/PID probe, installation,
restart, package/source/service/agent/radio/security action, desktop/session change,
commit or publication occurred. The running Plan-135 installation is untouched;
Plans 136–140 remain undeployed. Untyped inputs, profile UI, comprehensive routing,
OSD and remaining A/C/D/E are still open.
