# Default installer confirmations to Yes

## Goal and evidence

Honor the user's preference for Enter to accept normal install.sh confirmations.
Compare checkout setup stage prompts and published-install prompts: both currently
show [y/N] and reject empty input. No upstream desktop behavior changes; Omarchy
comparison/pin is not relevant to this terminal-only change.

## Shape and safety

Use a shared [Y/n] confirmation helper for ordinary installer Yes/No questions.
Accept Enter, y and yes (case-insensitive, surrounding whitespace ignored).
Explicit n/no and other answers decline. EOF must decline, never grant consent.
Keep each independent approval prompt and warning, terminal/apply/digest guards,
package policy, backups, typed migration/recovery phrases and opt-in CLI flags.
Changing the default is not an unattended --yes mode or authorization to apply
anything during implementation. APT, sudo and hyprpm's own prompts are unchanged.
Commit/publication/signing prompts are outside install.sh scope and unchanged.

## Exclusions

No real installation, package/manager action, live activation, desktop/session
change, deployment, commit, push or publication. Existing published archives and
immutable installed helpers are not rewritten.

## Tasks

- [x] Back up affected implementation, tests and documentation.
- [x] Share affirmative-default confirmations across both installer routes.
- [x] Cover Enter, explicit declines, EOF and retained special approval gates.
- [x] Document the prompt default and unchanged independent consent boundaries.
- [x] Run full unit tests, clean-source verification and whitespace checks.

## Verification

925 unit tests passed, including affirmative Enter handling in both installer
routes, explicit No/unknown/EOF refusal, interruption and preserved exact typed
migration/recovery challenges. Clean-source verification and whitespace checks
passed. No actual installer stage, desktop change or publication was performed.
