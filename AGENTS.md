# Omabuntu development instructions

## Language and scope

Write every project file, comment, document, and commit message in English.
Build an Ubuntu-native, reversible desktop integration, not an Arch installer.
Keep private reference material and machine-specific data out of Git.
Do not modify the separate source reference package.

## Safety

- Diagnose before changing configuration.
- Never run Omarchy installers, migrations, provisioning, or Arch system tools.
- No boot, kernel, PAM, sudo, firewall, security-policy, or management changes.
- Preserve GNOME, login, VPN, certificates, keyring, Secure Boot, and corporate agents.
- Ask before package installation, additional package sources, privileged actions,
  desktop changes, service activation, reloads, and session transitions.
- Back up each affected path and record its previous state before applying changes.
- No lock/idle/suspend activation until authentication and recovery are verified.
- Do not expose an unreviewed Omarchy bin directory through PATH.
- Do not request or print credentials.

## Implementation

User preference: normal desktop components must not expire on a timer. Since
2026-10-24, use an explicit session-lifetime grant for approved live components;
reserve timed runs for explicitly requested disposable diagnostics. Do not
silently add a timeout wrapper. Session lifetime is not autostart or crash
supervision; those remain separate, backed-up deployment approval gates.

Use Python 3 standard library for orchestration unless a dependency is justified.
Doctor must remain read-only apart from private reports under ignored work/.
Keep probe timeouts and report missing commands, timeouts, and partial failures.
Do not treat successful collection as functional or security acceptance.
Configuration must match the documented target Hyprland version.
Check official version-appropriate documentation before configuration work.
Preserve the original shell as the preferred goal; agree on substitutes explicitly.
User feedback: assembling original primitives into simplified, authored panels is
not sufficient fidelity. Prefer the original component/layout source with narrow,
reviewed Ubuntu backend adaptations. Do not add more replacement panels as a
substitute for correcting the shared frame, visual hierarchy and interaction.
Document every excluded feature; source fidelity is not pixel or live acceptance.

## Publication and provenance

Do not import upstream code/assets before checking licenses and recording origin.
Do not commit snapshots, raw inventories, backups, corporate data, or credentials.
The project license is MIT, approved by the user. Preserve third-party licenses.
Do not publish a remote/release or change the project license without user approval.
A .gitignore is not a secret scanner or a publication approval.

## Plans

Write implementation plans in English under `plans/` before non-trivial work.
Name each file `NNN-kebab-case-topic.md`. Use the next free three-digit prefix,
starting at `000`; never renumber or overwrite an existing plan. One request
got one plan.

A plan states the goal, the evidence compared (including the pinned upstream
commit when Omarchy behavior matters), current project gaps, safety
constraints, the proposed shape, explicit exclusions, and checkbox tasks
(`- [ ]`). Check a task only after that task is done. A plan is not approval to
edit the desktop, bind keys, install, restart, or commit. Keep machine-specific
bind dumps, logs, and secrets out of the plan.

## Verification and Git

Run python3 -m unittest discover -s tests -v after changes.
Do not commit without asking. Use English Conventional Commits.
