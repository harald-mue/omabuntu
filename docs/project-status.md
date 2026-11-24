# Current project status and remaining source-parity work

This is the current acceptance summary after the owner's plan-133 review.
Older plans are historical records, not a live backlog. Removing an obsolete
unchecked task does not mean its proposed operation was executed or approved.

## Owner-reported acceptance

The owner explicitly confirmed that the everyday checks listed in the project
review are all working:

- Calendar, tray pin/hide choices, dock and World Clock preference persistence
  across bar restart and a subsequent login.
- Monitor/workspace behavior, including physical docking/hotplug and a fresh
  login in the tested setup.
- Existing audio output and microphone controls, Bluetooth device interaction,
  network panel, brightness and runtime scaling.
- Existing keyboard panel navigation and multi-output focus behavior.

The owner also reported having tested the installation/deployment review on a VM.
Record that as owner-reported VM acceptance, not as an outstanding generic
"first VM test" task. No exact VM image, release version or scenario-by-scenario
report was supplied. Do not invent evidence for real interrupted APT, abrupt
power loss, every package rollback, every dependency combination or every
Ubuntu/Hyprland version. Earlier failed immutable releases remain historical
failures; this report does not change their contents.

Separately, the shared Window Controls menu passed the owner's local test after
plan 132. Ghostty padding was also confirmed working after configuration reload;
that is a private Ghostty setting, not a shipped Omabuntu configuration change.

These are human functional observations, not new automated measurements or
universal application/hardware/security guarantees. Automated evidence remains
in the relevant implementation documents and test reports.

## Native indicator checkpoint (plans 149–152)

The approved read-only Plan 148 inventory identified existing SwayNC/Hyprsunset
owners; machine snapshots remain private. Plan 149 now binds the original DND and
NightLight parents to one shared, fail-closed native owner, with generation/state
keys, one-setter readback and private before/outcome receipts. Optional Show/Hide
Status Indicators uses reversible layout preferences; twelve defaults/current
layouts are unchanged. Existing Kelvin/gamma/scheduling settings are preserved;
no daemon, GNOME-global preference or replacement panel is introduced. Unknown services
do not become fake inactive icons. See [native indicator contracts and recovery](native-indicators.md).

Plan 150 previously installed ten manifested paths and selected the optional
indicator entry through a backed-up appearance transaction, with an owned
session-lifetime bar restart and no wallpaper restoration. Its installed seals,
readiness/recovery routes, unchanged native/unrelated state and settled journals
were verified. Plan 146 was that checkpoint's immediate fallback and requires
undoing/hiding the optional entry before using its older validator. No native
setter, target daemon, package, privilege, security, autostart, binding or wallpaper
change was performed by that deployment.

Plan 151 responds to the owner's general-operation report and position/description
gaps; **Plan 152 now installs this correction locally**. A narrow stable-controls opt-in
reuses the original ordered/single block for the two known controls, preserving
positions and showing inactive controls dimmed rather than regrouping them.
Confirmed readback retains observed delegates behind a separate write fence;
busy/blocked state no longer disables hover. Four pinned original English labels
and observed-state tooltip refresh restore descriptions. Generic original grouping,
vendor parents, native contracts and uncertainty protections remain unchanged.
1,535 units, 39 contained frame cases, audio/tooltip/tray/network regressions and
142 source seals pass. Actual Qt input is synthetic/offscreen, not native desktop
acceptance. See [plan 151](../plans/151-stable-indicator-buttons-and-tooltips.md).
The separately approved Plan 152 deployment changes exactly seven manifested
paths, verifies all 142 installed seals and leaves runtime/helpers/manager/menu/
assets unchanged. The previously recorded bar had already ended and no same-user
Quickshell remained, so only the new managed session-lifetime bar was started,
without wallpaper restoration. Existing preferences/global buttons, all prior
native-action receipts and authoritative native before/after state/ownership are
unchanged; no native setter, new warning or unresolved journal remains. Plan 150
is the immediate retained fallback and accepts the selected indicator ID without
a visibility rollback. The owner subsequently explicitly accepted the installed
Plan 152 DND/nightlight buttons and tooltips as working as intended. Their
fixed-target interaction and tooltip-rendering acceptance item is closed.

