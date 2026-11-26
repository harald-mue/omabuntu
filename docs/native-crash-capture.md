# Explicit native crash capture

`tools/native_crash_capture.py` is an opt-in development-side diagnostic launcher,
not an installed manager modification, autostart setting or crash restart policy.
It requires a verified, currently owned running installation and the unambiguous
current Hyprland session. Obtain explicit owner approval before activation.

```sh
# Plan only; no process is stopped or started.
python3 tools/native_crash_capture.py start

# After explicit approval: back up state, stop only the owned shell and start
# the unchanged release with GDB as its parent. Do not restore the wallpaper.
python3 tools/native_crash_capture.py start --apply
```

The launcher adapts only the exact Quickshell spawn during the installed manager's
normal startup. All other probes are delegated unchanged. GDB hands off the real
inferior PID, argv and start ticks, with the GDB parent/tracer relationship checked.
The manager's normal identity record and `omabuntu status|stop` continue to refer
to Quickshell, not GDB. On startup failure, the launcher attempts an ordinary
owned shell restart with background restoration disabled and records recovery.
It does not edit installed files, release seals or the launcher.

## Lifetime and recovery

The diagnostic shell and supervisor have no session expiry timer. Deadlines
apply only to debugger startup and fatal-signal capture. No debugger is attached
to an existing process; no Ptrace/core/security policy or service is changed.
GDB follows the parent and detaches helper children. Normal shell termination
passes through GDB, and the supervisor reaps the debugger.

On SIGSEGV, SIGABRT, SIGBUS, SIGILL, SIGFPE or SIGSYS, GDB attempts a trace of at
most 64 threads and 64 frames per thread, writing at most 1,000,000 trace bytes.
A supervisor limits fatal capture to 15 seconds and cleans up only identity-
checked inferior/debugger children. No core dump is requested; the diagnostic
supervisor keeps its inherited core-file soft limit at zero without increasing
the hard limit. This alone is not a universal guarantee against piped system
crash collectors. A normal capture stops the fatal signal before delivery and
terminates the debuggee without generating a core.

**After a fatal capture, the shell is stopped, not automatically restarted.**
Inspect the private receipts and obtain an explicit recovery decision. An
ordinary `omabuntu start` returns to normal undebugged operation. No future login
inherits this mode, and package/deployment operations retain their existing
approval and ownership checks.

## Data boundary

Arguments, local-variable values, register/memory dumps, source text, pretty-
printers, frame filters, auto-loaded debugger scripts and remote symbol fetching
are excluded. ASLR remains enabled. The debugger still reads process memory to
unwind the stack; traces can reveal function names, addresses, paths, file/line
metadata and argument names. Ordinary application output remains in the normal
private run log. Treat every report as private, not as guaranteed secret-free.
Without Qt debug symbols, stack resolution can be partial or fail, especially
after memory corruption. Debugging perturbs timing and does not ensure a crash
will reproduce.

## Evidence and limits

Backups and activation results go under ignored `work/crash-capture-169/`.
Per-run receipts, generated fixed GDB commands and a possible `backtrace.txt`
are under the private installed `runs/<run>/native-capture/` directory. Running
this mode requires the development-side supervisor code to remain available;
it is not a portable installed feature or published support promise.

Contained real-GDB probes cover normal exit, fatal capture with omitted secret
argument/local values, SIGTERM, a missing executable and the ordinary manager's
exact inferior identity/status/stop behavior. Unit tests cover adapter cleanup,
PID reuse refusal, parent/tracer proof and default plan-only gating. These are
not proof of native desktop stability, complete privacy or fault attribution.
