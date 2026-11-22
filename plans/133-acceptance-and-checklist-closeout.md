# Record owner acceptance and retire historical open checklists

## Goal and evidence

Record the owner's confirmation that the everyday tests listed in the preceding
project review passed and that the installation/deployment review was exercised
on a VM. Explain remaining original-shell implementation gaps and remove stale
open checklist entries. The source comparison remains Omarchy v4.5.0 at commit
ac2690cd7be4f47e4a255f5e2e78d904d436b068; this is a documentation reconciliation,
not a new upstream audit or import.

## Current gaps

Historical plans retain unchecked tasks after subsequent implementation,
replacement, publication or owner testing. Current summaries still describe
some owner-tested behavior as awaiting interactive acceptance. Actual omitted
features, security gates and exceptional failure cases must not be mistaken for
completed implementation merely because old checkboxes are removed.

## Shape and safety

Create one current status document separating owner-reported acceptance, real
feature gaps, deliberate exclusions and unverified safety/failure cases. Link
current capability, bar, installer and preference-repair summaries to that record.
Complete directly supported checklist items; remove the remaining historical
open task entries with explicit retirement notes rather than falsely checking
them. Keep historical evidence and technical exclusions intact. Back up every
existing edited file and record hashes/modes privately under ignored work/.

No desktop/configuration changes, reloads, locks, session transitions, package or
service actions, upstream imports, release/publication actions or commit.
"Should work" is not a security-test result or permission to activate anything.
The VM report does not supply a detailed scenario/version matrix or evidence of
real interrupted APT/power-loss recovery. Do not invent such evidence.

## Tasks

- [x] Review current summaries, historical open entries and source exclusions.
- [x] Save private prestates for every existing documentation path to be edited.
- [x] Record accepted tests and the remaining original-shell feature boundaries.
- [x] Retire stale checklists without converting untested safety cases to passes.
- [x] Verify documentation links/whitespace and run the complete unit suite.

## Outcome

Added docs/project-status.md as the current owner-acceptance and source-parity
summary and linked it from README and the current capability/deployment guides.
The everyday checks and VM report are recorded as owner-reported passes, without
inventing per-version, exceptional-failure or security evidence. Four historical
items were completed with that scoped report; 58 other unchecked entries were
retired across the old plans and guided-installer checklist. Retirement notes
preserve the distinction between stale tasks, actual feature gaps and unchanged
approval gates. The abandoned launch-wrapper plan remains explicitly superseded.

All 1,330 unit tests passed. Added local documentation links and whitespace were
checked. No desktop, private configuration, runtime, service, package, release,
commit or publication operation was performed. Existing file prestates and test
logs remain private under ignored work/.
