# Network and audio popup crash review

## Goal and evidence

Review opening, closing and switching the network/audio popups after the owner
reported a crash while clicking the upper-right controls. The kernel confirmed
a Quickshell segmentation fault in Qt QML 6.10.2; that location alone does not
identify the responsible component. Compare the Plan 163 installed source,
shared popup lifecycle, contained tests and original-derived source provenance
at Omarchy `ac2690cd7be4f47e4a255f5e2e78d904d436b068`.

## Gaps and proposed shape

The last runtime log does not identify which popup was clicked. Review lifecycle
and model changes statically, compare installed bytes and inspect regression
coverage. Record concrete risks separately from confirmed causes. Do not claim
that synthetic coverage establishes native crash freedom.

## Safety and exclusions

No live clicks, reproduction in the owner session, restart, installation,
configuration changes, network/audio mutations, service activation or commits.
No upstream imports. Keep machine-specific evidence under ignored work/.
This request is diagnosis only; any fix or deployment needs a separate decision.

## Tasks

- [x] Inspect shared lifecycle and network/audio controller/view code.
- [x] Compare installed source and existing contained regression coverage.
- [x] Record findings, uncertainty and recommended next diagnostic step.

## Findings

The installed controllers, views, audio provider and TrialPanel match repository
bytes. Installed KeyboardPanel matches `audio_frontend.derive_keyboard` exactly;
its differences from the vendor file are the existing Ubuntu focus/unmap policy
and local hit-testing boundary, not installation drift.

The strongest shared lifecycle review target is synchronous closure during event
dispatch. KeyboardPanel forwards a bar click through `target.triggerPress`, and
TrialPanel.requestPopout immediately closes the previous owner. In the installed
Ubuntu derivative `visible: open` unmaps the previous window immediately.
Separately, KeyboardPanel's cross-output dismissal Variants uses
`model: root.open ? Quickshell.screens : []`, while a delegate MouseArea calls
`root.close()` from `onPressed`. Closing therefore removes those delegates while
their own input callback may still be executing. These are concrete lifecycle
sequences to test, not proof of an invalid access or of this incident's cause.
The cross-output sequence requires a click on another output; the owner's
upper-right click report alone does not establish that condition.

Network open/close also toggles native scanning and refreshes row models; audio
open/close toggles native peak monitoring and clears displayed row lists. Both
are native-boundary candidates, but static inspection establishes no specific
fault in either provider. Lazy popup content remains loaded after first opening;
there is no general content-loader destruction on every close.

The contained desktop probe substitutes a lightweight KeyboardPanel Item;
existing synthetic panel/provider and navigation tests do not establish safety
of the real PanelWindow/Wayland dispatch path. All 1,640 unit tests pass; private
output is under `work/diagnostics/plan-164-unit-tests.log`. This is not native
crash reproduction or acceptance.

Recommended next step: a separately approved, disposable isolated reproduction
of the actual shared KeyboardPanel with synthetic network/audio models,
exercising click forwarding and dismissal with queued versus synchronous close.
Do not change focus policy, disable network/audio or deploy a speculative fix.
A native backtrace would be needed to attribute the Qt QML fault reliably.
No running desktop, runtime configuration or project implementation was changed.
