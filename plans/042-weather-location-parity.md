# Original weather location editing and IP lookup

## Goal and evidence

Restore the original Omarchy weather interaction at pinned commit
03ff1eff3812933f7088484533784d2f63eaf19a: click the city, type to search,
choose a suggestion, persist name/coordinates, and clear to IP-based location.
The user explicitly requested IP lookup and the original provider behavior,
superseding plan 041's Vienna-only restriction.

The existing vendor Panel.qml already contains this interaction and uses
wttr.in for reports/IP city, Open-Meteo for forecasts and typed geocoding.
The first Omabuntu extraction cut out the editor and hardcoded Vienna. Keep
these original UI blocks now; replace only curl/process and state paths with
a reviewed Python standard-library adapter. Preserve the vendor bytes and MIT
notices. Open-Meteo data attribution remains; acknowledge wttr.in as a provider.

## Proposed shape and safety

Use exact helper commands (report, locate, search, forecast, set, clear) and
fixed HTTPS endpoints, bounded replies, no redirects and bounded network probes.
Never accept arbitrary URLs. FileView watches private Omabuntu weather state.
Back up the existing record before set/clear; reject symlinked state paths.
No credentials, packages, privileged changes, timezone changes, lock or capture.
On first use without state, IP lookup is enabled, as requested. This exposes
the network's public IP to wttr.in; typed searches go to Open-Meteo.

Right-click notification service and shell IPC stay excluded because neither
is part of the existing admitted shell; middle-click refresh and panel controls
remain. Refresh timers do not limit the component lifetime. Ask before a
bar-only restart; back up every deployment path. No commit without asking.

## Tasks

- [x] Restore original location UI with witnessed backend-only substitutions.
- [x] Add bounded provider modes and backed-up location persistence.
- [x] Test endpoint/argument restrictions, state changes, failures and derivation.
- [x] Refresh provenance, documentation and full unit tests (596 pass).
- [x] Deploy and restart only the bar after approval; never lock or capture.

## Deployment result

After explicit approval, backed up the three affected installed files and the
release manifest, replaced them, verified bundle integrity and restarted only
the recorded bar. Configuration Loaded was logged with no QML/helper-launch
errors. No lock or capture was triggered. Native editing, selecting and clearing
are not claimed accepted until the user tries them.
