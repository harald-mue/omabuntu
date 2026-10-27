# Passive geometry contract and sealed original spacer

## Result and limits

The unchanged original spacer and its unchanged BarWidget base now pass **22
contained, non-rendering Item geometry cases** under the staged Ubuntu Qt runtime.
This is the first original QML leaf constructed by the project, not a running
bar, clock, calendar, full shell or desktop trial. No Window/PanelWindow, surface,
scene attachment, original Commons singleton, hardware probe, service, IPC or
helper is created. The production [guard](../config/shell/GuardedHost.qml) and
its empty catalog are unchanged.

The source namespace is deliberately adapted: the original Style implementation
and full module maps are absent. A tiny authored passive compatibility adapter
provides only the base widget's fallback shape. This is not original theme/style
parity, a replacement shell, or permission to enable the stock plugin closure.

## Contract

[PassiveContract.js](../config/shell/PassiveContract.js) accepts only bounded JSON:

```json
{"schema_version":1,"vertical":false,"bar_size":32,"spacer_size":12}
```

- Exact fields/version; vertical must be Boolean.
- bar_size must be an integer from 1 through 256; spacer_size from 0 through 4096.
- Missing/malformed/oversized data, legacy plugins configuration, extra commands,
  wrong types, fractions and out-of-range sizes reject the entire input.
- Input is at most 4096 JS string code units. There are no paths, URLs, QML,
  settings providers, executable callbacks or implicit original defaults.
- Accepted data becomes a frozen primitive-only snapshot. The constructor-owned
  [PassiveBarApi.qml](../config/shell/PassiveBarApi.qml) exposes readonly vertical
  and barSize views. It has no run, shell or moduleWidgets command/dispatch API.

The API's snapshotJson is a trusted constructor-owner input, not an immutable
security boundary or an approved live configuration interface. The snapshot and
public geometry views are readonly, but arbitrary QML or a trusted owner can
still access QObject implementation properties. Do not admit untrusted code on
that basis. Future production configuration changes need explicit revocation or
validated atomic replacement, not unreviewed property mutation.

The caller validates before preparing a spacer component, constructs/validates
the passive API, then supplies bar and validated settings in createObject's
initial property map. That makes the API available before initial bindings run.
No original object is prepared for invalid input/API. The test controller owns
this fixed sequence; the generic production gate is not extended or populated.

A tested rebind replaces the non-null API with a fresh validated API and replaces
the size snapshot before retiring the old API. No temporary null-bar fallback is
introduced. This is geometry evidence only, not full lifecycle/side-effect rollback.

## Sealed source closure and provenance

[spacer-candidate.json](../upstream/spacer-candidate.json) records the exact
profile, source URLs, commit, SHA-256/Git blobs, lengths, unchanged status,
authored-file hashes, module maps, scope and complete notice paths.

Original files from commit 03ff1eff3812933f7088484533784d2f63eaf19a:

| Original source | Bytes | SHA-256 |
|---|---:|---|
| shell/Ui/BarWidget.qml | 2297 | 6dc5f08b92280e323b9bb8645ec530bca9c68512f3af49f6e3d5a13a6d9f99a3 |
| shell/plugins/bar/widgets/Spacer.qml | 293 | 85abd1cd06755e57194b86d30df9c31e7521e5c91f5a663d9cd6420b9e91c545 |

Both files were read completely before import. The leaf only binds geometry;
the base has geometry/settings/broadcast helpers but no startup hook, IO process,
watcher, native service or IPC registration. Broadcast is not invoked or exposed
by this test profile. Its Style fallback is the reason sealing remains necessary.
The absence of risk markers alone was not used as an approval rule.

Each was fetched separately from the pinned public URL, bounded to 64 KiB,
verified against the pinned tree and captured bytes, then copied unchanged into
vendor/omarchy/. No private configuration or installed helper was copied.
The root MIT notice applies, with no additional notice in these two files;
preserve the full [upstream license](../vendor/omarchy/LICENSE), identical to
[licenses/Omarchy-MIT.txt](../licenses/Omarchy-MIT.txt). Other assets/component
licenses and the two supplemental helper origins remain unresolved and excluded.

The probe stages only these original files and these authored inputs:

- PassiveContract.js and PassiveBarApi.qml.
- [PassiveStyle.qml](../config/shell/PassiveStyle.qml), staged as Commons/Style.qml:
  a QtQml-only singleton with bar.sizeHorizontal = 32, no callbacks/probes/IO.
  32 is a diagnostic fallback token, not a claim about original theme dimensions.
