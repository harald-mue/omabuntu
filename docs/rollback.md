# Rollback contract

The approved selected-shell user runtime is installed and running manually;
active Hyprland configuration, system services and login defaults are unchanged.
However, the user installed the approved 96 system dependency packages.
Package versions and APT marks before/after are recorded privately under
work/dependency-install/. This evidence is not a complete system backup.

Any package rollback requires a separately reviewed transaction and restoration
of applicable prior APT marks. Do not automatically remove the full development
stack or use broad autoremove. Workspace source/build/staging artifacts are
separate from system packages and can be removed only when explicitly requested.

Before future application, record for every affected object:

- path or service/key/package identifier;
- whether it existed and its previous content/hash/link target/value;
- permissions and relevant directory metadata;
- verified target-backup location;
- exact operation and newly created objects;
- reversal steps and any separately approved reload/session operation.

Restore target backups, never the private Omarchy source snapshot.
Remove only objects demonstrably created by the specific application.
Do not broadly delete user configuration or use package autoremove as rollback.
Preserve service activation state, environment changes, and individual GSettings
pre-values; copying files alone is not a complete rollback.

A backup must verify source/destination integrity and report errors explicitly.
Local user apply/rollback/recovery commands are now implemented in
`tools/user_install.py`, tested within private workspace fixtures and now applied
with approval to the named user data/state/bin paths. The first-install
transaction records the original absent launcher/selectors and their backups. See [user installation](user-installation.md). Updating
selects a new verified version without overwriting the previous one. Rollback
switches to the previous verified version, or restores first-install launcher
and selector pre-state. Caught application failures restore backups; prepared
journals from interrupted deployment block activation until explicit recovery.
Release directories and journals are intentionally retained, not recursively
removed. Unknown external launcher changes or corrupt backups prevent automatic
restoration. This is not a package rollback, filesystem/power-loss guarantee,
service-state restore or claim of daily-use/security acceptance. No autostart
or locker service is installed by these commands.
