# Architecture

## Separate behavior from operating-system management

1. **Window manager:** version-matched Hyprland configuration, bindings,
   workspace behavior, input, and laptop display policy.
2. **Desktop shell:** original Omarchy Quickshell components where compatible,
   with reviewed loading, IPC, notifications, and agent ownership.
3. **Ubuntu adapters:** explicit desktop helpers using existing Ubuntu services,
   approved packages, and reviewed permissions.
4. **Deployment tooling:** inspect, plan, back up, apply, verify, and roll back.

Arch distribution management is outside this design.

## Repository layout

- `config/`: a standalone staged Lua prototype; no active installation or private inventory.
- `bin/`: reviewed desktop adapters, not the entire Omarchy command set.
- `packages/`: capability-to-package mappings and approved build recipes.
- `upstream/`: provenance records and eventually licensed selected source files.
- `tools/`: Python diagnostics, simulation-only package planning, isolated native
  parser checks, and an explicitly opted-in source builder with Bubblewrap.
- `tests/`: synthetic tests without desktop changes.
- `work/`: ignored private reports and development artifacts.

Unimplemented adapters and deployment commands are not represented by empty
placeholder directories. The staged profile is documented with its explicit limits.

## Deployment contract (local user tooling implemented; host apply pending)

Inspection and planning never activate components. Applying a reviewed plan
requires explicit opt-in, verified backups, and a change manifest. User and
system changes remain separate. Rollback restores the actual target pre-state,
including removal of newly introduced files and activations.

Use a dedicated versioned runtime location rather than executing files from
the private reference snapshot. Do not make the repository location a required
permanent desktop runtime path.

`tools/package_user.py` now creates standalone, sealed local release bundles;
`tools/user_install.py` supplies read-only planning, explicit user installation,
Start/Stop/Status, verified version selection, update, rollback and interrupted
transaction recovery. Default host paths and exact limitations are documented
in [user installation](user-installation.md). Workspace installation fixtures do
not constitute host apply or daily-use acceptance. Autostart/crash supervision,
lock authentication/recovery and session-transition acceptance remain separate
approval gates. The production shell catalog and original full-shell services
are not expanded by this deployment tooling.
