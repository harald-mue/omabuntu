# Original bar, clock and spacer dependency review

## Outcome

The original bar, clock widget/calendar and spacer remain **blocked unmodified**.
Their small visible surface is not an isolated dependency surface. The shipped
[load catalog](../config/shell/GuardedHost.qml) is still empty and unchanged.
In this initial review phase no original QML/plugin/service object was constructed
or graphically tested. Follow-up: the [sealed spacer profile](passive-spacer.md)
now constructs the unchanged leaf/base as non-rendering Items with a deliberately
adapted passive namespace, not the blocked stock Commons/Style closure.

One separable original source file is now included, unchanged: the clock's
[pure date/format model](../vendor/omarchy/shell/plugins/panels/clock/Model.js).
Its exact source/license review and contained Qt mathematical checks are below.
This is not a replacement clock or an assertion of original UI fidelity.

## Repeatable pinned static audit

```sh
python3 tools/audit_widgets.py --reference /path/to/private-reference \
  --source-evidence work/research/omarchy-source
```

The optional development inputs are explicit; no private reference/evidence is
needed to run the vendored model tests or the eventual standalone desktop.
The evidence directory contains the previously collected source-tree.json and
source-provenance.json. The auditor checks the complete cached response hash,
pinned commit/repository/URL and non-truncation before using its Git blob index.
Every visited captured file must match that blob by its actual bytes. No network,
reference program, helper, QML engine, plugin or shell execution occurs here.

The auditor reads bounded regular files, refuses links/traversal/missing explicit
imports/unsupported module declarations and limits graph/text growth. It follows
literal local JS/QML references and visible local/qs.Commons/qs.Ui type symbols,
records native imports, unresolved literals, ambiguity and dynamic-source lines,
and retains source hashes and lexical helper/risk markers in private reports.

Final private evidence:
work/widget-audit/20261024T101847.309301Z/report.json.

| Entry | Lexical reference closure, including module metadata |
|---|---:|
| Original bar | 20 files |
| Original clock widget/calendar | 33 files |
| Original spacer | 11 files |
| Combined distinct visited files | 38 files |

**These are not eager object counts or exact complete dependency closures.**
Comments/strings contribute conservative references; a function referencing a
singleton does not prove that singleton starts at import time. QML precedence,
inline/native types, JS context, runtime registries/custom modules, data/assets,
external helper closures and native backend behavior remain separate questions.
Module exports being available does not mean every export is instantiated.
For example, clock-local Panel/BarWidget names coexist with qs.Ui names; lexical
ambiguity is recorded, not resolved by pretending this tool is a QML compiler.
This audit never grants loading permission.

## Manually reviewed integration boundaries

Witness paths are relative to the pinned upstream shell tree at
03ff1eff3812933f7088484533784d2f63eaf19a; root entry hashes and decisions are in
[widget-candidates.json](../upstream/widget-candidates.json).

### Original bar

- plugins/bar/Bar.qml:736-751 applies configuration and invokes
  Util.execDetached("omarchy-bar sync-glass") when the look changes, including
  the initial empty-to-opaque transition. An empty widget layout is not inert.
- :951 calls applyBarConfig on completion. :1465-1477 starts the bar-off Bash
  probe and watches its state directory. Other FileViews track appearance/state.
- :1493-1531 creates per-screen bar/drag/move delegates; BarPanel is a PanelWindow
  with layer/exclusion behavior. Hidden bar surfaces are parked, not necessarily
  unloaded. Do not confuse hidden state with absence of compositor effects.
- :978-987 exposes shell command/background routes. WidgetHost (:2282 onward)
  selects registry components, custom QML or custom commands; custom command
  execution ultimately uses Bash (:2759-2777). A fixed layout alone does not seal
  those code paths or the registries that supply components.
- Startup helper invocation and Style/Color dependencies must be separated from
  layout/rendering. Source-level changes, explicit host APIs and sealed component
  resolution are needed before any real bar trial. No native window is tested.

### Original clock

- plugins/panels/clock/BarWidget.qml:130-140 declares Loader active:true for
  Panel.qml while visible:false. The calendar is prepared/created, not disabled
  by being invisible; interactive:false on its button would not remove it.
- The label uses SystemClock, I18n, Style, WidgetButton and the shared BarWidget
  base. ShellIpc registers through IpcRegistry; the calendar further extends
  Ui/Panel and loads the keyboard/panel control toolkit.
- Right-click format cycling can persist through shell.updateEntryInline;
  middle click calls bar.run("omarchy-menu-timezone"). Panel settings can also
  persist. Read-only label display must be separated from IPC/actions/persistence
  and calendar creation before a constrained original-widget trial.
- No SystemClock, original label, calendar, IPC endpoint or timezone helper was
  instantiated/executed by this work. The accepted code below is math only.

### Original spacer and shared tokens

- plugins/bar/widgets/Spacer.qml is a small geometry leaf, but extends
  Ui/BarWidget.qml, whose bar defaults to null and whose barSize falls back to
  Style.bar.sizeHorizontal. Its default height can therefore activate Style.
- Commons/Style.qml:369-373 starts three hyprctl queries via refresh; :464-555
  declares command processes/fontconfig/state watchers; :557-559 invokes refresh
  and font resolution on completion. This is not passive spacing data.
