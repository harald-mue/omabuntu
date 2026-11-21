# Complete normal application launch integration for partial window controls

## Superseded and archived before deployment

The user clarified that the original user-wide button-layout switch, including
GNOME, is wanted rather than a new application-launch mechanism. Plan 131
supersedes this experiment. All launch-adapter source changes were restored to
their exact pre-plan-130 state; new experimental files were archived privately
under work/archived-window-controls-130/. No experimental launch adapter was
installed. The full-suite contract correctly rejected adding a Process to the
previously closed authored-source set; that unfinished experiment was not accepted.
The unchecked tasks below are historical, not current work or acceptance.

## Goal and evidence

Address the reported no-op after launching GNOME Files from the application grid
and Super+Shift+F. The agreed scope is partial toolkit support, but plan 128
left ordinary launch paths unintegrated. Complete that missing repository wiring
without claiming GTK4/libadwaita support or altering the running desktop.
Use plans 127–129, the pinned Quickshell launch APIs and existing fixture/native
checker contracts. Omarchy baseline remains v4.5.0 commit
ac2690cd7be4f47e4a255f5e2e78d904d436b068. Runtime Quickshell pin is
2b4501a282689792b62e94f3fb30d8f512324fe6.

## Gaps and proposed investigation

Application grid and floating dock currently call DesktopEntry.execute directly;
normal compositor keybindings and desktop/D-Bus activation have distinct owners.
Inspect exact supported launch/environment APIs before choosing the adapter.
Preserve desktop entry argument expansion, terminal handling and working directory;
never substitute shell parsing of desktop Exec strings. GNOME Files 50.2.2 has a
GTK4/libadwaita headerbar, not covered by the two existing toolkit variables.
Determine feasible normal-launch wiring and explicit unsupported paths first.

## Safety and exclusions

Repository code/tests and bounded source review only. Back up changed paths before
edits. No live application restart, private binding/profile rewrite, shared
GNOME/GTK setting, compositor environment update/reload, service environment
export, package action, deployment or commit. Further live integration requires
review and approval. No injection or unsupported universal-support claim. Keep
raw public sources and machine evidence under ignored work/.

## Tasks

- [ ] Inspect pinned launch APIs and distinguish grid/dock/keybinding activation.
- [ ] Select and implement the safe normal-launch path for supported applications.
- [ ] Add regression tests for real entry semantics and policy refresh/failure.
- [ ] Document remaining GNOME Files and activation-path limits, not just saved intent.
- [ ] Run the full unit suite and review source hashes/packaging without deployment.
