# Omarchy upstream gap analysis

## Goal

Analyze the gap between Omabuntu's reviewed Omarchy baseline and current public
upstream Git references, then recommend a bounded Ubuntu-native update sequence.
This request authorizes analysis, not imports, pin changes or desktop deployment.

## Evidence to compare

- Omabuntu baseline: `omacom/omarchy` commit
  `03ff1eff3812933f7088484533784d2f63eaf19a` (recorded v4.5.0-rc1).
- Resolve current upstream default branch, tags and releases from GitHub, and
  compare immutable commit trees and changed source where available.
- Compare affected upstream files to Omabuntu's source-derived profiles,
  adapters, provenance metadata, tests and documented integration boundaries.
- Existing capability documents are historical evidence, not a fresh live
  acceptance record. Exact current upstream commits will be recorded in the
  analysis after lookup; missing refs and partial API results stay explicit.

## Current gaps and proposed shape

Omabuntu has per-component provenance and adaptations, not a mergeable upstream
checkout. A newer root pin alone cannot update derived QML, helper semantics,
assets or dependencies. Inspect direct and transitive changes, preserve narrow
Ubuntu backends, and classify useful changes separately from excluded Arch
provisioning and security/session policy. Produce an English summary under docs/
with recommended priorities, acceptance gates and explicit limitations. Raw API
results and downloaded review text remain under ignored work/.

## Safety and exclusions

Do not execute downloaded scripts, installers, migrations, package recipes or
services. Do not modify the separate reference package, installed configuration,
Git remotes, dependency pins or session state. No package installation, lock,
idle, suspend, security policy or corporate management changes. Review licenses
before any later code/asset import. Preserve the accepted explicit SDR default
(`render.cm_auto_hdr = 0`) and original component/layout fidelity. No commit or
publication is authorized by this analysis request. Back up existing paths before
any edits; the planned report is a new file.

## Tasks

- [x] Resolve current upstream refs and compare them with the pinned baseline.
- [x] Inspect relevant source changes, dependencies and license boundaries.
- [x] Map changes to Omabuntu implementation and remaining fidelity gaps.
- [x] Write prioritized findings, exclusions and an update recommendation.
- [x] Run `python3 -m unittest discover -s tests -v` and check the final diff.

## Outcome

The report is `docs/omarchy-upstream-analysis.md`. Current observed targets are
v4.5.0 (`ac2690cd7be4f47e4a255f5e2e78d904d436b068`) and the divergent quattro
head (`6194f4606c585da8b839b87df9120b7d796afedf`). Complete tree comparisons and
all 410 development comparison commits were collected privately. All 71 mapped
vendor parents match the current baseline; 22 change in stable and 26 in
quattro. Selected pure extraction tests expose network/weather blockers for both
targets and additional display/dock blockers for quattro. The upstream HDR
workaround agrees with plan 076. All 1068 unit tests passed. No source or runtime
pins, installed paths, desktop state, Git remotes or reference material changed;
no upstream code was executed or imported. No commit was made.
