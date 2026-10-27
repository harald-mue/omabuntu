# Refresh installation status and the guided-installer roadmap

## Goal and evidence

Document the existing release installer accurately and make prerequisites,
manual approval boundaries and missing first-install capabilities clear.
Compare README.md, docs/user-installation.md, docs/dependencies.md,
docs/package-plan.md, docs/plan.md and the implemented tools/package_user.py
and tools/user_install.py. Use the recorded .23 deployment and the user's
hyprpaper and Qt image-plugin installations as evidence, not as a claim of
fresh-machine acceptance. The pinned Omarchy source remains
`03ff1eff3812933f7088484533784d2f63eaf19a`; this work changes documentation,
not upstream behavior.

## Gaps and shape

The installation guide still names .19/.18; the project roadmap describes
an earlier stage. The existing tool deploys verified user releases but does
not install packages or integrate a new desktop. Add a dedicated guided
installer roadmap and connect it to current installation and dependency
guides. Document APT simulation, runtime versus build dependencies,
functional probes, backup/apply gates and separate rollback domains.

## Constraints and exclusions

English documentation only. No package installation, source changes,
configuration edits, runtime deployment, service activation, session changes,
commits or publication. Do not add machine inventories or raw logs. A
roadmap is not approval to implement or activate a system installer.

## Tasks

- [x] Correct current installation status and document prerequisites.
- [x] Document the guided-installer design and remaining acceptance gates.
- [x] Update README and roadmap links; clarify package-plan scope.
- [x] Run the required verbose unittest suite and update WORKLOG (427 tests
      pass; local file links in the changed guides resolve).
