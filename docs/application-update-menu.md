# Application Update menu

## Scope and original placement

The repository implements **Update > Omabuntu** in the command menu, immediately
before System. This follows the Update root placement and icon of Omarchy
v4.5.0 commit `ac2690cd7be4f47e4a255f5e2e78d904d436b068`; only the application
entry is retained and renamed. See [upstream assessment](update-menu-assessment.md).
No original update/provisioning scripts are imported or executed.

The configured shortcut remains **Super+Space** (`omabuntu:menu`), not Ctrl+Space.
No keybinding, desktop deployment or live update is part of this implementation.
The original command-menu component is retained; this adds no update panel,
background polling, service, autostart or expiry timer.

## Interaction and permissions

Selecting Omabuntu launches the installed `application_update.py` in an
independent `xdg-terminal-exec` terminal with fixed argv. It is not a shell
command assembled from user input. The terminal and runner are independent of
the shell that may be restarted. Missing terminal/runner inputs produce a menu
error, not a fallback installer. Launch success means only that the terminal
process was started, not that a check, download or update succeeded.

The runner requires an interactive terminal, a normal user, an unambiguous
Hyprland Wayland identity, the selected intact installed release and its
recorded running shell. It offers no unattended/auto-yes options. The user
separately confirms:

1. **Check signed public release metadata** over the network.
2. **Download and verify** a newer compatible application candidate.
3. **Apply the exact reviewed plan**, including the recorded shell-only restart.

Opening/searching the command menu or evaluating guards performs no network
check. Explicitly activated checks use bounded HTTPS requests through the
existing downloader's host/redirect policy. The GitHub API provides a candidate
tag only; availability is based on signature-verified checksums and signed
metadata, not arbitrary API text. The archive must match the signed size and
digest and pass the existing safe extraction and bundle verification checks.
The publisher public key is shipped as part of the verified installed payload;
no moving bootstrap/key is downloaded or silently substituted.

A matching public version performs no deployment and is reported as a version
match, not proof that the installed bytes equal the public archive. Public
versions are compared numerically, not lexicographically. The publisher's exact
`release-VERSION` bundle prefix is normalized for both installed-version policy
and incoming-bundle comparison with numeric signed metadata; local suffixes or
adaptation markers are not stripped or bypassed. Older public releases
are refused. Local/non-semantic release names, adaptation provenance markers
and unknown provenance are blocked from automatic public replacement. The
standard `local_image_directories` provenance field is not an adaptation marker.
There is deliberately no hidden override to replace unpublished local fixes.
This protects the currently used private derivatives from older public latest.

## Application-only transaction

The runner reuses `release_update.review/apply` and the existing manager's
verified selection, control lock, journals, contract/schema rules, runtime
preflight and startup-failure recovery. A second update terminal is refused by
a private operation lock. Selection/process drift causes a new review to be
required. Existing update locks and unresolved-journal refusal remain in force.

A dedicated Installation subclass always disables wallpaper restoration,
including restoration of the previous application after failed startup.
The runner never invokes `published_install.py`, setup provisioning, package
installation, source compilation, automatic legacy adoption or native migration.
Missing dependencies, incompatible native/state targets or failed preflight
block the switch rather than installing prerequisites or prompting for sudo.
Power/lock safety and the existing refusal while a locker is present are kept.
The post-v0.2.1 source preflight shares the [native patch-family policy](native-compatibility.md)
and reports concrete failed checks as well as the private report path. It still
requires runtime checks and does not generalize native-contract migrations or
change plugin ABI approval. That source follow-up is not retroactive to v0.2.1.

Network metadata, downloads, extracted candidates and reports are retained in
private `$XDG_CACHE_HOME/omabuntu/menu-updates/<timestamp>/` (default `~/.cache`).
The current updater cannot clean that cache automatically; retained data may be
large. Treat it as private. Preflight reports are explicitly redirected there
instead of writing into the immutable installed updater payload. The ordinary
updater transaction retains its normal private selector/launcher backups and
application update journals. Existing preference files are not migrated/reset.

The old application release is retained. Startup failure triggers the existing
previous-selection/startup recovery; it is not proof of successful visual or
security acceptance. Interrupted transactions remain blocked for explicit
journal recovery rather than silently resuming. The terminal keeps its result
or error visible until Enter is pressed. There is no process lifetime timeout
on the desktop components or update terminal; network/probe readiness limits
remain bounded diagnostics.

## Packaging and verification

`tools/update_payload.py` stages the Python import closure of the application
runner and signature/archive path, plus the reviewed runtime prerequisite
manifest, hyprpm policy and publisher public key under `updater/`. Those files
are covered by the release manifest. Imported build/provisioning modules are
existing dependency code only; this runner never calls their mutating entry
points. `tools/menu_update.py` is a small separately packaged menu launcher.
The complete closure can import/validate policy without this checkout or Make.

`tests/test_menu_update.py` covers synthetic signed-metadata ordering, signature
failure, offline handling, damaged metadata/archive, version/local-provenance
policy, cancellation stages, process drift, stopped-session refusal, actual
transaction switching/recovery with mocked native probes/processes, wallpaper
suppression, prerequisite refusal, detached fixed-argv launch and standalone
payload imports/report location. Existing signature tests use disposable keys;
no private publisher credentials are needed. The contained menu fixture covers
the added root row/navigation without starting a host terminal or update.

## Deployment and acceptance boundary

After explicit approval, the menu and complete updater payload were deployed
as a new private local release with a bar-only restart. Startup/manifest checks
passed, the installed definitions contain Update > Omabuntu, all three bars and
the independent menu registration are present, and relevant preferences remain
byte-for-byte unchanged. Runtime/assets and other shell components were retained.
The previous application is available for rollback. No terminal was launched or
release service contacted during deployment; no public update was performed.

The user subsequently confirmed terminal invocation and cancellation before
network access. This records user feedback on that limited interaction, not an
independently observed network trace.

After separate approval, a metadata-only diagnostic exercised the same review
logic with the verified installed trust key and matching deployed sources.
The actual public v0.2.0 signature and metadata verified. The private installed
derivative correctly returned `local-release-blocked`. Exactly four discovery/
metadata fetches occurred; archive download/apply callbacks were forbidden.
Current/previous selection, bundle integrity and running identity were unchanged.
This validates signed discovery and the current local-version refusal, not a
native terminal's behavior through a full update.

The feature and publisher-style bundle-version comparison fix are now shipped
in public [v0.2.1](releases.md#v021-release-scope). Publishing it does not switch
an existing installation; a private/local derivative remains protected from
automatic replacement. The earlier private deployment is not retroactively
changed by publication.

Real update-switch acceptance remains outstanding; a Git commit or published
release alone does not establish that acceptance.
Tests do not establish native terminal focus/floating behavior, recovery after
an actual shell-parent exit, a real public-version update pair, GNOME
coexistence or fresh-machine behavior. Those remain explicit acceptance gates.

Excluded from this batch: Status/Rollback menu entries, Process/Shell restart,
channels, kernel, firmware, Config resets, Ubuntu upgrades, theme/artwork updates,
passwords/encryption, system time/timezone and hardware/service restarts.