Stay-awake, reminders, recording and remote providers are not enabled; passwordless
sudo remains excluded. The reported button/tooltip acceptance does not establish
broader colour/setter/security, recovery or unsupported-provider acceptance.
Query readiness and contained tests do not establish those properties either.

## Active expansion after acceptance

The owner subsequently requested implementation of areas A–E. This is tracked
in [plan 134](../plans/134-original-shell-a-to-e-expansion.md), separate from the
retired historical checklists. Its first implemented slice restores
the original per-application playback stream controls, identity-safe mutations
and keyboard navigation. A second slice restores the original
keyed bar pool, a closed per-widget registry, shared five-section layout
persistence/API and layout-order navigation with independent output pools.
A third prerequisite slice now connects the unchanged original move/remove
model operations to guarded expected-layout transactions, with stale-write
rejection and shared queue/conflict recovery. A fourth slice restores
the original widget pointer handlers, click/held feedback, open-panel marks,
spacers/outlines, ghost/settle/poof and conditional drag/removal writes. The bar
surface follows original full-screen/idle-input-strip ownership while reserving
only 26 logical pixels. The independent command menu can restore the default
widget order after removals. These four slices are now installed locally through
[plan 135](../plans/135-local-original-shell-installation.md), with only the owned
session-lifetime bar restarted. Startup/integrity, unchanged preferences and the
recovery route were verified; native interactive acceptance remains open.
The subsequent local [plan 144](../plans/144-local-original-shell-update.md)
installs completed source updates from Plans 136–139 and 141–143, retaining Plan
135 as the immediate immutable fallback. Exactly 23 manifested paths changed;
only the owned session-lifetime bar restarted, without wallpaper restoration.
Integrity/startup/recovery actions and unchanged preferences/global buttons were
verified. Plan 140's optional manual ALSA profile backend is not shipped or run.
No native interactive acceptance is inferred. This was the Plan 144 checkpoint;
Plan 153 below subsequently completes the admitted B source scope. A/C/D/E and
new native acceptance/deployment gates remain separate.
The owner's prior everyday/VM acceptance does not automatically accept new code.

## Owner observations after Plan 144

The owner reports fullscreen click-through working, media controls appearing to
work and Bluetooth being okay. These observations accept the reported everyday
paths only, not the full action/failure/device matrix or microphone/audio/security
behavior. A supplied private screenshot shows the media menu row without an icon;
Plan 145 adds the missing icon fields to both Show/Hide Media Controls; Plan 146
now installs them. No screenshot or machine-specific capture is imported into the
repository.

## Historical indicator-UI installation checkpoint (plan 146)

The approved five-path update installs the menu icon fix, original indicator UI
files and their Ui type registration. Only the owned session-lifetime bar restarted,
without wallpaper restoration. All 139 sealed sources, startup markers, installed
menu icons/recovery routes and unchanged preferences/global buttons verify. Native
runtime, manager, helpers, layout/defaults and services are unchanged. Plan 144 is
the immediate verified fallback. There are no pending update/deployment journals.
The indicator UI remains uninstantiated: no native status owner or visible reveal
is enabled by installing the files. Native pixel/input/security acceptance remains
separate. See [deployment and boundaries](../plans/146-local-indicator-ui-and-menu-update.md).

## What is still different from the original shell

The comparison baseline is Omarchy v4.5.0 at commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Older component import pins remain
recorded in their own provenance files. Plan 133 imported nothing. Plan 134's
subsequent BarModel import has its own source/license/tree/blob review and hash
record. Plan 137 also imports the unchanged MIT MediaModel.js and Service.qml
parents after pinned tree/blob/license review, initially deriving a read-only
shared media-selection owner. Plan 138 also admits the unchanged licensed media
BarWidget.qml and derives optional original controls with guarded transport.
These bounded reviews are not a line-by-line audit of the entire upstream shell.

### Shared shell, frame, theme and layout ownership

The selected entry remains `TrialShell`, with original components behind narrow
adapters, rather than the complete original `shell.qml` startup and services.
Original horizontal geometry/palette transitions are present. Plan 134 adds
original keyed WidgetPool/WidgetHost ownership, a closed Component registry,
shared five-section layout persistence and layout-order panel routing in source.
Plan 138 adds a thirteenth optional media Component while preserving the existing
twelve-widget defaults, with transactional Appearance Show/Hide Media Controls. Widget instances/state survive moves; each output owns its own pool.
The existing widgets share the common per-output bar API rather than separate
right-side/tray owners. See [frame implementation and boundaries](bar-frame.md).

