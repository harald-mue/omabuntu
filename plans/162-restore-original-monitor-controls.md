# Restore the original monitor controls

## Goal and evidence

Respond to the owner's rejection of the installed authored monitor-profile page:
remove it from the running shell and restore the original single-page monitor
interaction, rather than redesigning the rejected page. Compare the MIT monitor
Panel/Model from Omarchy v4.5.0 at
`ac2690cd7be4f47e4a255f5e2e78d904d436b068` with the installed Plan 161 derivative.
Use the already pinned official Hyprland wiki and reviewed 0.57.0 source
`efb50993780079460b0cbed1363e2166a2de1d9f` for partial monitor-rule updates.
The owner screenshot shows duplicate navigation, a permanent technical paragraph,
and capture rejected for an existing layout gap. Synthetic tests did not establish
visual fidelity or native usability; the earlier completion claim was too broad.

## Gaps and proposed shape

The profile integration replaced original output switches with navigation and
added an authored page plus a shared automation owner. Remove those connections.
Keep original brightness, text-size, scale and output rows, with only narrow
Ubuntu backend adaptations and inline errors. Restore actual output enable/disable
with last-active-output protection, stale observation/session checks, private
before-state backup and observed readback. Preserve shell-local text sizing through
the normal controller, without requiring a profile page or automation owner.
Retain dormant legacy profile code/data for recovery and history; do not weaken
its layout validation or silently migrate/delete profiles. Update current status
so the withdrawn integration is not advertised as original parity or accepted.

## Safety and exclusions

Diagnose and back up source and affected installation paths with hashes, modes,
and absence. Refuse deployment over an unresolved display/deployment transaction
or active automation. Do not apply/save profiles, change geometry/text/permissions,
or issue brightness/output setters during verification/deployment. No GNOME/GTK
font changes, packages, services, bindings, autostart, wallpaper, security-policy
changes, commits or push. Restart only the owned session-lifetime managed bar;
every normal/recovery start must use `restore_background=False`. Preserve unrelated
settings, assets, runtime, audio/Bluetooth controls and receipts. Hardware/pointer/
visual acceptance remains an owner check, not an inference from contained tests.

## Tasks

- [x] Diagnose current source/installed state and privately back up affected paths.
- [x] Restore the single original-derived surface and independent normal controls.
- [x] Add regressions for no profile navigation/owner, direct guarded toggles,
      stale/last-output refusal, unchanged layouts with gaps, text and keyboard use.
- [x] Run all unit tests, contained actual-QML checks, source seals and preflight.
- [x] Deploy the narrow correction reversibly and verify unchanged native state,
      settings, session lifetime, fallback, receipts and warning-free startup.
- [x] Update current documentation and record precise verification limits.

## Closeout

Installed `original-shell-162-20261124T064224.047865Z` with exactly five manifested
changes: three shell files, the display helper and provenance. All 154 shell seals,
exact helper bytes, manifest and preflight pass. 1,640 units, contained actual-QML
normal pointer-signal/keyboard controls (including a click during read-only refresh,
last-output protection, text first-create/readback, scaling and brightness), and
desktop/audio/frame/tooltip/clock/clean-source checks pass. The legacy-named profile
QML fixture now exercises the corrected normal monitor popup, not the rejected page.

Only the owned bar restarted, retaining session lifetime, with background restore
disabled and no new warnings. Read-only installed status and before/after geometry
checks pass; text, settings, receipts and dormant profile state are preserved.
No display/deployment/update transaction remains open. Plan 161 is the verified
immediate fallback; Plan 159 is also retained and verified. No live native setter,
profile save/apply, automation, permission, package, service, binding, autostart,
commit or push was performed. The legacy profile capture validator is not weakened
or advertised as repaired: the authored feature is withdrawn from normal operation.
The corrected visual/native device behavior still needs owner acceptance.
