# Keep the bar surface alpha-capable across background changes

## Goal and evidence

Fix the reported lack of visible effect for all three Bar Background choices.
The user's screenshot shows the original Opaque/Glassy/Clear submenu with a
selected Glassy entry. The deployed preferences also report Glassy, while
TrialPanel has no explicit alpha-capable surface format.

The pinned Quickshell source at commit
`2b4501a282689792b62e94f3fb30d8f512324fe6`, windowinterface.hpp and
proxywindow.cpp, documents and implements the relevant constraint: initial
opaque color selects a surface without an alpha buffer unless
`surfaceFormat.opaque` is explicitly false. The format cannot change after
window creation. The adapter starts with Opaque before asynchronously reading
persisted preferences. Omarchy menu fidelity remains pinned to v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`.

## Shape and safety

Back up affected repository files, explicitly request an alpha-capable bar
surface before creation, retain the existing background color bindings, refresh
the authored source hash, add a regression contract and document the acceptance
boundary. This changes the format capability, not the chosen background.
Do not change preference files, compositor/blur rules, GNOME, keyboard bindings,
packages or services. The initial problem report did not authorize deployment;
the user subsequently explicitly approved the new local version and bar-only
restart. Back up current selectors, running identity and relevant preferences,
clone the verified installed release and replace only TrialPanel and provenance.
Use the existing reviewed application-update transaction with wallpaper restore
disabled and automatic previous-selection recovery on failure. Do not reload
Hyprland, change preferences, commit or publish.
Preserve the original components; no replacement panel or upstream script import.

## Exclusions and verification limits

These options affect the horizontal menu bar, not the command-menu card or
application windows. Glassy uses the existing translucent color; compositor
blur remains user-owned. Static tests and contained fixture success are not
proof of native alpha blending or visual acceptance. A newly created native
bar surface and user feedback are required to accept the fix.

## Tasks

- [x] Back up sources and add the explicit pre-creation alpha format.
- [x] Add regression coverage, source hash and documentation.
- [x] Run unit tests and relevant contained checks.
- [x] Deploy the narrowly adapted release after the explicit restart approval.
- [x] Verify process/manifest integrity and unchanged preferences.
- [x] Obtain user confirmation of native visible differences.

## Repository verification

1106 unit tests passed, along with the contained command-menu and clock
fixtures. The new regression contract requires the explicit surface format
while retaining all three background bindings. Those repository checks did not
change user preferences or the running shell.

## Approved deployment result

After explicit approval, prepared a verified private derivative changing only
TrialPanel and provenance, retaining every other bundle byte. The reviewed
application-only update completed with a bar-only restart, no user-state
migration or native transition, and wallpaper restoration disabled. The previous
release remains selected as the rollback target. Startup and manifest checks
passed; all three bar outputs and the independent menu shortcut registration
are present. Relevant preference presence, bytes and modes exactly match the
pre-deployment backup. No shell error markers were detected.

Private prestate, update plan/journal references and verification evidence remain
under ignored `work/bar-background-096/deployment/`. No compositor reload,
keybinding/configuration edit, package/service change, commit or publication was
performed. After deployment, the user explicitly confirmed that switching the
three background options now works. This accepts the reported Bar Background
issue in the current session, not unrelated Appearance interactions, GNOME
coexistence, fresh-machine behavior or security acceptance.
