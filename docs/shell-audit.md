# Original shell, helper, and packaging audit

## Result

**Do not launch the unmodified original shell on the target.** The successful
isolated module/type probes do not cover its startup code or integrations.
This phase only read source/reference data and public packaging text. No
captured desktop executable, shell script, Lua, QML shell, PKGBUILD, patch command,
transaction hook, or service was executed.

The reference integrity check still passes: 2,286 regular files, 558 symlinks,
and both original-copy manifests. No reference content changed.

## Repeatable static evidence

```sh
python3 tools/audit_shell.py --reference /path/to/private-reference
```

The reference is an optional explicit development input, not a runtime dependency
of the standalone project. Reports are private under ignored work/shell-audit/.
The auditor reads bounded regular text from the captured shell, installed
Omarchy helpers, default menu/configuration, and original Hyprland autostart.
It records source hashes, manifest entry points, lexical helper edges, and
risk-category line numbers, not full source contents.

It does not follow original absolute bin/ symlinks. It reads the separately
captured installed helper files instead. The one relative helper alias,
omarchy-nvim-refresh -> omarchy-nvim-setup, is recorded as a passive edge without
opening the link. Its target must be a captured regular file in the same helper
directory. Other links, alias chains, traversal, invalid manifests, and missing
required inputs stop the audit rather than pretending coverage.

Final evidence: work/shell-audit/20261024T091037.986335Z/report.json:

- 777 regular text files; 538 helper entries including one passive alias.
- 40 first-party plugin manifests, including 10 service manifests.
- 422 potential lexical helper dependencies from shell/menu/autostart seeds.

**422 is not a count of executed calls or a complete call graph.** Comments and
strings contribute conservative candidates. Bare `omarchy` subcommand dispatch,
sourced libraries, dynamically assembled commands, plugin discovery, and external
non-Omarchy commands need manual review. Finding no marker does not approve a
helper. The scanner is an inventory aid, not a shell parser or security sandbox.

## Startup is not controlled by an empty plugin list

Source witnesses, relative to the captured Omarchy share tree:

- shell/shell.qml:1 declares OmarchyLoadPatch; :22-26 instantiate shared registry,
  application library, brightness, and background-intro objects immediately.
- shell/services/PluginRegistry.qml:140-167 makes first-party non-bar plugins
  enabled unless explicitly listed in disabledPlugins. `plugins: []` is not a
  deny list. The selected bar has a separate selection path.
- shell/shell.qml:923-1042 loads enabled service entry points with
  Qt.createComponent/createObject, not only visible bar widgets.
- shell/shell.qml:1315-1410 also mounts enabled keepLoaded panels/overlays without
  waiting for a user to open them.
- shell/services/PluginRegistry.qml:717-795 starts plugin-directory creation,
  discovery and an inotify watcher. User plugins are executable QML, not data.

The ten service IDs are omarchy.background, omarchy.dock, omarchy.lock,
omarchy.notifications, omarchy.polkit, omarchy.battery, omarchy.idle,
omarchy.media, omarchy.nightlight, and omarchy.remote-session.

The built-in fallback and shipped default configuration include 150/300-second
screensaver/lock settings and do not disable those services. Disabling entries
only in a valid user JSON file does not establish a fail-closed fallback for a
missing, invalid, or not-yet-applied configuration. A future host must enforce a
positive load policy **before object creation**, including bar, service, panel,
shared startup objects, reload paths, and fallback paths. No such enforcement
has been implemented or claimed by this audit.

Hiding widgets, relying on an absent helper executable, or blocking PATH alone
is insufficient: NotificationServer, PolkitAgent, PAM, UPower and other native
QML types can operate directly. Scoped plugin APIs are not an OS-level sandbox
for untrusted QML. Third-party discovery must not be part of an initial trial.

## Manually traced boundaries

| Path/function | Observed source behavior | Ubuntu decision before any trial |
|---|---|---|
| Original launcher | Journals Quickshell, controls watcher/popup flags, supervises failures and relaunches | Design explicit one-session lifecycle; do not copy crash supervision into an unapproved trial |
| Shell IPC/restart | Guesses a recent display/socket; restart can kill matching instances across displays, re-lock and restart invitation units | Replace with explicit session targeting; no restart helper exposure yet; quiet IPC success is not a health check |
| Shared brightness/background startup | BrightnessKeys runs omarchy-hw-display immediately; BackgroundIntro probes state/Owe and uses compositor-specific callbacks | Gate shared objects, not only plugin manifests; no automatic hardware/background integration |
| Plugin discovery | Creates/watches a user plugin directory; dynamic component loading | Fixed reviewed roots and allowlist; no arbitrary user plugins during a trial |
| Menu | Executes action strings and batches when/checked guards through bash; configurable providers generate further commands | Replace command boundary with reviewed typed actions; hiding install/update rows alone is insufficient |
| Theme change | Runs multiple retint helpers and theme-set hooks, not just a color update | Initially read a reviewed palette only; do not expose the original theme changer |
| Browser theme policy | theme-set -> theme-set-browser -> theme-set-browser-policy can invoke sudo/pkexec and write managed browser policy | Excluded: preserve corporate browser policy and all existing trust roots |
| Power/battery | Startup reads profile; UPower power-source changes can call omarchy-powerprofiles-set, which uses powerprofilesctl set | Keep profile changes disabled until existing target ownership/policy is reviewed |
| Night light | Startup probes Hyprsunset; user actions can start it through UWSM and change temperature | Separate opt-in controller ownership; no startup or duplicate daemon |
| Lock/idle | First-party services, native session lock, password/fingerprint PAM paths and timer/helper actions | No load or testing before Ubuntu authentication/recovery approval; never install Arch PAM or migrate stay-awake state |
| Notifications/Polkit | Native bus/server/agent objects instantiated as services | Keep existing target owners; no second agent/server in a trial |
| Original Hyprland autostart | Launches shell, first-run provisioning, power-profile initialization, monitor watch and post-boot hooks | Do not port the autostart wholesale; none of these routes are approved by this audit |

