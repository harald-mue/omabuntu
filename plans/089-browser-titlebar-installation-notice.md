# Explain browser titlebars during installation

## Goal and evidence

Add an informational installation notice and user documentation for browser CSD
versus Omabuntu floating-workspace titlebars. The user confirmed that enabling
Chrome's "Use system title bar and borders" solves their Chrome appearance
problem; Edge is currently out of scope for a fix. Compare plan-087 exact
Chromium 156.0.8078.79 source, the user's result, current installer presentation
and titlebar documentation. Omarchy reference remains v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; no universal upstream CSD suppression
is claimed.

## Gaps and shape

The installer does not explain browser-owned buttons or the manual Chrome
appearance setting. Add shared informational text to the published install
completion path (including already-current installs) and the human-readable
local release review. Document where to look, the exact English toggle, expected
tiling/floating-workspace behavior, rollback and capability/PWA/GNOME caveats.
Keep Edge explicitly unverified rather than suggesting Chrome's setting exists
there. Keep JSON output machine-readable. Preserve previous uncommitted research.

## Safety and exclusions

Back up affected repository files before editing. Text-only installer guidance:
no browser detection, profile reads/writes, launch/restart, prompts, GNOME/GTK
changes, plugin load/reload, session transition, package change, installation,
commit or publication. User confirmation is local functional feedback, not fresh
GNOME login or all-browser acceptance. No reference-package changes.

## Tasks

- [x] Back up repository prestate and add shared installer guidance.
- [x] Add installation/titlebar documentation and update research status.
- [x] Add regression coverage for notice placement/content and JSON safety.
- [x] Run the full unit suite and diff checks; record remaining acceptance limits.

## Outcome

Shared notice text in `tools/setup_ui.py` is shown after verified published
installation/current-release checks and in human local install/update reviews,
not rollback reviews or JSON output. It explains the exact manual Chrome toggle,
original-state recording/undo, Edge's unresolved status and the absence of any
automatic browser or GNOME/GTK changes. The installer and hyprbars documentation
include expected behavior, theme-button distinction and GNOME/PWA limitations;
the research report records subsequent user-confirmed Chrome appearance success.

Repository prestate backups/hashes/modes and the full test log remain privately
under ignored `work/browser-titlebar-notice-089/`. All 1082 unit tests pass and
`git diff --check` passes. No desktop changes, installation, browser launch,
commit or publication occurred. Existing published immutable releases do not
acquire this notice until an approved build/release distributes these changes.
Edge, GNOME login, PWA/PiP and full button-action acceptance remain unclaimed.
