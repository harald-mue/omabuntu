# Verify the original Omarchy window-control implementation

## Goal and evidence

Answer how Omarchy itself handles client-side window controls and floating
workspace titlebars, rather than proposing another unverified workaround.
Use Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`, its complete recorded tree and
blob-verified relevant installer/default/helper/migration files. Inspect the
separate public package-source repository where titlebar or settings packaging
matters; record its exact revision and distinguish current packaging from a
stable-time package pin if historical identity is unavailable.

## Current gap and proposed shape

Prior discussion did not establish the actual upstream mechanism for suppressing
app buttons. The stable tree references omarchy-hyprland-titlebars rather than
only stock hyprbars. Compare its declared package/source behavior with Omabuntu's
reviewed stock-plugin adaptation and the GNOME-preservation requirement. Treat
absence of a setting in selected files as bounded evidence, not universal proof.
Document verified mechanisms and remaining runtime/package-version uncertainty.

## Safety and exclusions

Read-only source research. Save raw public files, tree inventories and response
metadata privately under ignored work/. No upstream script execution, import into
vendor, package install, desktop setting/profile change, service/plugin reload,
application restart, reference-package mutation or commit. Do not repeat the
rolled-back GTK-module/browser exceptions.

## Tasks

- [x] Verify stable titlebar and desktop-settings source plus relevant package recipes.
- [x] Compare original behavior with Omabuntu and explain the GNOME isolation boundary.
- [x] Record exact source evidence, limitations and validation without deployment.

## Findings

Stable `default/hypr/workspace-modes.lua`, lines 446–510, loads
`/usr/lib/omarchy-hyprland-titlebars/titlebars.so`, configures a 30-pixel bar
scoped by floating-workspace membership, and adds close, maximize and minimize
commands. Minimize calls `omarchy-hyprland-window-minimize %WINDOW%` rather than
relying on a browser-native Wayland minimize request. `config/chromium-flags.conf`
selects native Wayland. The seeded Chromium preferences contain theme defaults,
not window-control suppression.

Package history no later than the stable core commit (2026-11-05T02:48:30Z)
resolves the titlebar recipe to omacom/omarchy-pkgs commit
`0c7102d724264f6b966402b7199613486d222698`. It specifies
omarchy-hyprland-titlebars 0.3.0-4, source tag v0.3.0, archive SHA-256
`ca3bdd14ea7e092c1777b306df11b862e520cdb97c13459deab721fca0d6ed93`,
and Hyprland 0.57.1. The v0.3.0 API tree identifier is
`b351b14bbed4b04ed55e6380e03784edcee68399`. README, licenses, main.cpp,
barDeco.cpp and globals.hpp were downloaded and checked against recorded tree
blob IDs. This is a BSD-3-Clause hyprbars fork with MIT Omarchy changes, not the
stock hyprbars source pinned in Omabuntu's upstream/hyprpm.json. Its reviewed
registration/rendering/rule code creates and scopes its own decorations; it
does not strip browser-rendered controls or implement a GTK-settings override.
Fork replacement would not by itself prove CSD suppression or browser acceptance.

The bounded source scan covers 116 install/runtime-profile files, 218 migrations,
plus the four additional environment/window defaults in the migration review,
and 752 helper/config/etc/relevant-default files (overlap is intentional).
All downloaded bytes passed recorded Git blob verification. One binary cursor
cannot be UTF-8 decoded and is not a script/settings-review failure. No
button-layout, decoration-layout, GTK_CSD or GTK_MODULES setting was found in
these scanned stable files. The sole hide_window_decorations match is Kitty's
own setting, not a universal browser rule. This is source evidence, not a live
Omarchy browser/PWA test or proof about every external distribution package,
user customization or future version.

The key correction is that upstream floating-workspace titlebars are verified,
but the requested universal disappearance of application controls is not an
established upstream behavior. Omabuntu currently uses stock hyprbars with its
reviewed membership rules and Ubuntu minimize helper. Do not misrepresent a
shared GNOME button-layout write as the original stable mechanism: no such write
was found in the reviewed source. No alternate session-global setting,
XWayland conversion or failed GTK-module retry is proposed or deployed.

Raw source, API metadata, per-file scan results and historical recipe evidence
remain private under work/research/omarchy-window-controls-086/. No changes were
made to application profiles, desktop settings, plugins or the reference package.
Validation results are recorded there separately from source/runtime acceptance.