- Commons/Color.qml:228-257 reads theme/override files and watches the user
  override. I18n declares watched locale/catalog inputs. Util includes command
  dispatch helpers even though many of its functions are pure. References to
  these modules do not prove all of their functions or dependencies execute.
- An atomically injected complete passive bar API might avoid the spacer's Style
  fallback branch. That behavior has not been tested; injecting it only after
  creation is not sufficient evidence. A sealed minimal module map and possibly
  a reviewed token/geometry split are still required.

## First original pure-code import

The complete clock Model.js was manually read and reviewed before copying:
function definitions and date/number/array/string math, constant arrays, and a
guarded CommonJS export. It imports no local/native modules, creates no QML
objects and uses no Qt/Quickshell, commands, files, network or service APIs.
The audit records no local edges or helper/risk markers for this file. This is
a review of these exact bytes, not a rule that marker-free JavaScript is safe.

- Canonical source: shell/plugins/panels/clock/Model.js, pinned commit above.
- Fetched separately from the pinned public raw URL with a 64 KiB response bound;
  bytes match the pinned Git blob and captured file. No private user data copied.
- SHA-256: 101514693517f694203841a4f39fe4c54d9469a2cbf4dd6b0264e6d440adbe75.
- Git blob: 873db9535edc73e220517c848d69733cdd4d1feb.
- Size: 12,174 bytes; modifications: none; separate dependencies: none.
- Upstream root MIT notice applies; no separate copyright/license notice appears
  in this file. Preserve Copyright (c) David Heinemeier Hansson and the full
  notice in [vendor/omarchy/LICENSE](../vendor/omarchy/LICENSE), identical to
  [licenses/Omarchy-MIT.txt](../licenses/Omarchy-MIT.txt). Copyright is not
  reassigned to Omabuntu. Provenance is recorded per file, not blanket-imported.

In this initial phase no original UI files, helpers, fonts, icons, translation
data or other assets were copied. The later spacer/base import is recorded
separately in the linked passive profile. Additional Omapager/Elsewhen/brand/dataset obligations from the
[source review](shell-gate.md) do not become cleared by importing this model.

## Contained Qt checks, not UI tests

```sh
python3 tools/check_clock_model.py
# Plan only, no files/processes/desktop changes.

# Explicit contained mathematical check, no original widget construction:
python3 tools/check_clock_model.py --run --build-dir work/builds/<timestamp>
```

The runner verifies the fixed model path, source/review manifest, SHA-256/Git blob,
length, unchanged status and both complete notices before any process. It also
verifies the existing runtime source lock/staged hashes and uses the established
Bubblewrap containment: read-only runtime/test/model files, disposable HOME,
private PID/network namespaces, no real buses, host session/compositor/display,
GPU or network. Each case times out after 20 seconds; no less-isolated fallback.
Only a minimal authored ShellRoot/check timer and the reviewed JS are evaluated.
Crash suppression is diagnostic-only; the compiled runtime is unchanged.

Final private evidence:
work/clock-model/20261024T101847.402782Z/report.json.

Four timezone cases passed under the actual Qt 6.10.2 JavaScript engine:
UTC, Europe/Berlin, America/Havana and America/Santiago, **221 assertions each**.
The case verifies the selected zone's offset, ISO weeks/year/leap boundaries,
format rings/seconds/vertical presets, week-start normalization, birth-year/life
math and continuous six-week civil-date grids across historical midnight/DST
transitions. These are fixed synthetic dates, not user information. No Node/V8
success is substituted for testing Qt's engine.

An intentionally wrong ISO-week assertion is a fifth negative control: exactly
exit 42 and the specific deliberate assertion ERROR, with no success marker.
Each ordinary case requires exactly one marker with 221 assertions and its
expected timezone, exit 0, Configuration Loaded and zero WARN/ERROR/FATAL/CRITICAL.
Crash, timeout, missing/duplicate/wrong metrics and unrelated failures cannot pass.
Commands, checker/metadata/probe/log hashes, metrics/diagnostics and unchanged
inputs/stage are recorded. Earlier successful runs remain unchanged. No actual
original widget, rendering, dynamic Color import or service acceptance follows.

At the end of this phase the suite had **126 tests**, including 26 new static-audit, provenance,
classifier and preflight contracts. Unit tests themselves never execute JS/Qt.

## Backup, rollback and next step

Only project files and ignored research/test reports changed. No active Ubuntu
configuration, service or runtime installation changed, so no active-path backup
or desktop rollback was needed. The separate reference and staged runtime remain
unchanged. No package/privileged command, graphical trial, service activation,
real reload, auth/lock/idle/suspend test, session transition, commit or upload.
Remove/revert only these candidate project additions to discard this work;
previous package rollback still requires its own reviewed transaction.

Next, design the minimal passive token and atomically injected host-API contract
needed by an original spacer or label, and test that sealed module closure in
containment before enabling any original QML entry. Keep the policy catalog empty
until that integration is reviewed. A complete original clock includes calendar,
settings, locale, IPC and actions; silently replacing it with a similar label
would not establish parity. Any eventual graphical trial still needs separate
approval, affected-path backups, compositor/service ownership, recovery and
rollback. Full shell and authentication acceptance remain separate gates.
