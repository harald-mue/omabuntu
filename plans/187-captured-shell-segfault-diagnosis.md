# Captured shell segmentation fault diagnosis

## Goal and evidence

Diagnose the owner-reported disappearance after the Plan 186 live upgrade.
The owned session shell is absent while Hyprland survives. Its capture receipt
records SIGSEGV and a completed debugger run, with a retained native backtrace.
Compare the actual failing stack and bounded startup/error evidence against
Plan 186's original carousel/native chooser adaptation and the unchanged
notification runtime/closure. Relevant Omarchy pin remains
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; Quickshell pin remains
`2b4501a282689792b62e94f3fb30d8f512324fe6`.

## Gaps and constraints

Past source/unit/private-native success is not live stability or crash-causality
acceptance. Preserve the entire owned run and capture with hashes/modes before
inspection or restart. Do not inspect notification message/history/clipboard
contents, request full cores or collect debugger argument/local values. Distinguish
crashing thread evidence from background workers and speculation.

This request authorizes diagnosis, not an unrequested desktop restart, rollback,
package installation, service change or competing notification fallback. Keep
all machine-specific paths, raw stacks and logs private under ignored work/.
No source-reference package modification, commit or publication.

## Tasks

- [x] Preserve the owned run, capture and stale running record with integrity metadata.
- [x] Inspect the faulting thread and bounded non-content error evidence.
- [x] Compare implicated code with the exact deployed sources and pinned runtime.
- [x] Report proven findings, unresolved causes and the safest next action.

## Findings

Thirteen evidence files were copied with matching hashes/modes. The debugger log
identifies thread 1 as receiving SIGSEGV; its captured stack passes through
`QQuickItem::boundingRect`, `QQuickPlatformFileDialog::selectFile`,
`QQuickFileDialog::onShow` and `QQuickAbstractDialog::open`. All 60 observed
threads were captured without byte truncation. The deployed picker matches the
workspace source exactly and opens its new in-process import dialog from the
provider-completion callback.

This localizes the observed failure to showing the import chooser. It does not
establish why the item is invalid, distinguish a Qt defect from integration/
lifetime misuse, or explain earlier unrelated crashes. Successful private
fixture tests were insufficient live stability acceptance. Hyprland remains;
the shell/debugger/supervisor are absent, and the notification role has no owner.

No restart, rollback, service or desktop change was performed. The safest next
implementation step is chooser process isolation with realistic repeated
open/select/cancel/reopen and lifecycle regression controls before deployment.
Restoration must retain the captured evidence and use a fresh exact session
notification grant, never a spent grant or a competing fallback.
