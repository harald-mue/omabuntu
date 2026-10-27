# Testing

## Automated foundation checks

```sh
python3 -m unittest discover -s tests -v
```

Tests mock external commands and use synthetic temporary files.
They cover success, missing binaries, command failures, timeouts, invalid UTF-8,
session-aware probe selection, missing binary-version evidence, OS parsing,
and private report output. The binary version probe does not start a compositor.

These are tool tests, not Ubuntu desktop, QML, authentication, or suspend tests.
Use the suite output for the current test count. The [network control port](network-control.md)
adds seven isolated Wi-Fi action cases with a fake NetworkManager and no host
radio or secret. The [app launcher first-open fix](app-launcher.md)
adds seven actual Qt cases, including native DesktopEntries with a private
catalog and no application execution. The pre-fix cold test failed as expected. The activated [tooltip correction](tooltip-port.md)
adds seven isolated Qt lifecycle/bubble cases; native popup/hover acceptance
remains pending. The [original section geometry](bar-frame.md) adds seven
actual Qt frame cases with synthetic Hyprland, not native desktop dispatch. The [audio output port](audio-output-port.md)
also has eight isolated Qt fixtures using fake nodes and surface ownership, not
native audio, compositor focus or sound playback. Source-fidelity assertions
check original hero/output/device markup; they do not establish pixel parity. Session lifecycle contracts additionally
cover explicit non-expiring grants, process identity, duplicate-start refusal
and bar-only stop boundaries; see [session lifecycle](bar-session.md). Separately, the original tray has five
isolated Qt fixtures and the [network status port](network-status-port.md) has
seven. The live button is the later [network control port](network-control.md),
not that status popup. These use synthetic inputs, not host DBus; see [bar port status](bar-port.md).
Build tests cover plan-only defaults,
source locks, archive checksum/traversal/link guards, sandbox mount arguments,
staged-prefix layout, QML install configuration, artifact link handling,
mandatory shader-tool detection, diagnostic classification, and post-build shader
assessment (including .qsb directories, empty outputs, and optimizer failures). Runtime-check tests cover fixed nonvisual probes,
nullable type resolution, sandbox binds/environment, stage hash/source validation,
positive/negative controls, timeout reporting, and refusal of an uncontained
fallback. The test suite itself never launches Qt or desktop services. Static-audit tests
also cover passive alias handling, source hashes, lexical graph cycles, manifest
validation, traversal/size/link rejection, no reference execution/network, and
commit-pinned packaging metadata. Gate tests cover fixed fixture generation,
strict diagnostic/negative-control classification, mandatory containment and
stage preflight, linked-source rejection, and the complete pinned license notice.
Widget-audit/model contracts cover pinned file/tree/notice hashes, bounded reads,
links/traversal/import/module guards, conservative lexical references, model
scope, exact runtime metrics, fixed probes and fail-closed preflight.
Additional mocked tests cover mandatory APT simulation flags, candidate pinning,
missing candidates, solver errors/removals, exact-build gating, private profile
snapshots, isolated environments, and native-check failures.

## Clean-source publication checks

```sh
python3 tools/check_clean_source.py --run
```

This repeats the unit suite and fixed help/plan/refusal checks in a new candidate
export without existing work inputs, images or Git metadata; reports remain
private. It does not invoke the native builder. See [clean-source verification](clean-source.md).

Plan 023 additionally exercised the documented native build in that export,
using newly fetched checksum-pinned archives rather than old source/build caches.
The resulting runtime passed all 32 isolated checks and the desktop, command-menu
and image-picker fixtures. An image-free bundle passed installer preflight and
relocation verification, including decoding the authored 16x16 WebP probe. A
smaller valid 1x1 probe had failed native Qt decoding and was replaced, without
using an imported image or weakening the preflight. Existing upstream build
warnings remain warnings, not an unqualified acceptance claim.

These checks use the same host dependencies, not a fresh Ubuntu installation.
They install nothing, start no desktop/service and do not establish visual,
authentication or publication acceptance.

## Manual diagnostic check

```sh
python3 tools/omabuntu.py doctor
```

Review failed probes in the private report. Missing runtime data outside a
Hyprland session must stay unknown, not pass.

## Native profile parsing and package simulation

```sh
python3 tools/omabuntu.py plan quickshell
python3 tools/omabuntu.py check-profile
```