The browser-policy chain is concrete, not just a token match:
installed helper omarchy-theme-set lists omarchy-theme-set-browser in its retint
commands (:543-552); that helper invokes omarchy-theme-set-browser-policy (:56).
The policy writer's require_root (:65-75) selects sudo or pkexec and writes into
existing managed policy directories for Chromium/Chrome/Edge/Brave. Even cosmetic
theme actions therefore cross the corporate-management boundary.

Shared Commons objects also require review: Style performs compositor/font
queries; InputDevices starts an inotify process; InputMethodState starts a
Python indicator. A plugin allowlist by itself does not remove these transitive
startup dependencies. External CLI availability and behavior remain target gates,
not permission to add another package transaction.

## Exact Quickshell package recipe identified

[Packaging provenance](../upstream/quickshell-packaging.json) records the matching
public package-repository revision:

- Repository: https://github.com/omacom/omarchy-pkgs
- Commit: 2be7cd983944f50612338124ec6725da95dceb2e
- PKGBUILD SHA-256:
  e871efd5b0705d16226b4e8cd0b9ed99269129a62cc4590583df5581c25ab6aa

The hash matches pkgbuild_sha256sum in the captured Quickshell .BUILDINFO, and
the recipe has the recorded package version/release (-1). The current default
branch was newer (-3) and did not match; it was not substituted for the reference.
The recipe pins the same upstream Quickshell commit used by our build.

The pinned patch and Arch transaction hook were downloaded as text. Both hashes
match the matching recipe's SHA-256 entries. Private research/provenance files
are under work/research/shell-audit/. No PKGBUILD was sourced or run; no patch was
applied; no hook was installed. This identifies the recorded recipe and patch,
not signed authenticity or byte-identical original binaries.

### Meaning of OmarchyLoadPatch

load_qtquick_611.patch makes the root pragma opt into scanner/interceptor changes:

1. Rewrite unversioned QtQuick imports to QtQuick 6.11.
2. Extend interception/scanning for local dynamically loaded and lower-case QML.
3. Accept the root marker without the unpatched launcher's unknown-pragma warning.

Its stated rationale is the new QtQuick Color singleton in Qt 6.12 shadowing
Omarchy's Color singleton. It is not proof that the shell requires Qt 6.12.
Our Qt 6.10.2 predates that stated collision, and blindly importing QtQuick 6.11
is not an appropriate lower-version compatibility solution. **Keep the current
unpatched runtime for now.** Any future port must test real local/dynamic imports,
Color resolution, and remaining Qt APIs. Do not silently add this patch, suppress
the marker warning, upgrade Qt, or claim full shell equivalence from module probes.

The original recipe also differs in build type (RelWithDebInfo), distributor,
prefix (/usr), and toolchain/Qt. It sets CRASH_REPORTER=Off; our explicit build
retains crash-handler support. The Arch ALPM compatibility hook must not be
copied or automatically translated into Ubuntu package-manager policy.

## Follow-up status

The [source pin and independent fail-closed host prototype](shell-gate.md) now
resolve the original shell revision and retain the complete root MIT notice.
The new host has contained authored-fixture coverage, but is not integrated into
the original startup paths. Component/asset notices, production dependency closure,
full-shell compatibility, graphical testing and security gates remain open.

## Safe next implementation slice

Before importing original code/assets into public candidate files:

1. Resolve the original Omarchy source revision and retain its complete license
   notices; package metadata says MIT, but the installed share tree lacks the
   complete license/source evidence needed for a distributable import. Assets
   and bundled components need separate provenance, not blanket MIT assumptions.
2. Implement and test an independent positive loader policy, with no active
   services, menu commands, mutable theme hooks, local plugins, or shared
   hardware/background startup. Missing/invalid configuration must load nothing.
3. Prepare a tiny original-widget trial candidate (bar/clock/spacer), explicitly
   incomplete rather than a substitute shell. Re-audit its shared dependencies;
   do not call the workspaces widget compatible before its Omarchy Lua helpers
   and the temporary global-workspace prototype have been reconciled.
4. Test local QML import/type resolution in containment before considering graphics.
5. Request separate approval for graphical context, service ownership, affected
   paths/backups, rollback, and session behavior. No lock/idle/power test is implied.

Compiler, protocol, generated tooling, rendering, authentication, corporate-policy,
and packaging acceptance gates remain open. No active Ubuntu configuration or
existing service has been changed by this phase.
