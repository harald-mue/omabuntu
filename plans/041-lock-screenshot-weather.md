# Lock and screenshot menu actions, followed by the original weather panel

## Goal and compared evidence

Add System > Lock and Trigger > Capture > Screenshot to the existing command
menu, then adapt the original weather panel beside Elsewhen. This is one user
request and one plan. Preserve unrelated uncommitted plan 040 changes.

Omarchy is pinned to 03ff1eff3812933f7088484533784d2f63eaf19a. Its menu
uses omarchy-system-lock and omarchy-capture-screenshot. Omabuntu already has
an explicit installed-manager lock action and the Omasnap wrapper from plan
031. Omasnap is pinned to a432f40b14598a4a02b89fa0054f9a0ba3662dd4;
its screenshot integration is already implemented, not a missing grim backend.
The weather panel sources and helper/provider contract must be reviewed at the
same Omarchy pin before import; root and component license notices must be
checked first.

## Gaps and proposed shape

The command menu currently omits both actions. Add exact registry tokens that
launch the existing installed manager for lock and the packaged capture wrapper
for screenshots. Detach these session-lifetime actions so the menu can close
and does not cover a screenshot selection. Never give a lock a timeout.
Keep stdout from detached programs out of the JSON menu response. Validate
helper presence and refuse unrecognized action shapes.

For weather, prefer the original source and layout with a narrow Ubuntu backend,
not an authored replacement panel. Review the upstream provider and location
handling before choosing a Python standard-library adapter. Mount after Elsewhen.
Document network endpoints, location handling, cache/refresh intervals, failures,
and exclusions. Ask for a location if none has been selected; do not silently
send IP location, home/office details, or coordinates to an external provider.

## Safety and exclusions

No lock test, capture, package install, live bar restart, privileged action,
PAM, idle policy, or keybinding changes. Screenshot continues to use Omasnap,
not grim/slurp. Weather consent does not authorize IP geolocation or an
unreviewed provider. Deployment and a bar-only restart require separate approval.
No commit without asking. Back up affected paths before deployment.

## Tasks

- [x] Add exact menu registry actions for the installed lock manager and Omasnap.
- [x] Add menu rows in upstream order and package the existing capture helper.
- [x] Test detached argv, no session timeout, missing-helper and injection refusal.
- [x] Review pinned weather sources, notices, endpoints, and location contract.
- [x] Adapt and test the original weather panel and reviewed backend for Vienna.
- [x] Run the full unit suite and update documentation and WORKLOG (590 tests after weather integration).
- [x] Ask before deploying files or restarting the live bar; do not lock or capture.

## Weather review checkpoint

The pinned panel's manifest names Omarchy as author. No additional component
notice appears in these four source files; root MIT attribution must accompany
any future import. Panel.qml uses wttr.in for current reports and IP-based
location detection, api.open-meteo.com for forecast/current conditions, and
geocoding-api.open-meteo.com for typed city search. The bar wrapper also has a
right-click notification command; this is outside the approved backend scope.
Do not adopt automatic IP location or the additional wttr.in provider without
asking. Proposed adaptation: original view/model, Open-Meteo only, user-chosen
city, no weather fetch until configured, no notification command or ShellIpc.
At that checkpoint no source had been imported. The user subsequently approved
Open-Meteo only and selected Vienna. The four original files are now vendored
with root MIT attribution recorded before import. The original model, widget,
and panel layout are staged with witnessed transformations. City editing,
notification actions, IPC, wttr.in and IP location are excluded. Vienna uses
48.2082 N, 16.3738 E and Europe/Vienna, with Celsius and km/h. The Python
standard-library probe accepts only `forecast`, rejects redirects, bounds the
response to 256 KiB and gives the HTTPS request a 10-second timeout. The panel
refreshes every 15 minutes and retries failures at most three times per cycle;
last-good values remain visible on failure, as upstream. These are refresh and
probe deadlines, not a component lifetime limit. A one-shot approved provider
check returned a valid four-day report. Unit tests never use live network.

The user subsequently approved deployment and a bar-only restart. Affected
paths were backed up privately before changing the active release. Installed
integrity passed, and the recorded bar restarted with Configuration Loaded and
no QML or helper-launch errors. No lock or screenshot was triggered. Hyprland
and applications stayed running. The earlier local qmllint pass had unresolved
Quickshell/qs imports; clean startup is construction evidence, not native popup
or visual acceptance. Data attribution
to Open-Meteo (CC BY 4.0) is in the bar tooltip and third-party notices.

