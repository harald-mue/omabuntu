# Artifact-bound inactive notification package

## Goal and compared evidence

Continue after the verified Plan 174 build/private-bus checkpoint. Bind an
explicitly selected exclusive runtime to an inactive local review release and
preserve independently inspectable patch/build/test provenance. Compare pinned
Quickshell `2b4501a282689792b62e94f3fb30d8f512324fe6`, the exact exclusive patch,
Plan 174's eligibility/build/native-bus receipts, the unmodified parent stage and
Omarchy `ac2690cd7be4f47e4a255f5e2e78d904d436b068` notification source closure.

## Current gaps and proposed shape

The generic packager accepts only ordinary builds, while the separate verified
variant is intentionally outside that namespace. Documentation still describes
Plan 174's completed build and tests as outstanding. Add an explicit optional
variant argument that requires the verified parent build, successful artifact-
bound eligibility, exact source closure and matching copied runtime. Preserve the
normal package path. Include a bounded, offline-readable capability descriptor,
patch and exact private evidence; make its validator reusable by a future migration
controller. Relocation changes only the reviewed qs alias. Never infer a live role
from a capability descriptor, package installation, environment or UI setting.

This slice prepares artifact capability proof, not the current host's deployment
approval producer. Both host admission booleans stay false by default. Native
surface/input acceptance and an approved single-owner migration remain open.

## Safety and exclusions

Back up every affected existing project file with hashes/modes. Write output only
under ignored work/. No installed release, shell/debugger restart, capture stop,
SwayNC configuration/service/autostart/D-Bus activation change, host notification
bus probe, notification/body/history collection, DND setter, package installation,
compositor/GPU/input exposure, new service, commit or publication. Preserve prior
failed test evidence and all diagnostic/recovery data. A capability proof is
local integrity/provenance evidence, not a signed adversarial attestation or live
migration approval. Preserve all third-party notices and ship the exact patch.

## Tasks

- [x] Reverify eligibility and back up changed existing paths.
- [x] Add explicit inactive variant packaging and offline artifact proof validation.
- [x] Test default inactivity, parent mismatch, evidence/runtime/source tampering and relocation.
- [x] Prepare and verify a real inactive local review release without starting it.
- [x] Complete Plan 174's documentation and update source/deployment boundaries.
- [x] Run full units, contained source regressions and whitespace/backup checks.

## Implemented scope and evidence

The packager's optional --notification-runtime accepts only the separate variant
whose current eligibility, parent report and parent stage all verify. The ordinary
path remains unchanged and creates no capability descriptor. Additional optional
runtime attachments are rejected for the exact-manifest variant path. Runtime
sources/notices retain the verified baseline parent; the patch and native
build/bus/eligibility/source witnesses ship as private package evidence.

The standalone standard-library validator is read-only and checks evidence
relationships, exact source closure, complete digests, copied verifier and full
relocated runtime. Only qs's relative alias is adapted. It never reads notification
state, starts processes, accesses a bus or changes host admission flags. Capability
success always returns deployment_approved false. This is local integrity and
provenance evidence, not signed attestation against arbitrary same-user edits.

Sixteen new regressions cover default inactivity, explicit variant selection,
wrong/unverified parent, relocated alias, altered runtime/source/verifier/evidence,
incomplete/resealed failed bus results, missing digests, unexpected symlinks and
hardlinks, path escape and attempted live grants. A real local package passes
all 469 release-file seals and its own offline capability validator. Intermediate
private review versions are retained; no release selector is changed.

The full suite passes 1,704 tests. Contained original notification/card checks,
42 audio, 39 frame, desktop and five clock checks pass. Backup hashes/modes for
all five changed existing paths verify. All nine final clean-export checks and
tracked/new-file whitespace checks pass. Results are recorded with the remaining
run evidence under work/notification-package-175/.

The host admission/migration producer, native compositor/surface/input/action
acceptance and separately approved reversible SwayNC transition remain excluded.
Neither the running crash capture nor any installed shell/provider is touched.
