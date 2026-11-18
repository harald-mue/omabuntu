# Install and update the original activation-focus policy

## Goal and evidence

Make the user-confirmed browser activation behavior part of Omabuntu installation
and updates, rather than only the development user's personal profile. Compare
plans 123-124, Omarchy v4.5.0 `ac2690cd7be4f47e4a255f5e2e78d904d436b068`
(`default/hypr/looknfeel.lua`), the reviewed Hyprland 0.57.0 configuration API,
fresh-session templates, published installation, setup release switching and the
application-only updater. Existing v0.2.4 artifacts are immutable.

## Gaps and proposed shape

The personal profile now enables focus-on-activate, but source defaults and
ordinary app updates do not deploy it. Add the default to fresh/evaluation
profiles and ship a tiny dedicated focus-only managed Lua module. Do not redeploy
the broad legacy managed snippet, which also carries unrelated activation/layout
behavior. After an approved successful application install/update, reconcile this
module and one clearly marked include through an independent backed-up journal.
Cover already-current installer reruns and the menu updater as well as setup.

The initial additive desktop configuration/reload needs a disclosed confirmation;
normal installer defaults remain unchanged. Once owned/current it is idempotent,
with no repeated question or reload. Unknown/edited managed files, ambiguous
includes, stale inputs and interrupted journals require review rather than
replacement. Missing profiles defer until generic session creation. A running
session must be the current owned Hyprland context; otherwise stage only while
Hyprland is stopped, never reload another desktop. Report application switch and
policy-stage outcomes separately, including deferral/failure, without pretending
one is an atomic rollback of the other. Future explicit user customizations are
not silently reset. Browser launch arguments and singleton/GTK behavior stay as-is.

## Safety and exclusions

Repository implementation and isolated fixture tests are authorized. The local
setting already works; no further live deployment, reload, app activation,
workspace switch, package/service change, commit, push, signing or publication is
part of this request. Keep backups/raw diagnostics private under ignored work/.
Every deployed file has a recorded previous existence/content/mode before writes;
restore only transaction-owned content and preserve concurrent edits. Record prior
runtime/autoreload state for live application and recovery. Do not replace private
profiles, enable plugins/autostart/locking or expose upstream helpers through PATH.

## Tasks

- [x] Trace all installation/update and fresh-profile paths; back up affected sources.
- [x] Implement narrow owned focus-policy planning, deployment and guarded recovery.
- [x] Integrate packaged defaults and normal installer/update flows with explicit scope.
- [x] Test fresh/repeat installation, upgrades, conflicts, failure/recovery and no-op behavior.
- [x] Update documentation, run the complete unit suite and verify packaging inputs.

## Outcome

Fresh templates and future packaged artifacts enable the original global policy.
Normal published installation (including current-version reruns), setup release
switches/ready-release installation and menu updates run the independent,
explicitly confirmed focus stage. Generic session ownership remains intact;
recognition of the exact focus-only addition also preserves later explicit
adoption of an untouched legacy managed profile. Noninteractive app approvals do
not silently authorize a desktop change. Low-level manager/package operations
remain app-only, and application rollback does not undo the independent policy.

Fixture tests cover additive stopped/live deployment, idempotency, decline,
missing profiles, edited/ambiguous/symlinked inputs, stale approvals, reload
failure, backup integrity, concurrent edits/recovery, host-session admission,
legacy adoption and actual updater follow-up ordering. The full suite passed;
private logs, source backups and updater import-closure staging evidence are in
`work/focus-policy-125/`. The verified updater closure includes `focus_policy`.
No additional live configuration, release artifact, commit, push or publication
was performed. The owner's positive Chrome interaction test applies to the
previously approved local correction, not a fresh-machine acceptance of this
new installer helper.
