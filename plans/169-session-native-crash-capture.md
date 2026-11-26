# Session native crash capture

## Goal and evidence

Implement and activate the owner-approved minimal GDB capture after Plan 168.
Use the unchanged installed release, exact owned-process identity and existing
manager startup/stop checks. Two kernel-confirmed faults (including one without
a click) do not attribute the fault to a popup. Original shell provenance is
Omarchy `ac2690cd7be4f47e4a255f5e2e78d904d436b068`.

## Gap and proposed shape

Add a development-side opt-in diagnostic launcher, not an installed manager or
runtime modification. A narrow temporary Popen adapter delegates all ordinary
manager probes unchanged and substitutes only the exact expected Quickshell
spawn with a GDB parent. Publish the inferior's real PID/argv/start ticks to the
unchanged manager, so ordinary status/stop continue to identify Quickshell, not
the debugger. Keep supervision/capture receipts private and separately identify
the debugger. No autostart or crash relaunch.

Test with synthetic normal exit, fatal signal, termination and capture privacy
controls before activation. Capture a bounded number of raw frame locations,
without arguments, locals, source text, core dumps, auto-load or symbol downloads.
Keep ASLR and existing policy unchanged. A separate supervisor bounds capture
completion only, never the normal session lifetime. After a fatal signal,
terminate/reap only the owned debuggee and debugger; retain evidence and require
an explicit recovery decision rather than leaving a stopped desktop indefinitely.

## Safety and exclusions

Back up affected source/deployment state and previous process metadata before
changes. Owner approved one live shell stop/start under GDB; do not attach to
other processes, change policies, install packages, activate services, alter
settings/wallpaper, modify release seals or enable core dumps. On startup failure,
restore normal owned shell startup without background restoration, recording the
failure. No synthetic crash in the live desktop. No commit or publication.
Stack metadata can still contain private paths; keep reports private.

## Tasks

- [x] Implement narrow diagnostic adapter and supervisor with identity checks.
- [x] Add synthetic capture/privacy/normal-exit/stop/failure regressions.
- [x] Run all unit tests and contained real-GDB synthetic probes.
- [x] Back up live state and restart only the owned shell with diagnostic capture.
- [x] Verify startup, actual inferior identity, tracer and ordinary status/stop
      contract; document recovery and limitations.

## Closeout

Added `tools/native_crash_capture.py`, 13 unit regressions and
`docs/native-crash-capture.md`; these are new paths, not installed release edits.
All 1,653 unit tests pass. Five contained real-GDB probes pass: normal exit,
fatal SIGSEGV with a secret argument/local sentinel absent from capture/logs,
SIGTERM, missing executable and ordinary manager inferior identity/status/stop.
The synthetic executable had debug information, so the omission test was not
merely a consequence of unavailable symbols. No synthetic live desktop fault
was induced.

The owner-approved restart succeeded using the unchanged installed release.
Startup markers and normal manager status pass; the real inferior argv/start
identity and GDB parent/tracer relationship match. The capture has not fired.
Private prestate/run-log/control-lock backups, exact launch results and identity
verification are under `work/crash-capture-169/`; contained evidence is beneath
its probes directory. The active run has a private native-capture receipt
subdirectory beside its ordinary output log. No installed manager, shell,
launcher, settings, background, autostart, service or policy was modified.

This mode has no session expiry and no automatic crash restart. On a fatal stop,
it attempts a bounded stack-location capture, then terminates/reaps only its
owned children. A 15-second watchdog applies solely after fatal capture starts.
An ordinary owned stop remains available. After a crash, preserve the private
trace and obtain a recovery decision; normal start returns to undebugged mode.
No claim of Qt fault attribution, complete symbol resolution, desktop stability
or zero-sensitive-data capture is made. No commit or publication was performed.
