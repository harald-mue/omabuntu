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
a visibility rollback. Native visual/tooltip/pointer acceptance is still pending.

Stay-awake, reminders, recording and remote providers are not enabled; passwordless
sudo remains excluded. Native glyph/pointer/colour/setter/security acceptance
remains with the owner. Query readiness and contained tests do not establish it.

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
No native interactive acceptance is inferred. A/B remain partial and C/D/E remain outstanding.
The owner's prior everyday/VM acceptance does not automatically accept new code.

## Owner observations after Plan 144

The owner reports fullscreen click-through working, media controls appearing to
work and Bluetooth being okay. These observations accept the reported everyday
paths only, not the full action/failure/device matrix or microphone/audio/security
behavior. A supplied private screenshot shows the media menu row without an icon;
Plan 145 adds the missing icon fields to both Show/Hide Media Controls; Plan 146
now installs them. No screenshot or machine-specific capture is imported into the
repository.

## Latest local installation (plan 146)

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

Output/input selection, volume, mute and microphone peak meter already work.
Per-application stream controls from plan 134 are now installed locally under
plan 135; native acceptance of these new controls remains open. Remaining differences include device/profile controls,
virtual/untyped-source fallback, comprehensive virtual-to-physical sink resolution
and the original OSD paths.
[Plan 137](../plans/137-original-media-selection-and-audio-labels.md) now restores
original reactive active-player selection, MPRIS-aware stream labels and active
row presentation. A single shared owner keeps history consistent across outputs;
only frozen primitive metadata reaches rows. Plan 138 extends it with the
original optional media widget/popup and explicit generation-bound transport.
Current identity/capability checks reject missing, stale/recycled or ambiguous
targets without fallback; source selection changes the in-memory preference only.
Artwork/OSD/volume keys/external helpers remain excluded. Native request issuance
is not playback acceptance or a DBus unique-owner compare-and-swap, and full
asynchronous server-error/focus/input/pixel acceptance remains open. Plans 137/138
are deployed through Plan 144, not natively accepted.
[Plan 136](../plans/136-remaining-original-shell-integrations.md) now restores the
original two-channel master semantics with serial/default preflight and explicit
output/microphone scope. Plan 144 now deploys it: unlike historical Plan 135,
the hero/right-click master affects both channels. Native acceptance remains open.
[Plan 139](../plans/139-native-audio-volume-routing.md) now separates
selected output from the loudness target for recognized DSP/EasyEffects endpoint
routes. Output gain/mute and combined master requests revalidate captured native
identity/generation/route proofs; ambiguous, unready or missing routes never fall
back to DSP gain. Existing original controls remain, with disabled gain and an
explicit unknown percentage when unresolved. Routing observations are not native
link-health, hardware identity, server-transaction or hotplug acceptance. Idle
EasyEffects config fallback, application-name inference, unrecognized custom DSP,
profile UI and untyped sources remain open. The pinned native QML API has no profile
switching contract; no profile stub or replacement panel was added. Source-only
[plan 140](../plans/140-guarded-alsa-profile-backend.md) adds a functioning manual
[ALSA profile backend](audio-profile-backend.md) through an optional, separately
supplied Ubuntu pactl executable. It has strict running-local-server/card identity,
digest review, private before/prepared receipts and explicit profile-only recovery,
not shell/menu/installer wiring or full topology rollback. Ambiguous/partial/stale
state refuses; uncertain native requests never automatically retry or compensate.
Connecting has an explicitly consented socket-activation race risk, not an absolute
no-activation guarantee. No host audio command/query/change, deployment, package,
restart or activation was performed by that backend request, and Plan 144 excludes
that optional backend.
[Plan 141](../plans/141-native-microphone-ownership.md) strengthens the existing
original microphone surface with frozen serial/native-object-generation/provider
proofs, actual-default/readiness/unique-membership guards for local gain/mute,
and guarded preference-only input selection. The master validates the input proof
before either setter; unsupported present defaults are not treated as absent.
Missing authority disables the original input slider, and synchronous failures
report uncertainty without retry or compensation. No untyped input setter/helper,
new tracker/peak/recording policy or new panel is admitted. Plan 144 deploys
these shell integrations, excluding Plan 140; native protocol/hardware/recovery/
policy acceptance, untyped fallback
and a profile surface remain open.

Implementing these would require extending the original surfaces and reviewed
PipeWire/WirePlumber actions, handling disappearing devices and explaining each
behavior change. Native service-owned state must not be duplicated blindly into
an Omabuntu JSON preference file.

### Bluetooth and native policy integration

Pair/connect/disconnect/forget and owned discovery exist. The full original
status/error behavior and an owned pairing-agent integration are not complete.
Plan 136 adds bounded connect/disconnect/forget tracking, observed
pairing follow-up, duplicate rejection and adapter/device disappearance handling.
The pinned native API exposes no structured operation-error signal; invocation
exceptions/deadlines report uncertainty rather than claiming success. This is
deployed through Plan 144, but does not supply an owned authentication agent.
Radio retention differs: the Ubuntu adapter uses BlueZ Powered, while upstream
uses a persistent rfkill-oriented helper. Automatic Bluetooth-to-default-audio
routing is also not ported.

Persistent radio policy or automatic routing would require a separate Ubuntu
ownership/recovery design and approval; the working device panel does not
implicitly authorize rfkill, service, trust or policy changes.

### Displays, power and input methods

Brightness and runtime scale work. Persistent per-output scale/layout settings,
output enable/disable, topology editing and text-size controls are not offered.
Supporting them would require conflict-aware native configuration updates,
per-path backups and safe recovery when outputs disappear or geometry overlaps.

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
