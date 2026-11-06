# Keep browser CSD controls without duplicate hyprbars

> **Superseded by plan 085:** the browser exception was rolled back in source
> and live configuration; this plan records the historical experiment.

## Goal and evidence

Implement approved variant 1: retain Chrome/Edge application controls in tiling
and floating workspaces, suppressing only their compositor-side hyprbars.
Preserve GNOME and all shared application/GTK settings. Plan 080 identifies the
two decoration owners. Compare the current titlebar templates, deployed owned
rules/receipt, and official Hyprland v0.57.0 regex matching/API source. Omarchy
component baseline remains v4.5.0 stable at
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; this is a documented Ubuntu adaptation.

## Shape and current gap

The existing named show rule enables hyprbars for every floating-workspace
member. Replace its class wildcard with the documented `negative:` full-match
browser-family expression, retaining the hide rule, membership tag, rule names
and workspace refresh mechanism. Cover Chrome, Edge and their app/PWA class
forms; leave other applications unchanged. Apply the same exception to the
historical source snippet to prevent inconsistent source behavior.

Add regression coverage for positive/negative class cases, rule ordering and
repeated Lua application. Back up tracked source paths before edits. For the
approved live change, verify installer ownership and back up the deployed
rules plus activation receipt before updating only the show matcher and its
receipt hash. Apply only that named rule live through the compositor API;
do not re-evaluate the whole button-adding template or reload the plugin.
Retain private deployment evidence and exact rollback data.

## Safety and exclusions

No gsettings/dconf/GTK or browser profile/policy changes. No new app launch,
window move, app restart, compositor/plugin reload, logout, service/autostart
change, package installation, shell restart, commit or publication. Keep existing
activation grants and helper paths. Refuse unknown deployed source, ownership
mismatch, symlinks or concurrent changes. Back up before host writes; restore
file/receipt and named matcher on failure. Native visual acceptance requires
user interaction; read-only rule checks are not screenshot acceptance.

## Tasks

- [x] Verify version-specific matcher/API behavior and back up source prestate.
- [x] Implement the browser exception and regression coverage.
- [x] Run the full unit suite and source/diff checks.
- [x] Back up and apply only the owned deployed rule/receipt and live named matcher.
- [x] Verify unchanged GNOME setting, clean config errors and process continuity; document limits.

## Outcome

Official Hyprland v0.57.0 source confirms `negative:` RE2 full-match inversion,
named-rule reuse and replacement of an existing class match engine. The two
source snippets now keep selected Chrome/Edge/PWA classes outside the existing
floating-membership show rule. No third rule or custom-effect/button append was
introduced. Tests cover browser identities, unrelated/near-miss classes, source
parity, rule order and unchanged two-rule behavior; existing Lua execution tests
continue to cover repeated-application safety.

The private deployment verified the receipted exact pre-change titlebar template,
current compositor version, already loaded receipted plugin, ownership and absence
of config errors. Under the manager control lock it backed up both files/modes
and their prestate before changing the owned titlebar matcher plus receipt hash.
It applied only the named class matcher live, retaining effect/button state,
activation grant, helper paths and the selected immutable application release.
The durable file is used on subsequent config loads/logins; future packages use
the updated source template. No new bundle was required for the owned config.

Post-apply checks confirm clean config errors, unchanged GNOME button layout,
valid plugin/config ownership receipt and identical owned shell process record.
All 1082 tests and the clean-source export check pass; diff whitespace checks
pass. Native visual/focus acceptance on floating browser/PWA windows and the next
GNOME login remain user checks. No windows were moved, no reload/restart or
service change occurred, and no commit/publication was performed. Private evidence
and the exact backup location are recorded under ignored
`work/research/window-buttons-081/`; durable backups are in the manager's private
`titlebar-csd-transactions/` directory.
