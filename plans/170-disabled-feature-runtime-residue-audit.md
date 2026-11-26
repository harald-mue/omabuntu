# Disabled feature runtime residue audit

## Goal and evidence

Determine what remains of removed monitor-profile and Advanced audio menus,
separating dormant packaged files, instantiated-but-disabled QML and shared
helpers still required by normal controls. Compare Plans 162–163, the current
source and installed release. Original UI provenance is Omarchy
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Repeated native crashes are not proof
that retained components are responsible.

## Gap and proposed shape

Menu removal does not necessarily remove components, timers, imports or helpers.
Trace reachability and activity gates, compare installed bytes and inspect only
owned child-process metadata. Identify safe cleanup boundaries and dependencies
without deleting shared code or evidence.

## Safety and exclusions

Read-only audit apart from this plan/private ignored evidence. No live provider
queries, state changes, cleanup/deletion, crash-mode interruption, restart,
deployment, packages or commits. Preserve recovery receipts and user settings.
Any cleanup implementation and live deployment need separate approval.

## Tasks

- [x] Trace retained QML roots, helper dependencies and execution gates.
- [x] Compare installed bytes and owned process activity without provider queries.
- [x] Record justified cleanup candidates and acceptance limits.

## Findings

All reviewed installed QML/JS/helper bytes match the current source. The monitor
profile QML files and helper environment variable remain packaged, but TrialPanel
no longer constructs DisplayProfilesState or references the profiles view. Its
watcher and pending-profile timer therefore have no live root in this shell.
Do not equate packaged files with running automation.

Normal monitor controls still import display_profiles: native session/inventory
proof, lock/pending checks, text-size state/backups and outcome receipt writing
are shared. In particular, Profiles.set_text calls overview after writing text,
which reads the profile store/history and inventories displays even though the
profile page is removed. This is concrete unnecessary workflow coupling worth
separating; deleting the module now would break normal controls or guards.

Advanced audio has a fixed-false UI capability, but TrialPanel still constructs
AudioNativeState and passes it to the ordinary provider. Opening the ordinary
audio panel constructs the disabled AudioNativeControls subtree. No helper
queries or event subscription start without the separate grant (false by
default, and the UI invocation path is disabled). Nevertheless the optional
state/Process/Timer objects and bridge properties remain, and the ordinary
provider still evaluates AudioUntyped.merge on native state changes. Untyped
fallback is not functional without its separate grant; its live hooks can be
removed while retaining ordinary typed inputs, output/stream controls, DSP
routing, peak monitoring and OSD. This is a cleanup candidate, not a diagnosed
native memory fault.

The single owned-descendant snapshot found an inotifywait process and no optional
audio helper or monitor-profile watcher/guard. It cannot exclude short-lived
processes or establish live internal QML flags. No debugger memory inspection,
native audio/display queries or additional grants were performed. The current
diagnostic capture had not fired at the check.

Recommend first removing the disabled optional audio objects and hooks from the
normal shell, then extracting the shared monitor primitives out of the profile
workflow before retiring packaged profile UI/env references. Preserve private
profiles, text settings, backups and recovery receipts, and deliberately retain
or archive offline recovery functionality. Do not remove ordinary PipeWire
tracking/routing as if it were solely Advanced audio. Any implementation and
live deployment remain separate approvals; no implementation was changed here.
Private evidence: `work/disabled-feature-audit-170/findings.json`.
