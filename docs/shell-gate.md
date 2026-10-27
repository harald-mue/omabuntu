# Source provenance and fail-closed loading prototype

## Status and authorization

The user approved pinning original sources/licenses and preparing a tested,
positive loading policy. This phase changes project code/documentation only and
runs fixed authored nonvisual fixtures in the existing isolated staged runtime.
It does not approve a graphical trial, install a custom runtime, activate a
service, or run any original shell/helper/plugin/authentication code.

**This is not an integrated or desktop-ready original shell.** The shipped
catalog is empty. The original shell remains unchanged and must not be launched
as a way to try this prototype; its existing startup paths bypass this new host.

## Original source and license pin

[Source metadata](../upstream/omarchy-source.json) pins:

- Repository: https://github.com/omacom/omarchy
- Observed tag: v4.5.0-rc1 (not used as a mutable runtime/build input).
- Commit: 03ff1eff3812933f7088484533784d2f63eaf19a.
- All **249 captured shell regular files** match the pinned recursive Git tree
  by Git blob hashes of their actual bytes. The private comparison records
  SHA-256 as well; the tree response is non-truncated.
- **536 of 538 helper entries** match. omarchy-nvim-setup and the passive
  omarchy-nvim-refresh alias are absent from that tree; their supplemental or
  packaging origin remains unresolved. They are not approved for import/use.
- The complete upstream MIT notice is retained unchanged in
  [licenses/Omarchy-MIT.txt](../licenses/Omarchy-MIT.txt), SHA-256
  717ba1949502290f8e47688ae2e323acd06c8ca47aec9f7596b15f678c1af4a2.

This is source-content evidence via HTTPS, not signed attestation or an original
binary/package rebuild. A bounded search of 20 historical default-branch package
recipes did not match the captured Omarchy PKGBUILD hash; do not confuse this
with the separately established exact Quickshell recipe. The source and capture
both contain the literal version file 4.0.0.alpha despite the RC package/tag.
The package label/version file alone was therefore not used as source proof.

A full-source archive exceeded a conservative 64 MiB response bound. It was not
saved or extracted; research switched to bounded Git tree metadata and pinned
license/version blobs. No recipe, installer, source program or patch was run.
Research remains private under work/research/omarchy-source/.

### MIT is not blanket asset/component clearance

No original runtime code, icons, fonts, themes or datasets are imported into
public candidate files in this phase; the license notice is the only imported
upstream document. The source scan identified additional review obligations:

- notifications/Service.qml explicitly credits Omapager, Copyright (c) 2026 Neil
  Jagdish Patel, under MIT. Preserve this attribution and establish the complete
  component notice/revision evidence before importing that code.
- The Elsewhen manifest names Jason Fried as author and declares MIT. Keep that
  metadata and review applicable notices before importing the panel.
- Six branded SVGs under plugins/agents/assets/ have unresolved individual asset
  provenance/permissions and possible trademark implications.
- Emoji dataset provenance and external Nerd Font/font notices are separate
  obligations. No font package or font file is introduced by this work.

Original project work remains MIT under the project [license](../LICENSE).
Third-party copyright is not reassigned to Omabuntu.

## What the prototype enforces

[GuardedHost.qml](../config/shell/GuardedHost.qml) is a nonvisual QtObject. It
imports only QtQml and our [LoadPolicy.js](../config/shell/LoadPolicy.js).
There is no registry, plugin discovery, shell IPC, shared hardware/background
startup, command runner, theme hook, file watcher, timer or fallback shell in it.
Only the synthetic test harness imports Quickshell and uses a bounded check timer.

The only accepted configuration shape is:

```json
{"schema_version": 1, "components": []}
```

The components list contains IDs only, never URLs, QML, commands or catalog data.
The trusted host catalog defaults to {} and cannot be populated by this JSON.
Configuration is bounded to 65,536 JavaScript string code units and 16 IDs;
malformed/wrong-version/unknown-field configurations, unknown/protected/duplicate
IDs and invalid catalogs reject the **entire** plan before Qt.createComponent.
An empty list is inert. Legacy plugins: [] is rejected, never a request to load
the original defaults.

Trusted catalog records are restricted to bar/widget entries, no declared
capabilities, and local .qml URLs beneath the isolated /probe/components/ mount.
The ten first-party service IDs are explicitly denied even if mislabeled as a
widget. Remote/outside/traversal URLs are rejected. This path restriction is
intentional: this prototype cannot be used as a production original-widget host
without another reviewed integration change.

The complete plan snapshots validated URLs before creation; in-place catalog
mutation during construction cannot redirect a later entry. Only after complete
validation does the host synchronously prepare and construct each fixture. A
preparation/object failure revokes all handles already created by that attempt.
Reentrant revocation stops further construction, including after a creation
callback. The isolated tests observe actual constructor completion and teardown,
not only import/type registration.

### Reload and fallback fail closed

- No configuration, invalid configuration and unsupported original configuration
  load no components. There is no inherited default or discovery fallback.