The original model move/remove entry points now have conditional backend writes
and shared pending-error recovery. This guards cooperating writers, not native
pointer behavior, ABA revisions or races by uncooperative external editors.
Original widget drag/removal and visual feedback are now restored in source,
with contained handler/geometry checks, not native input-dispatch acceptance.
[Plan 142](../plans/142-original-fullscreen-bar-input.md) adds the
original per-output fullscreen observer and one shared event read refresh. The
stable bar surface chooses an empty input region under fullscreen/hide and cancels
owned drags without persistence; maximized mode retains the strip. This is an
input-ownership prerequisite, not native remap/click-through/focus acceptance or
complete visual fullscreen/peek policy. The existing reservation and geometry are
unchanged, with suppression-first drag precedence explicitly adapted for Ubuntu.
The implementation request made no desktop changes; Plan 144 subsequently
installs these sources without changing compositor configuration.
[Plan 143](../plans/143-original-bar-peek-ownership.md) restores the
original shared hover tally/120ms leave hysteresis, frozen per-output center-box
edge and ancestor HoverHandler in the existing frame. Late owner binding,
handoff/destruction and hide/fullscreen release are explicit Ubuntu seams; the
clock/weather API now reaches the independent shared suppression flag. No
admitted indicator yet consumes reveal state, so this is an ownership prerequisite,
not visible expansion or completed peek/popup policy. Three actual-owner contained
cases and source/model contracts do not establish native pointer/pixel acceptance.
Plans 136–139 and 141–143 are now locally deployed through Plan 144; broader
native acceptance remains open and Plan 140's optional backend remains uninstalled.
[Plan 145](../plans/145-original-indicator-reveal-ui.md) derives the
original active/inactive indicator blocks and BarIndicator visuals, preserving
fixed-edge growth, mirrored inactive order, clipping/opacity and hover delay.
Only caller-supplied prebound Components can load; defaults are empty and no
indicator is added to TrialPanel or the layout registry. Actual original UI runs
against synthetic statuses in contained tests, never fake live desktop states.
Plan 146 installs these files without instantiating them.
No Ubuntu status owner exists yet for the original seven indicator functions;
backend selection, notification ownership, security-sensitive exclusions and
separate deployment approval are prerequisites to useful visible desktop reveal.
Arbitrary plugin registry/startup, full theme services, bar-edge relocation,
nested tray layouts, full fullscreen/peek/reveal and popup policy, and reviewed
vertical/notch variants remain absent. Backend
and contained Qt/JS checks do not establish native, visual or pointer acceptance.
Closing the remaining gap needs further source-based shared-owner work and
narrow Ubuntu adapters, not whole-shell activation. It is not a request to replace
working panels with new authored approximations or to start the full upstream
shell with its unreviewed services. The current owner test does not establish
pixel parity with every upstream layout.

### Audio completeness

**Plan 153 completes the admitted B-audio source contracts, not deployment or
native acceptance.** See [audio completion and explicit exclusions](audio-completion.md)
and [plan 153](../plans/153-complete-audio-integration.md). Existing original typed
output/input/stream controls, master mute, media selection/transport and recognized
routing remain; there is no replacement audio panel.

The new source adds in-panel ALSA profile review/Apply/profile-only recovery,
current-card/native-owner/scope proofs, optional local pulse observation and
virtual-input gain/mute with private before/prepared/readback/uncertainty receipts.
Profile/control writers share a lock and cannot bypass unresolved preparation.
Metadata-backed custom DSP routes require unambiguous native links and retain
association in their route proof. Unknown, absent, recycled and ambiguous targets
do not get a fabricated fallback.

One nonvisual owner serves all outputs and reference-counts panel monitoring.
The original measured OSD/model and SizedImage slot are restored through closed
feedback and local-cache image admission. Profile/recovery rows join original
keyboard navigation. Plan 154 locally installs the optional helpers; bridge queries
are off until explicit UI consent, including transport-activation risk. Missing
dependencies/providers, malformed results, event loss and uncertainty disable
optional writes instead of installing, starting, retrying or compensating.