- qs.Ui exports only BarWidget; qs.Commons exports only Style. Exact small module
  maps are generated from reviewed constants, never copied wholesale.
- Complete license, an authored root/check timer, fontconfig input and a fixed
  missing-type control file. No original Style, Color, I18n, registry, translation
  data, other UI, plugins, scripts, assets or fonts enter the probe closure.

A constructor tripwire is added **only to the authored Style adapter** in the
private probe. It logs a marker and has no system action. Original file contents
are never instrumented or patched. The record includes the resulting probe hashes.

## Runtime evidence

```sh
python3 tools/check_spacer.py
# Plan only; no files, subprocesses or desktop changes.

# Fixed, contained geometry diagnostics only:
python3 tools/check_spacer.py --run --build-dir work/builds/<timestamp>
```

The runner accepts no external configuration/source/reference/QML/catalog path.
It verifies exact review scope, closed file sets/module maps, source/adaptor
hashes, upstream lengths/Git blobs and both complete licenses before processes.
It reuses build source-lock/stage verification and the established Bubblewrap
isolation: read-only probe/runtime, private HOME/PID/network, no host session,
real buses, GPU, display/compositor or network, 20-second process timeouts and no
less-isolated fallback. Crash suppression is diagnostic-only, not runtime rebuild.
QtQuick Items remain unparented; there is no Window or rendering/visual acceptance.

Final evidence: work/spacer-check/20261024T104040.369578Z/report.json.

Cases cover horizontal/vertical geometry, original default span, zero-size hidden
state, readonly API/frozen snapshot, validated rebind, invalid API/input/type/size
and unknown command fields. Every ordinary case requires exact typed metrics,
exit 0, Configuration Loaded, one success marker, zero Style tripwire hits and
zero WARN/ERROR/FATAL/CRITICAL. No denied case prepares/creates the original leaf.

Controls make missing enforcement observable:

1. **Late injection:** deliberately omit bar during creation, read the geometry
   and only then assign the API. It must hit the authored Style tripwire exactly
   once. Final geometry alone could look correct while startup had already used
   a fallback. This unsafe ordering exists only in this fixed diagnostic control.
2. **Sealed namespace:** compile a fixed InputDevices type reference; require
   the expected missing-type error from the component, without creating it.
   This verifies the stock singleton is not available, not permission to run it.
3. **Wrong geometry assertion:** require exactly exit 42 and its specific expected
   assertion ERROR with no success marker. Crashes, timeout or unrelated errors
   cannot stand in for this control.

The first exploratory run at 20261024T103635.705379Z passed; it remains unchanged.
The final runner additionally rejects Boolean/number substitutions in result
metrics. Reports include commands, exact profile/probe/log hashes, diagnostic
counts, tripwire counts and unchanged probe inputs/stage.

Clock-model regression checks also pass unchanged: four timezone cases with 221
assertions each plus the expected assertion control. Current evidence:
work/clock-model/20261024T104053.295969Z/report.json. The earlier mathematical
reports retain their original metadata hashes and are not rewritten.

At the end of this phase the suite had **143 tests**, including 17 new
provenance, closure, read-only surface, preflight and diagnostic-classifier
contracts. Unit tests never start Qt. Do not confuse these with the 22 actual
geometry processes.

## Backup, rollback and next gate

Only candidate project files, reviewed public sources and ignored private reports
changed. No active Ubuntu path changed, so no active-path backup/desktop rollback
was needed. The reference and staged runtime remain unchanged. No packages,
privileged commands, runtime deployment, host service activation, real reload,
auth/lock/idle/suspend, graphical session trial, logout/reboot/session switch,
commit, remote, upload or publication. Revert only the project additions to drop
this work; earlier package rollback still needs its own reviewed transaction.

Next, define the additional passive font/color/spacing/locale and restricted
host interfaces an original clock label would need. Keep its eager calendar,
IPC, settings persistence and timezone actions out of any initial contained
candidate. Do not extend this narrow Style adapter into an undocumented fake
original toolkit or admit stock clock/bar components using spacer success.
Any graphical trial still needs separate affected-path backups, explicit scope,
compositor/service ownership, recovery/rollback and approval. Full shell,
rendering, original dynamic Color behavior, build warnings and authentication
acceptance remain separate open gates.