The initial native verifier returned config ok for the bundled Lua prototype.
The initial final-manifest APT simulation proposed 96 new packages, no upgrades,
and no removals. Neither test installed packages or applied configuration.
See [package planning](package-plan.md) and [profile limits](minimal-profile.md).

## Source-build validation

The pinned cpptrace and Quickshell sources compile and stage with Ubuntu Qt
6.10.2 inside Bubblewrap. The expected version probe and presence of 13 required
QML metadata files passed. A clean rebuild after installing the separately
approved spirv-tools package produced both nonempty shader outputs with zero
optimizer failures. This result remains staged-with-warnings because other
upstream/Qt warnings need assessment. All nine sandboxed steps passed; a corrected
post-build scanner reassessed the unchanged artifacts in a separate assessment
report, retaining the original failed scanner report for traceability.
See [runtime build boundaries](runtime-build.md). No full shell, PAM conversation,
lockscreen, service agent, or graphical integration test has been performed.

## Isolated runtime validation

The separately approved live diagnostic run passed 32 sandboxed checks: ELF and
relocation/linkage inspection, sandbox startup, 28 positive module probes (24
with representative nullable type resolution), and one missing-import negative
control. No representative service object was constructed. Positive probes logged
no WARN/ERROR/FATAL/CRITICAL diagnostics; the missing module failed as expected.
Staged hashes and symlink targets remained unchanged. See
[method, evidence, and remaining limits](runtime-check.md).
This is not a functional service, rendering, full shell, or security test.

## Isolated loading-policy fixtures

The independent [fail-closed host prototype](shell-gate.md) is tested using fixed
nonvisual QObject fixtures, not original plugins. This checks actual construction
and teardown, whole-plan denial, protected services, sticky reload/replacement,
reentrant revocation, and URL snapshots. The shipped catalog stays empty. The
unit suite never launches Qt; the explicit --run runner reuses the approved
contained runtime without host session/service access. See the linked evidence
for expected failure diagnostics and the assertion-negative control. This is not
original-shell compatibility or a graphical/security acceptance test.

## Original clock-math checks

The [widget dependency review](widget-candidates.md) keeps original UI entries
blocked but imports one unchanged, provenance-reviewed pure JS model. The explicit
contained checker runs it under Qt 6.10.2: 221 assertions in each of four timezone
cases, plus a specific failing-assertion negative control. No original QML object,
SystemClock, calendar, IPC or helper is loaded. This is mathematical evidence,
not clock/bar rendering, original shell compatibility or service acceptance.
The regular unit suite itself never executes JS or Qt.

## Sealed original spacer geometry

The [passive API/spacer profile](passive-spacer.md) constructs the unchanged
original leaf/base under a deliberately minimal module map and passive Style
adapter, not the stock Commons implementation. Twenty-two contained Item cases
check geometry, readonly/frozen inputs, atomic injection/rebind and invalid-input
denial. A late-injection tripwire, missing-type namespace check and expected
assertion failure make the boundaries observable. No window or rendering occurs;
production admission, full style fidelity and desktop/service acceptance remain
open. These runtime cases are separate from the non-executing unit suite.

## Sealed read-only clock preview

The [clock preview](clock-preview.md) stages the unchanged spacer, base, button,
glyph, and pure model with a derived read-only clock label. The original clock
parent stays in vendor only as provenance and is not loaded by those five
cases. They check formatting, a private software image, strict trial-policy
denial, and an expected assertion failure. The prepared Wayland trial entry is
not started and receives no display socket. The live trial's derived calendar
is a separate mirror, covered by `tests/test_clock_calendar.py` and the desktop
panel compile. These runtime cases are separate from the non-executing unit
suite.

## Keybindings menu

`tools/keybindings_menu.py` formats fixture `hyprctl binds` text and refuses
dispatch unless the action is in that list and is not session-ending. The unit
tests do not call a compositor. The explicit contained runner
`tools/check_tray_port.py --suite keys` loads the real selector with two fixed
rows, with layer and shortcut ownership removed. Return records the selected
action and does not run it. See [keybindings menu](keybindings-menu.md).
This is not live Super+K acceptance.

## Future functional acceptance

Track each required feature as passed, failed, not tested, or deliberately omitted.
Record versions, expected/actual behavior, and rollback.
A clean hyprctl configerrors result is necessary but not sufficient.
Test bindings, real application launch, notifications, screen sharing, and docking.

Lock/idle/suspend testing requires an approved authentication and recovery path.
No deliberate lockout or crash test in an unapproved corporate session.
