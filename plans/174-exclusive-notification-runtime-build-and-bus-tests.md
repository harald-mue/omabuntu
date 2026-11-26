# Exclusive notification runtime build and private-bus tests

## Goal and evidence

Build Plan 173's exact exclusive-registration patch against pinned Quickshell
`2b4501a282689792b62e94f3fb30d8f512324fe6` and test the actual NotificationServer
on disposable private D-Bus instances. Original notification UI remains pinned to
Omarchy `ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Compare the validated baseline
build/stage, source lock, exact server source/patch hashes and actual ownership
results, not just the patch text or synthetic QML server. End any still-owned
session crash supervision without affecting unrelated debuggers.

## Gaps and proposed shape

At plan creation the patch was not built and the baseline runtime retried after
a competing owner's exit. Create a separate variant build, with a recorded baseline and complete
artifact hashes, under ignored work/. Never mutate the existing build or relabel
a patched variant as the unmodified source recipe. Use network-free Bubblewrap
builds and fixed private-bus probes covering free-name acquisition, conflict,
no replacement/queue/late takeover, clean exit and bus loss. Produce a verifiable
artifact-bound eligibility receipt only after the actual checks pass. This is
not a live deployment grant or a producer for the current host's admission flags.

## Safety and exclusions

Back up each changed existing project path first. Preserve installed releases,
SwayNC configuration/service/activation, GNOME notification ownership, private
notification history and crash evidence. No host notification bus, compositor,
GPU/input, package installation, live notification, DND setter, service reload,
installation, autostart, live shell restart, commit or publication. Disposable
test daemons and probe lifetimes are explicitly bounded; no timeout is added to
normal desktop components. Do not kill arbitrary GDB processes or an untraced
ordinary shell. Live migration and rollback remain separately approved work.

## Tasks

- [x] Record prestate; verify debug ownership and close any remaining owned capture.
- [x] Implement/verify the variant build and exact patch application.
- [x] Build the patched runtime without modifying the baseline stage.
- [x] Exercise actual native registration/ownership on private buses.
- [x] Seal/verify candidate eligibility and add refusal/tamper regressions.
- [x] Run full unit/source checks and document results and remaining live gates.

## Completed checkpoint

A separate clean Quickshell build uses only the locked local archive and verified
baseline cpptrace stage in network-free Bubblewrap. The exact-source patch also
fails closed on missing/disconnected buses; its 500ms health check is not a normal
component lifetime timeout. Only the executable differs from the baseline stage.
No installed artifact is changed and no alternate runtime is silently accepted as
an ordinary source recipe.

Six actual private-bus checks pass: free-name acquisition/native Notify/clean exit,
replacement refusal, conflict refusal with no queue or later takeover, an
unpatched negative control reproducing late takeover, missing-bus failure and
bus-loss failure with no takeover after private-bus recreation. The first probe
attempt lacked a synthetic passwd/group view and bus connection policy; its
failed receipt/logs remain preserved. The corrected fixture exposes only minimal
synthetic identity files and a disposable bus without activation service paths.

The artifact/checker-bound eligibility receipt verifies and explicitly does not
authorize live deployment. Twelve refusal/fixture regressions accompany the
1,688-test checkpoint. Plan 175 completes this documentation and adds a separately
selected inactive review package; its full unit and contained source regressions
also pass. Current contracts and live exclusions are in docs/notifications.md.

Private prestate, patch/build/test/eligibility reports and logs remain under
ignored work/. No SwayNC configuration/service, notification/DND state, installed
runtime, desktop configuration, package, service, autostart, commit or publication
was changed. The initial read-only debug check found no active owned capture or
traced managed shell; it did not kill an unrelated debugger or ordinary shell.
Subsequent explicitly requested crash-capture restarts are separate Plan 169
operations, not permission for notification preparation to interrupt tracing.
