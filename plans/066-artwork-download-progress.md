# Artwork download progress

## Goal and evidence

The v0.1.5 published installer's artwork download (consented after one [Y/n])
runs ~120 sequential pinned HTTPS fetches (~65 MB) with no output until the
final JSON report, so the user cannot tell whether it is working. The download
itself is correct; only feedback is missing.

Evidence: `download_backgrounds.materialize` (per-item fetch/reuse loop used
by `user_artwork.apply`), `user_artwork` CLI `--download`, `published_install.offer_artwork`.
Pins unchanged (Omarchy artwork commit 03ff1eff3812933f7088484533784d2f63eaf19a).
No behavior change to verification, atomic writes or prompts.

## Shape

- Optional `progress` callback in `materialize(position, total, item)` invoked
  after each processed file; default `None` keeps every existing caller silent.
- `user_artwork.terminal_progress` prints one flushed line per file
  (`[k/n] target (KiB)`) plus a start line with totals; used by the CLI
  `--download` path and by `published_install.offer_artwork` via an apply
  argument. Plain stdout, works piped, no ANSI.
- Progress lines precede the final JSON report; receipts/tests unaffected.

## Safety and exclusions

No fetch, prompt, package, service or desktop action changes. No
parallelization (deterministic order, unchanged timeouts). No commit/push or
release publication in this task; public availability needs a later signed
release. Progress output is cosmetic, not acceptance.

## Tasks

- [x] Back up affected sources; add the callback and terminal printer.
- [x] Wire CLI and published installer; add regressions for per-file callback.
- [x] Run full tests/clean-source/whitespace; report release limitation.

## Result

`materialize` gained an optional per-file `progress(position, total, item)`
callback (default silent for all existing callers). `user_artwork.terminal_progress`
prints one flushed plain line per file plus a start line with count and size;
the CLI `--download` path and `published_install.offer_artwork` pass it, so the
consented download shows `[k/n] path (KiB)` instead of a silent multi-minute
pause. Verification, atomic writes, prompts and the receipt are unchanged.
All 1011 tests, clean-source and whitespace checks passed. Progress output is
cosmetic, not acceptance. This is uncommitted source; the running v0.1.5
release does not include it until a later signed release is published.