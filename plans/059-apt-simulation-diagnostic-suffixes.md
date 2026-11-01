# APT simulation diagnostic suffixes

## Goal and evidence

Recognize the trailing bracketed dependency diagnostics in the user's APT
simulation without misreporting otherwise valid upgrade lines as parse errors.
The supplied examples include empty brackets, package/architecture lists and
`package:architecture on package:architecture` diagnostics. The current parser
requires the version/origin parentheses to end the line.

This is APT output parsing, not Omarchy behavior; no upstream Omarchy pin is
relevant. Existing package transaction summarization correctly identifies the
installed-package changes and must continue to block them.

## Shape, safety and exclusions

Accept only a restricted trailing diagnostic grammar after the existing version
and origin fields. Preserve version validation, candidate checks, additive-only
APT policy and every application approval gate. Add positive and negative
regressions. Do not perform package, PAM, systemd, boot, service or desktop changes;
do not propose a blanket upgrade or silently select older development packages.
Do not commit, sign or publish without separate approval. Back up affected source
files under ignored work/; do not copy the private package inventory into Git.

## Tasks

- [x] Back up affected source and correct the trailing-diagnostic parser.
- [x] Test supported diagnostic forms and unsafe/unknown trailing text.
- [x] Verify upgrade refusal, full unit suite and whitespace checks.
- [x] Explain the remaining prerequisite blocker and release limitations.

## Result

The parser accepts the observed diagnostic suffix forms, preserves strict version
and candidate checks, and rejects unknown trailing text and nested parentheses.
All 962 unit tests, clean-source and whitespace checks passed. Installed-package
changes remain blocked. The actual plugin prerequisites cannot be applied under
the additive-only policy on the reported baseline; declining the optional plugin
package stage remains the immediate application-installation workaround.

This source-only fix is not part of an existing signed release. No package,
service or desktop change, commit, signing or publication was performed. A parser
fix does not establish fresh-VM dependency or native titlebar acceptance.
