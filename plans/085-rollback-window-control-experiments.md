# Roll back the window-control experiments

## Goal and evidence

The user explicitly requested rollback of the unsuccessful window-control work.
Restore the operational state before plans 080–084 without undoing the accepted
Omarchy v4.5.0 stable update (commit 6bdba98). Compare the owned live titlebar
file/receipt against the completed plan-081 transaction and its exact backups,
and the tracked source changes against HEAD. No browser module was installed or
persisted; the real Chrome test failed module loading.

## Shape and safety

Back up the current source and live file/receipt state before rollback. Require
the current ownership hash and transaction after-state to match, then restore
the original titlebar file/receipt bytes and modes. Update only the existing
live named rule's class matcher back to `.*`; do not reload plugins or re-add
buttons. On failure restore the backed-up experimental file/receipt/matcher.

Restore only the known experimental source/template/test edits. Archive newly
authored module, builder and experiment-specific tests privately under ignored
work/ rather than deleting them. Preserve analysis/plans as explicitly rolled-
back historical evidence. Do not revert the accepted stable application release,
change GNOME/GTK/browser profiles, restart browsers/shell/compositor, alter
services/autostart or commit. Existing duplicate CSD/hyprbars appearance returns;
the desired session-specific app-button suppression is not claimed implemented.

## Tasks

- [x] Verify exact live ownership/prestate and back up all affected paths.
- [x] Restore original live titlebar/receipt and named class matcher.
- [x] Restore functional source changes and archive unsupported research code/tests.
- [x] Verify plugin/process continuity, GNOME layout and clean config errors.
- [x] Run full tests and document the restored state and remaining limitations.

## Outcome

Original titlebar and activation-receipt bytes/modes were restored from the
verified completed experiment backup after checking current ownership and exact
after-state. Current experimental files and metadata were backed up first in
the manager's private titlebar-csd-rollbacks directory. The existing named live
class matcher was restored to `.*`, without appending effects/buttons or
reloading the plugin. Receipt validation, unchanged loaded plugin handle,
unchanged owned shell process and clean config errors were verified.

The source snippets and dock-parity test again match commit 6bdba98 exactly.
New module research source, builder and experiment-specific tests were moved
into ignored work/rollback-window-controls-085/archived-code. Only explicitly
historical/rollback documentation remains in the working tree. No module was
installed or persisted, so no machine-wide/module-startup removal was needed.
The accepted stable release remains selected and running. GNOME button layout
remains appmenu:minimize,maximize,close. No browser, shell or compositor restart,
service/autostart change, commit or publication occurred during this rollback.

All 1079 baseline tests and the clean-source export check pass. The original
appearance returns: app controls remain in tiling, and floating-workspace
browsers can again have both app controls and hyprbars. Desired session-local
button suppression and browser-native minimize equivalence are not implemented.
No visual acceptance or fresh GNOME-login claim is made. Private rollback
prestate/results and source archives are under ignored
work/rollback-window-controls-085/.
