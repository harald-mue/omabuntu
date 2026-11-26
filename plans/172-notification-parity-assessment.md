# Notification parity assessment

## Goal and evidence

Compare pinned Omarchy v4.5.0 (`ac2690cd7be4f47e4a255f5e2e78d904d436b068`)
notification service, toast UI and interaction with Omabuntu's current shell and
existing notification owner. Determine useful fidelity gaps without assuming the
user's dissatisfaction has one known cause. Compare hash-verified upstream
sources, current source admission/DND adapter, bounded live owner metadata and
notification configuration where available. Do not collect notification bodies.

## Gaps and proposed assessment

Omabuntu explicitly excludes the upstream notification service; its DND indicator
adapts an existing SwayNC owner. Check actual ownership rather than infer it from
installed packages. Separate upstream source features, active local behavior and
unverified user-visible behavior. Identify narrow styling/integration options
versus a separately reviewed full original-service port; do not implement either.

## Safety and exclusions

Read-only diagnosis, except private research evidence under ignored work/ and
this assessment plan. No test notification, notification/history payload access,
DND setter, package installation, service stop/start/reload, desktop edit, shell
restart, debugger interruption, security-policy change or commit. Notification
ownership changes and third-party imports require separate review/approval.
Do not take over GNOME's bus ownership or start competing notification daemons.

## Tasks

- [x] Verify upstream source content and notification behavior/dependencies.
- [x] Inspect current shell boundaries and active notification owner/configuration.
- [x] Summarize concrete parity gaps, limitations and recommended next decision.

## Findings

Thirteen upstream files (notification plugin closure, sender and system document)
were fetched at the pinned commit and matched against recorded Git blob hashes.
Original service provenance also credits Omapager (Neil Jagdish Patel, MIT);
retain that attribution in any later reviewed import. Raw sources and owner
metadata are private under `work/notification-parity-172/`.

Omarchy owns `org.freedesktop.Notifications` inside Quickshell. It draws themed
380-scaled-unit cards in source-grouped top-right decks, pinned to the initially
focused output until empty. Hover expands a deck and pauses expiry; new arrivals
wait during reading (bounded hold). Low/normal durations start at 5/8 seconds,
requested durations extend up to 30 seconds, critical remains until dismissed.
It has explicit keyboard mode, source/action/window activation, history replay,
verification-code actions and its own DND exceptions. History is capped at 100
entries/24 hours, transient entries are not persisted and detected codes are
redacted. These are source findings, not a full security/functional acceptance.

Live read-only D-Bus owner/server queries identify SwayNotificationCenter
0.12.4 as the current notification server. Its process has no custom config/style
arguments; its XDG configuration locations select the ordinary user/system
paths. No user SwayNC directory was found. The system configuration/style specify
500-wide notification windows, fixed default styling, 10/5/0 normal/low/critical
timeouts, app grouping, a separate control center and enabled 2FA actions.
Inline reply is advertised as a capability but disabled in the found config;
capabilities alone are not enabled-feature acceptance. Existing loaded state was
not introspected or reloaded; these are file observations, not pixel tests.

Omabuntu's normal shell does not stage/instantiate the upstream notification
service. Its indicator adapts only the existing SwayNC DND owner and does not
supply the toast layout, history, focus routing or notification theme. Therefore
this is not notification parity despite the original-derived DND button. A
SwayNC style/config adjustment could improve appearance but would remain a
different service/interaction model; do not call it original fidelity.

A faithful port would need the original service/UI/model dependency closure,
reviewed Ubuntu action/state/ownership adapters, DND backend replacement,
privacy and notification-action review, and separately approved reversible
single-owner deployment. The present shell crashes are an additional gate: a
shell-owned notification service would fail with that process, whereas the
existing SwayNC process is separate. Do not add more shell responsibilities or
stop the current provider during this read-only assessment. Clarify whether the
user dislikes appearance, placement, dismissal/lifetime or activation before
choosing the next implementation slice.

No notifications were sent, read or dismissed; no history content was collected.
No service, configuration, DND state, installed release or debugger was changed.
No production code changed, so no new runtime/unit-test verdict is claimed.
