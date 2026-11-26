# Native notification history, redaction and transience

## Goal and evidence

Exercise actual native NotificationServer ingestion and original persistence/replay
for Omarchy `ac2690cd7be4f47e4a255f5e2e78d904d436b068`, using the verified exclusive
Quickshell `2b4501a282689792b62e94f3fb30d8f512324fe6` runtime and existing private
Labwc/Pixman/SHM + Qt OpenGL/llvmpipe lab. Compare Plans 173/178's model/persistence
checks, Plans 179–180's native interaction evidence, and original Store/Service
transient, code sanitisation, restore, six-row replay and 100-row/24-hour limits.

## Gaps and shape

Existing native checks do not comprehensively prove redaction/transience across
real Notify updates, disk writes and private process restart. Add a separate
fixture around the unchanged sealed service. Send fixed synthetic ordinary,
transient, replacement and verification-code messages over the private bus.
Validate bounded owned private files read-only, report only counters/assertions,
and observe actual replay/restore cards without clicking code/URL/actions.
Restart only owned fixture processes, preserving test-state checkpoints before
intentional reseeding. Seed bounded synthetic retention edges after the fixture
stops, never alter host state or wall clock. Include transient-to-persistent and
persistent-to-transient replacements, redacted live/history/restart, recent replay,
retention count/age and capability-field exclusions actually guaranteed by source.

## Safety and explicit exclusions

No host notification/history/clipboard collection, live DND, code copying, URL/app
launch, host sockets/buses/devices, package/download/build/install, live provider/
SwayNC/shell/GDB operation, session/security change, commit or publication.
Keep the verified lab/runtime read-only, private bus activation disabled, synthetic
state/captures/failures under ignored work/, bounded diagnostics and owned cleanup.
Back up existing edited project paths with hashes/modes. No normal component
lifetime wrapper or automatic live admission is introduced.

These are synthetic filesystem/model/native-surface checks, not clipboard or
locked-session secrecy, adversarial security, production app acceptance, Hyprland
policy, crash diagnosis or approval for reversible live migration.

## Tasks

- [x] Reverify lab/runtime/source and define bounded private state assertions.
- [x] Implement native history/transient/redaction/restart/retention fixture.
- [x] Run actual native cases and preserve failures/state checkpoints.
- [x] Add synthetic refusal/regression tests; run full units/source export.
- [x] Verify backups/inputs and document bounded acceptance and remaining gates.
- [ ] Resolve the native layout binding-loop gate before accepting this checkpoint.

## Results: functional checks observed, native acceptance blocked

Seven functional cases pass: ordinary/transient storage exclusions; native
transient replacements in both directions; live/history code redaction; private
restart restoring only a redacted persistent card; six-row replay without duplicate
history or native sender actions; legacy-code sanitisation and 24-hour retention;
and the 100-row cap/newest ordering. The service, cards, surfaces and shaders stay
unchanged. Private state reads enforce bounded owned 0600 exact schemas without
repair; intentional reseeds occur only after owned fixture shutdown and hashed
state checkpoints.

The full native diagnostic exits nonzero because the original readonly layout
binding reports loops. Phase counts first increase in code live/history handling
and later in mixed history replay. Ordinary/transient/replacement phases and the
third process's legacy restore/retention checks are clean apart from the expected
absent-Hyprland warning. The exact trigger remains unresolved. Smaller private
ordinary/code controls are clean without/eager row metrics and with matching
synthetic sender metadata; these variants are not full-history acceptance.
No warning is suppressed or production code modified to obtain a pass. This
finding does not establish causality for the prior live native crashes.

Failed full runs, clean diagnostic controls, two synthetic redacted/replay captures,
active state and pre-reseed snapshots remain private. Synthetic raw legacy seed
artifacts contain the authored fake canary deliberately; absence assertions apply
to the active sanitised store, not every artifact. No real notification content,
clipboard, DND, shell/provider/debugger/session/security state is inspected or
changed. Owned children are reaped and read-only lab/runtime/source inputs remain
unchanged. No download/install/build, live restart, commit or publication occurs.

Fourteen new synthetic state/refusal/diagnostic regressions and all 1,773 unit
tests pass; all nine clean-source checks pass without original lab/runtime/work
inputs. Three existing document backups verify by hash/mode, along with fixture/
dependency hashes, active store constraints and all private state checkpoints.
Repeated full native runs retain four layout-loop warnings across the first two
process generations; the third has only the expected unavailable-Hyprland warning.
Synthetic diagnostic regressions keep binding loops as failures. The open acceptance task above is intentional: completion of fixture
implementation and source checks must not relabel the blocked native checkpoint.
