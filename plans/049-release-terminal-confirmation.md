# Fix release terminal confirmation

## Goal and evidence

The first real release invocation stops with "File or stream is not seekable"
after reporting a clean working tree, before tests/build/tag/push. The confirmation
helper opens /dev/tty with r+, which requests a seekable buffered read/write
stream. Terminals are not seekable. Existing publication tests mock the helper
and therefore did not exercise its real terminal I/O.

## Shape and safety

Open separate read-only and write-only terminal streams, flush the prompt, and
retain exact yes-only approval and cancellation behavior. Test using a local
pseudo-terminal without involving the user's controlling terminal. Back up the
affected source/test files privately before editing. No desktop behavior or
upstream pin comparison is relevant. Do not run release publication, access the
private signing key, commit, push, install packages or bypass approval gates.

## Tasks

- [x] Fix terminal streams and add real pseudo-terminal regression tests.
- [x] Run the full unit suite and whitespace checks.

## Verification

804 tests passed, including real nonseekable pseudo-terminal approval and refusal
cases. Whitespace checks passed. No release workspace had been created by the
failed run, so that run did not reach build/tag/push/publication. No publication
or signing attempt was executed during this fix.
