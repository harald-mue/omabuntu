# Update menu: original placement and Omabuntu integration proposal

## Evidence and shortcut terminology

Compared Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068` with Omabuntu's command menu and
release tools. Eight original blobs (menu, update, system-package update,
channel selection, shell restart, terminal presentation, update confirmation
and menu launcher) match the pinned Git tree. Private verification evidence is
under ignored `work/update-menu-098/`. No upstream helper was executed/imported.

The user named Ctrl+Space. The repository's documented and configured command
menu shortcut is **Super+Space**, targeting `omabuntu:menu`; see
`config/hypr/session-template.lua.in` and `docs/command-menu.md`. This assessment
concerns that menu, not a new keyboard shortcut. Confirm Ctrl versus Super
before any separately approved binding change; no live binding was inspected
or changed for this analysis.

## Exact upstream placement and hierarchy

Source: `default/omarchy/omarchy-menu.jsonc` at the pinned commit. The root row
is at line 31; Update children occupy lines 436–464. Root order is Apps, Learn,
Appearance, Trigger, Setup, Install, Remove, **Update**, About, System.
Update is a sibling of System, not a System submenu.

```text
Update                         (aliases: restart, refresh)
├── Omarchy
├── Channel
│   ├── Stable
│   ├── RC
│   ├── Edge
│   └── Dev
├── Kernel                     (conditional; dynamic kernels provider)
├── Config                     (title: Reset to default)
│   ├── Hyprland
│   ├── Hyprsunset
│   ├── Plymouth
│   ├── Tmux
│   └── Shell
├── Extra Themes               (conditional)
├── Process                    (title: Restart)
│   ├── Hyprsunset
│   └── Shell
├── Hardware                   (title: Restart)
│   ├── Audio
│   ├── Wi-Fi
│   ├── Bluetooth
│   └── Trackpad
├── Firmware
├── Password
│   ├── Drive Encryption
│   └── User
├── Timezone
└── Time
```

The main action is `update.omarchy`, launching
`omarchy-launch-floating-terminal-with-presentation omarchy-update`. The
presentation wrapper opens an independent terminal with logo and completion/
failure output. This is not an inline menu action that immediately upgrades.

However, `omarchy-update` itself orchestrates sudo authorization, package-cache
pruning, snapshots, an idle inhibitor, development/keyring updates, pacman
system upgrades, migrations, orphan cleanup, service restarts, hooks, mise/AUR
updates, boot verification and a possible reboot offer. Channel selection
changes package repositories/package families and invokes the updater. Shell
restart has lock/relock and notification-service behavior. These are unsuitable
for direct execution or a search-and-replace pacman-to-apt port in Omabuntu.

## Existing Omabuntu capabilities and missing pieces

| Area | Existing evidence | Integration consequence |
| --- | --- | --- |
| Menu | `config/shell/omabuntu-menu.jsonc` deliberately omits Update; `tools/menu_model.py` accepts closed actions only. | Add a reviewed root/action, not an arbitrary shell-command escape. Place Update before System while Install/Remove/About remain excluded. |
| Public release path | `make update` invokes `install.sh --download-release`; `tools/download_release.py` obtains GitHub's latest stable published release, verifies publisher-signed checksums, metadata, archive and extraction constraints. | Reuse the verification logic, but factor checking/downloading from installer execution. The current downloader always downloads/extracts and then launches the installer; it is not a check-only API. |
| Installer scope | `tools/published_install.py` reviews missing PPA/package/font prerequisites and offers artwork, session/plugin and repair steps. | Do not blindly attach the general installer to a menu item labeled application update. Build an application-only path; report missing prerequisites/target mismatches without installing or reconfiguring them. |
| Deployment | `tools/setup.py::local_release` and `tools/release_update.py` support exact-plan approval, locking, prepared bundles, journals, compatible state-schema checks, bounded readiness and previous-selection recovery on startup failure. | Reuse the transaction, not a second selector-switch implementation. Preserve all refusal rules and do not silently enable legacy/native migration flags. |
| Restart side effects | `release_update.start_bar` normally calls `Installation.start()`, which restores the recorded wallpaper by default. Prior approved narrow deployments explicitly disabled that restoration. | Provide a reviewed application-only, wallpaper-preserving option; do not assume the ordinary update path has no desktop side effects. |
| Installed distribution | `tools/package_user.py` ships menu/session helpers and the manager, but not the complete downloader/setup/update dependency closure or trusted publisher key as a menu updater. | Package and test the required closure and public trust anchor explicitly. A menu action must work without this checkout, Make or a temporary installer source path. |
| Local adaptations | Installed private derivatives can include newer fixes than the latest public release; version strings are not necessarily semantic public versions. Current v0.2.0 predates the newly committed Appearance controls and rendering fixes. | Detect public versus local provenance. Never call a lexicographically different name an upgrade or silently replace local fixes with an older published bundle. Git commits/pushes are not published releases. |

## Recommended first integration

Use the original root label/icon and hierarchy location, with **Omabuntu** in
place of Omarchy. Keep the original terminal-based interaction instead of
adding a replacement update panel.

```text
Update
└── Omabuntu                   → independent interactive update terminal
```

Inside that terminal:

1. Show installed application identity, public/local provenance and update scope:
   Omabuntu only, not Ubuntu packages, Hyprland, plugins, personal configuration
   or managed corporate components.
2. On explicit activation, check the public release with network size/time
   bounds and verify its signed metadata using the installed trust anchor before
   making a trusted availability decision. Report offline/rate-limit/signature
   failures clearly; unsigned API descriptions are discovery hints only. Opening the
   root menu and evaluating its guards must not trigger network/download work.
3. Distinguish already-current, verified newer compatible release, public
   downgrade, locally adapted/unknown ordering, and incompatible prerequisites.
   For local versions, default to reporting that automatic replacement is
   blocked. Offer a separately explicit reviewed replacement path only if
   desired; do not automatically fast-forward the checkout or rebuild sources.
4. Download/stage only the explicitly selected candidate. Verify it using the
   already trusted publisher public key, signed checksums, target/contract and
   archive restrictions. Never trust a replacement key supplied by that archive
   or fetch a moving bootstrap script/key as an implicit menu trust update.
5. Display the exact update plan and ask once about application deployment,
   including the recorded shell-only restart. Cancel means no deployment or
   desktop change. Network/staging writes stay in private cache/reports.
6. Execute through the existing transactional updater with wallpaper restore
   disabled, preferences preserved, session-lifetime grant retained, and
   automatic previous-selection/startup restoration on failure. No new timer,
   autostart, supervisor, package install or session transition.
7. Keep completion/failure and a private report location visible in the terminal.
   The runner must be detached from the shell it restarts and must use a resolved
   immutable helper path retained during the transaction; do not make the update
   depend on a QML Process surviving that restart. Validate terminal selection
   and pass fixed argv, never shell-interpolate user values or upstream scripts.

Suggested action token: `omabuntu-update:review`, mapped to a dedicated Python
launcher and a reviewed packaged update runner. This is a proposal, not an
existing registered action. Add no unattended `-y`/automatic approval route.
Check/verified are not installed/running, and startup is not visual acceptance.

### Useful later additions, explicitly adapted

- **Update > Status:** installed/public identity and last result, with a separate
  explicit refresh. Prefer this to a background polling service or network guard.
- **Update > Rollback:** review the previous retained application release and
  request confirmation for the shell restart. This is an Omabuntu addition, not
  an original upstream row. It is application rollback, not a reset of all
  preferences, packages or personal Hyprland configuration.
- **Update > Process > Shell:** preserve this upstream placement if separately
  wanted. Add an independent, confirmation-gated, identity-checked runner with
  locking, locked-session refusal and startup/failure recovery. Do not import
  the original restart/relock/service helper or use broad process kills.

Do not ship empty Channel/Config/Hardware branches or misleading `restart` and
`refresh` aliases for an application-update-only first version. Reintroduce
those aliases only with reviewed matching semantics.

## Explicit exclusions

No upstream Channel (no Omabuntu RC/Edge/Dev distribution contract), Kernel,
Config reset, Extra Themes updater, hardware/service restarts, Firmware,
Password/encryption, Timezone or Time controls. Existing artwork/theme licensing
and provenance gates are not bypassed by updating the application.

Ubuntu package updates are a different operation governed by Ubuntu/corporate
management. Do not hide `apt upgrade`, new sources, firmware or reboot under
Omabuntu's application entry. An optional link to the existing approved Ubuntu
update UI would require its own explicit scope; it is not part of this proposal.

## Implementation and acceptance gates

Before implementation, agree on the first-batch scope and shortcut terminology.
Then plan the packaged updater/check-only API, trusted-key closure, provenance/
version comparison, runner/TTY lifetime and failure recovery. Tests should cover
menu/action rejection, no network on menu open, offline and signature failures,
missing prerequisites without privilege prompts, local/public downgrade safety,
exact-plan drift, concurrent updates, cancellation, shell-parent exit, startup
failure restoration, preference/wallpaper preservation and rollback.

Native terminal interaction, self-restart recovery, updated UI behavior, GNOME
and fresh-machine acceptance remain separate from source review/unit fixtures.
This assessment changed no menu, updater implementation, binding, installed
release or live desktop, and did not contact the release service.