- A changed configuration, replaced trusted catalog, explicit reload or repeated
  start revokes approval and clears owned handles.
- Revocation is **sticky for this host instance**: later valid configuration and
  start calls cannot reactivate it. A fresh independently reviewed host instance
  would be required; no process/host restart is performed automatically.
- This deliberately trades hot-reload availability for safety. Qt destruction is
  deferred; the prototype never creates replacement objects in the revoked
  instance while old objects may still be tearing down.
- In-place catalog changes are not a revocation API. Use explicit revocation or
  atomic catalog replacement. The current attempt uses its immutable URL snapshot.

### What it does not enforce

A declared empty capabilities array is a review assertion, **not** a C++/QML
privilege sandbox. IDs can be renamed and trusted QML can execute arbitrary code;
this host cannot make malicious or insufficiently reviewed QML safe. URLs/code
and their complete dependencies must be reviewed before admission. Source hashes
for a future real-widget closure must be verified at staging; this policy does
not itself hash QML files or approve their contents.

The runner copies only our fixed authored fixture sources into a read-only
sandbox mount and records their hashes. The empty shipped catalog does not
approve any original widget, native service, shell singleton or shared startup
object. There is no graphical/session/service/authentication/security acceptance.
Destroying a QML handle does not prove reversal of arbitrary external effects.
A future integration must replace the original startup paths, preserve notices,
and enforce policy before preparing any original component, including shared
objects and fallback/reload paths. Merely importing this host alongside the
original shell would not provide that protection.

## Repeatable isolated checks

```sh
python3 tools/check_shell_gate.py
# Plan only: no files, subprocesses, QML or desktop changes.

# Explicitly approved, nonvisual fixture checks only:
python3 tools/check_shell_gate.py --run --build-dir work/builds/<timestamp>
```

The runner accepts no arbitrary QML, URLs, catalogs, external shell configuration
or reference directory. It reuses the stage/source-lock/hash verification and
Bubblewrap isolation of [runtime checks](runtime-check.md): read-only runtime
and probe sources, disposable HOME, private PID/network namespaces, no host
home/session sockets, real buses, display/compositor, GPU or network. Each
process has a 20-second timeout; there is no less-isolated fallback. Crash-handler
suppression is diagnostic-only, not a change to the compiled runtime.

Final private evidence:
work/shell-gate/20261024T094908.609350Z/report.json.

**42 fixed cases passed**, covering default/empty/invalid/legacy configuration,
whole-plan validation, duplicate/unknown/inherited IDs, all ten protected service
IDs, schema/size/capability/URL restrictions, actual positive construction,
partial failure cleanup, null object creation, sticky reload/replacement,
reentrancy and catalog URL snapshots. One intentionally wrong assertion exits
42 and is accepted only as that specific negative control, never generic failure.

Every ordinary positive/denial case has zero WARN/ERROR/FATAL/CRITICAL diagnostics
except the explicit object-creation failure case, whose single required-property
warning is expected and retained. The negative control retains one expected
assertion ERROR. Any other warning/error, crash, timeout, missing marker or
missing Configuration Loaded fails the check. Reports record checker hashes,
commands, per-probe file/link manifests, log hashes/diagnostic counts and unchanged
inputs/stage. The staged runtime remains staged-with-warnings, not desktop-ready.

The first exploratory report at 20261024T093538.758091Z failed its positive fixture
counter: relative JavaScript library imports through the root qs: URL and a
file: dynamic component did not share the expected counter instance. It is
retained, not rewritten. The harness now observes QObject completion/destruction
signals directly rather than assuming URL-alias singleton identity. This is not
proof of original-shell dynamic import/Color compatibility. The intermediate
successful runs at 20261024T093737.230772Z and 20261024T094133.235693Z also remain
unchanged. The final run uses strict diagnostic matching/checker hashes and adds
an explicit denial case for a catalog smuggled into untrusted configuration.

At the end of this phase the unit suite had **100 tests**, including 15 new fixture-generator,
classifier, isolation/preflight and provenance contracts. Unit tests themselves
never start Qt. Keep these separate from the 42 actual isolated QML cases.

## Backup, rollback and next gate

Only project files and ignored private research/test reports changed. No active
Ubuntu path was modified, so no active-path backup or desktop rollback is needed.
No runtime deployment, package transaction, graphical test, service activation,
reload, logout/session switch, auth/lock/idle/suspend test, commit or upload.
Earlier dependency rollback still requires a separately reviewed transaction.

Follow-up: the [widget review](widget-candidates.md) now records those lexical
closures and the separately reviewed pure-model import/tests. It does not admit
original QML or change this phase's fixture-only gate evidence.

Next, review the exact dependency closure of a tiny original bar/clock/spacer
candidate, preserve every applicable notice, and decide what shared Commons/API
startup must be separated before admission. Do not populate a production catalog
by treating this fixture success as approval. Real local/dynamic imports, Color,
compiler/protocol warnings and target APIs remain open. Obtain separate approval
for any eventual graphical context, path changes/backups, service ownership,
recovery and rollback. No new graphical test is authorized by this document.
