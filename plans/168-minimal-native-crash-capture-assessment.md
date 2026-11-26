# Minimal native crash capture assessment

## Goal and evidence

Assess a native backtrace path after the owner reported a second Quickshell
crash without a click. Compare the existing kernel fault records, owned-process
limits, Linux ptrace/core policy, installed debugger and crash collector, and
available symbol metadata. Popup provenance at Omarchy
`ac2690cd7be4f47e4a255f5e2e78d904d436b068` remains context, not a proven cause.

## Gaps and proposed shape

The current logs have no native backtrace; the faults occurred in different Qt
libraries. Determine whether an existing collector already provides useful
metadata and whether a supervised future start could capture stack addresses
without a core or local-variable dump. Separate a safe proposal from activation.

## Safety and exclusions

Read-only assessment only, apart from private ignored evidence. Do not attach a
debugger, pause/restart the shell, enable core dumps, read existing memory dumps,
change ptrace/core/security policy, install packages, enable remote symbol
fetching, activate services or publish reports. Do not print credentials or
corporate inventories. Backtraces can still disclose process metadata; no claim
of complete absence of sensitive data. Any capture activation is a separate
explicit approval gate.

## Tasks

- [x] Inspect existing collector, process limits and debugger policy read-only.
- [x] Inspect symbol availability and minimal debugger capture options.
- [x] Record safe next-step proposal and limits; run repository unit tests.

## Assessment

GDB is installed. coredumpctl is unavailable; Apport is installed but disabled,
and no matching Quickshell report was found in its ordinary crash directory.
The owned shell is untraced with a zero soft core-file limit. A zero limit alone
is not a universal guarantee that piped core handlers cannot receive memory.
The kernel core pattern points at Apport; leave that policy unchanged.

Yama scope 1 normally prevents a same-user debugger sibling from attaching to
this existing process unless an applicable exception exists. Do not probe by
attaching, elevate privileges or relax Yama. Instead, a future separately
approved start can make GDB the process's parent. That requires explicit
integration with the manager's exact PID/start-ticks/argv identity and stop/
recovery handling; an ad-hoc wrapper is not a safe drop-in replacement.

The installed Quickshell retains a symbol table but no embedded DWARF. The Qt
Core/QML/Quick libraries have no embedded DWARF and their standard build-id debug
files are absent. Dynamic symbols/addresses may still give useful partial
frames; no file/line or full symbolic backtrace is promised. No remote symbol
fetching or debug package installation was enabled.

Proposed diagnostic: explicitly approved session-lifetime debugger-parent
launch, ASLR preserved (`set disable-randomization off`), startup shell disabled,
auto-loading, frame filters, pretty-printers and debuginfod disabled. On a fatal
signal capture bounded stack locations only, with `-frame-arguments none`,
`-entry-values no`, `-no-filters`, `-frame-info location-and-address` and no
`-full`, locals, memory/register dump or generate-core-file command. Suppress
normal source-line/stop argument output too; merely avoiding `bt full` is not
sufficient. Decide and test termination/reaping and shell recovery semantics
before activation; do not leave a signal-stopped shell indefinitely.

A backtrace still requires reading the live process stack, can disclose paths
and function metadata, may be incomplete after memory corruption, and perturbs
timing. It is lower-data capture, not zero-sensitive-data or security acceptance.
No debugger attachment, additional inferior launch, restart, core enablement,
policy change or service activation was performed. Private assessment is under
`work/crash-capture-168/`. All 1,640 repository unit tests pass; their private
output is retained alongside the assessment.