Remote artwork/arbitrary file URLs, Bluetooth/network profile policy, unproved
mixed virtual-input/DSP combined master, graph creation/rewiring, full topology
rollback, new bindings, package/daemon/security changes remain explicitly excluded.
The Plan 153 implementation was source-only. The separately approved
[Plan 154 deployment](../plans/154-local-audio-completion-deployment.md) now installs
exactly 23 manifested shell/audio-helper/provenance changes, with all 150 shell
seals verified and no new warnings or unresolved deployment/update journals.
Only the owned session-lifetime bar was restarted. Runtime/manager/menu/unrelated
helpers/assets, preferences and native receipts remain unchanged; wallpaper
restoration stayed disabled. Plan 152 is the verified immediate fallback.

The subsequently approved [Plan 155](../plans/155-audio-advanced-page-and-scrollbar-gutter.md)
UI correction is now installed: the technical block is behind **Advanced audio…**
on a separate page with **Back to audio**, and overflowing audio content reserves
a themed inner gap before the vertical scrollbar. Only three sealed shell files
and provenance changed; helpers/runtime/menu/assets remain unchanged. The managed
bar restarted without wallpaper restoration, new warnings or open journals;
Plan 154 is the immediate fallback. All 150 seals, 1,587 units and 43 contained
audio cases pass. Owner visual/audio acceptance remains separate.

The owner rejected Plan 155 visual spacing and clipped navigation. The approved
[Plan 156 correction](../plans/156-audio-panel-height-and-navigation-polish.md)
is now installed: natural content fits available screen height without the extra
560-unit cap, nested scroll extent is explicit, overflow clearance is balanced,
and advanced/back uses original icon buttons. Twelve-device contained fitting
and constrained last-action reachability checks pass, alongside 1,588 units and
43 audio cases. Only two shell files and provenance changed; Plan 155 remains
the immediate fallback. The owner subsequently explicitly accepted the corrected
Plan 156 audio view visually. That layout confirmation is closed; the new audio
functional live matrix remains separate and pending.

[Plan 157](../plans/157-audio-stream-labels-and-heading.md) now installs a label-only
refinement: APPLICATION AUDIO replaces the raw audio.sources key, and duplicate
application names include a server-local Stream #serial plus supplied bounded
media descriptors when available. These are not participant identities and no
browser/meeting inventory is collected. Rows and controls stay independent;
layout and its owner acceptance remain unchanged. All 150 seals, 1,590 units and
43 isolated audio cases pass, with no new warnings/open journals. Only two shell
files and provenance changed; Plan 156 is the immediate fallback. Owner
confirmation of the new labels remains separate from broader live audio checks.

The optional bridge remains disconnected until explicit UI consent. Deployment
issued no optional audio query/subscription/setter/profile change, package/service
action, binding/autostart change, commit or publication. Existing owner everyday
acceptance is preserved, not generalized into new profile/call/hotplug/native
input/pixel/OSD-coexistence/security acceptance.

### Bluetooth and native policy integration

**Plan 158 completes the admitted C source integration; owner-approved Plan 159
now installs it locally, without claiming hardware/security acceptance.** Original panel/layout, typed observations and
shared discovery remain. A shared authored QtCore/QtDBus agent supplies transient
original-toolkit PIN/passkey/confirmation/authorization/display dialogs,
structured asynchronous connect/disconnect/forget results, owned cancellation,
source/owner/row/scope fencing and explicit uncertainty acknowledgement without
replay. It never requests default-agent takeover, installs packages, activates
BlueZ or writes trust. Unsupported service authorization refuses. The helper
starts only on an explicit device action, not component/panel startup.

1,597 units, 22 private-bus native scenarios, seven actual contained QML/Process/
prompt cases, desktop/clock and audio/frame/tooltip/clean-source regressions pass.
The source-check bundle verifies all 152 seals, exact helper bytes, manifest and
test-build rejection. Plan 159 installs exactly ten manifested changes derived
from Plan 157: six shell files, the production helper, manager/updater helper-path
exports and provenance. The managed session-lifetime bar alone restarted with
wallpaper restoration disabled; all installed seals match, zero new warnings or
unresolved journals, preferences/native/audio receipts preserved. Plan 157 is
the verified immediate fallback. The Bluetooth helper is not running: no live
agent registration, pairing or other native Bluetooth action was issued by the
deployment. New authentication/device behavior remains owner-unverified. See
[owned Bluetooth completion](bluetooth-completion.md).

