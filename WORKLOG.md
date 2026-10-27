# Development summary

This is a curated public development log, not a record of a particular machine's
processes, package transactions or desktop sessions. Detailed operational logs,
old deployment histories and cleanup backups are retained privately under
ignored `work/`. Historical Git objects are not changed by editing this file.

## Ubuntu-native foundation

- Added read-only doctor reports, capability mapping, package planning and
  explicit safety/approval boundaries.
- Pinned upstream source candidates and retained third-party notices instead of
  running an Arch installer or exposing upstream helpers through PATH.
- Added contained runtime building, artifact verification and nonvisual import
  probes. Build success does not establish desktop or authentication acceptance.

## Selected original desktop components

- Retained selected original Omarchy presentation/layout sources with narrow
  Ubuntu backend adaptations and deterministic generated mirrors.
- Added bar/frame, tray, audio/network panels, calendar, application launcher,
  command menu, image picker, keybinding view and floating-workspace dock paths.
- Kept excluded startup, privileged, authentication and unsupported behavior
  explicit. The full unmodified original shell is not deployed.

## Local installation and desktop integration

- Added sealed versioned local releases, identity-checked session control,
  transaction backups, rollback/recovery and separately approved login autostart.
- Normal desktop components use an explicit untimed session grant. Autostart
  is not crash supervision, and lock/idle/suspend acceptance is separate.
- Added managed compositor settings, title-bar plugin registration and recorded
  wallpaper restoration, without arbitrary configuration replacement.
- Fixed login readiness and process-lifetime issues, then prevented wallpaper
  helper bytecode from invalidating installed releases.
- Added atomic per-workspace mode persistence, executable Lua regressions,
  delayed-state restore and serialized floating-window claims.
- Added the approved manual screen-lock chord `SUPER+CTRL+L`. It runs the
  installed `lock --apply` helper once, on key release, so the held chord is
  not delivered to Hyprlock. Super+K lists that row and does not launch it.
  Idle and suspend stay unbound. The two-column keybindings card is included
  in the approved shell update below.
- A window moved between a floating and a tiling workspace is arranged the way
  Omarchy's move handler does: the mode's own floated window is tiled again on
  the way out, and a tiled window dragged onto a floating workspace is claimed.
  A window floated on its own stays floating. Fullscreen, click-to-focus, and
  the second floating-workspace tag stay excluded. The approved bar restart now
  serves this shell, including the two-column Super+K card. Hyprland was not
  reloaded.
- App launches from the app grid and the floating dock now arm Omarchy's
  delayed "Launching …" notice. It appears only when no window has arrived
  after two seconds, passes clicks through, and is not a notification. The
  approved bar restart serves this notice, and the user confirmed it.
- A real login and workspace persistence were user-confirmed. Disabled
  hyprpaper's independent splash and obtained visual confirmation; the
  compositor's splash flag alone does not control the wallpaper daemon.

## Publication preparation (plan 023)

- Excluded local wallpaper and preview directories from Git without deleting
  their contents; retained source provenance and existing third-party notices.
- Made local image staging optional and removed imported-image dependence from
  the installer codec probe. Local bundles can still include local images and
  are not automatically cleared for redistribution.
- Required explicit verified runtime build directories rather than a fixed
  developer timestamp; help/plan modes remain non-activating.
- Refreshed README and installation guidance, added a central third-party notice
  inventory and a repeatable clean-source verification workflow.
- Passed 542 unit tests locally and in an asset-free candidate export. A new
  contained native build from pinned archives, all 32 runtime checks, desktop/
  command-menu/image-picker fixtures, asset-free packaging, installer preflight
  and release relocation also passed without reusing old work inputs.
- The native preflight exposed Qt rejection of a valid 38-byte 1x1 WebP fixture;
  replaced it with an authored 16x16 lossless gradient and repeated preflight.
- Reversibly archived two superseded build directories privately with their
  original paths/inodes recorded. The retained original runtime still verifies,
  and all 120 local images still match recorded upstream blob checksums.
  Plan 023 deleted no old build bytes, large diagnostic logs or recovery backups;
  permanent pruning required a separate approval (see plan 024 below).
- Archived the previous operational diary privately before this rewrite.
  Existing Git history is deliberately unchanged; no commit, remote or public
  upload is authorized by this cleanup.

Verification results and bounded local artifact cleanup are recorded in plan
023. Unit, isolated-runtime and clean-source checks have different scopes and
must not be described as fresh-machine, visual or security acceptance.

## Approved archived-build pruning (plan 024)

- After explicit user approval, permanently deleted only the two superseded
  build directories previously archived by plan 023: approximately 2.42 GiB of
  logical build data. Original paths/identities and deletion outcomes are
  recorded privately; metadata does not restore the deleted contents.
- Both the retained original runtime stage and the new clean-source runtime
  stage still pass integrity verification. Other backups, release bundles,
  images, diagnostic logs and recovery material were not removed.
- No desktop, service, package, Git index, commit or publication changes.

## Authorized source commit preparation (plan 025)

- Verified access to the user-named GitHub repository and prepared an explicit
  source-only commit candidate, excluding local images and all private work data.
- Checked the full current candidate and the existing commit's file history with
  local secret/privacy patterns. Reviewed the findings as UI text, systemd unit
  names and authored sandbox paths. No dedicated secret scanner was available;
  this bounded check is not exhaustive security or redistribution clearance.
- The full 542-test unit suite and independent clean-source verification pass.
  Preserve existing history and hooks; use the user-requested commit identity
  only for the commit process, without persistent Git configuration changes.
- Reviewed the explicit 295-file staged candidate. Fixed three existing authored
  whitespace defects; retained the imported QR generator's original formatting
  and license bytes. Its known upstream whitespace is the only diff-check
  exception; hooks and source verification are not bypassed.
- Remote creation, push and publication remain separate from this local commit.

## Approved GitHub history integration (plan 026)

- After the subsequent push approval, found an independent GitHub initial commit
  containing only an MIT license. The user explicitly approved preserving both
  histories with a merge rather than replacing either branch history.
- Resolved the sole LICENSE add/add conflict by retaining the copyright notices
  for Harald Müller and Omabuntu contributors. MIT permission/disclaimer and all
  third-party licenses remain unchanged.
- Prepared a normal merge commit and fast-forward push using the requested
  process-local author/committer identity. No force push, history rewrite,
  repository visibility change, binary release or desktop deployment is part
  of this operation. All 542 unit tests and clean-source verification pass;
  the 296-file text-only candidate excludes images, binaries and private work.
  Actual commit/push outcomes are recorded privately and in Git; validation
  precedes execution.