Radio retention still deliberately uses BlueZ Powered, not persistent rfkill.
Default-agent/incoming takeover, automatic trust/reconnect, persistent radio or
connection/profile policy, PAN/file transfer and automatic default-audio routing
are explicitly excluded, not hidden unfinished C promises. They require separate
ownership/recovery/security scope; source completion does not authorize them.

### Displays, power and input methods

Brightness and runtime scale remain installed and owner-accepted. **Plan 160 now
implements D in source; owner-approved Plan 161 now installs it locally**: named persistent output profiles,
advertised modes/positions/transforms/scales, guarded enable/disable, saved-layout
review/apply/keep/restore, durable independent confirmation recovery, previous
layout drafts and original shell-local text-size controls. One shared owner
supports explicitly approved previously kept exact-topology login/hotplug
reapplication, not an external-writer override loop or new autostart/service.

1,624 units, seven real-process isolated fake-IPC recovery/startup/hotplug cases,
actual contained original-popup/profile/Process/text-readback controls and audio/
frame/tooltip/desktop/clock/clean-source regressions pass. A private source-check
bundle verifies all 154 seals, exact helper/manager bytes, manifest and runtime
preflight, retaining the Bluetooth helper. Plan 161 installs a narrow thirteen-
file derivative: seven shell files, three display helpers, manager/updater export
and provenance. Fresh 1,625 units (28 focused profile cases), seven private IPC
scenarios, QML and preflight pass. Legacy current-state permission compatibility
is corrected without chmod. All 154 installed seals match; zero new warnings or
open journals; settings/receipts/runtime/assets/menu/audio/Bluetooth preserved.
The bar alone restarted with session lifetime and wallpaper restoration disabled;
Plan 159 is immediate fallback. Read-only before/after geometry and installed
status RPC pass; profile/text paths remain absent and automation is off. Native
device/login/hotplug/
pixel/recovery/security acceptance remains separate. Advanced color/VRR/mirroring,
full monitor-rule or window/workspace placement rollback and GNOME/global app
text sizing are explicit exclusions. See [monitor profiles](display-profiles.md).

The power panel uses Ubuntu's existing power-profiles-daemon. Upstream's automatic
AC/battery policy is not installed, and unsupported cycle/charge-limit readings
remain unavailable. Charge-limit writes are not implemented. These are explicit
policy boundaries, not defects proved by a missing number in the panel.

Configured XKB layout switching is separate from an input-method service such as
fcitx; the original input-method integration is not ported.

### Optional source features and deliberate exclusions

The full upstream dock screen-remap service and arbitrary shell/plugin/layout
registry are absent. Existing dock and monitor behavior passed the owner's test;
that does not establish implementation of every upstream service.

Agents, dictation, live wallpaper and other unadmitted services are not included.
World Clock/weather notification, IPC, profile-fetch and system-timezone actions
remain deliberately narrower. Additional Setup/Trigger/About and menu modes are
not all ported. The Ubuntu application-update menu exists; upstream Arch package
installation/removal, provisioning and migration routes remain excluded, not a
pending request to translate them automatically.

Plaintext network-password reveal, arbitrary upstream helper execution and
unreviewed enterprise-profile creation remain excluded. No omitted feature is
automatically necessary for daily use or approved for implementation.

## Security, failure cases and future release gates

The owner's security assessment was "should work", not a report of new security
tests. Keep the earlier successful manual lock/unlock acceptance, but do not mark
wrong-password handling, long-duration/reconnect/DPMS cases, corporate-policy
review or automated idle/lid/suspend integration newly accepted. See
[lock readiness](lock-readiness.md). No such activation is authorized here.

Real power-loss and interrupted package-manager recovery are not newly verified
by the general VM report. Existing recovery tooling and fixtures keep their
recorded scope. A future source revision still needs license/provenance and
version review. Any new release needs its own privacy/distribution review and
explicit commit/publication approval; local acceptance is not publication.

## How to use the remaining work

There are no remaining unchecked historical Markdown tasks after plan 133.
The feature differences above are a descriptive decision list, not a claim that
all original features must be added. Choose one desired behavior before writing
its next implementation plan. Desktop edits, packages, services, reloads,
autostart, supervision and session/security transitions retain their existing
approval and backup gates.
