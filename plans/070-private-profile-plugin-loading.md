# Persistent plugin loading for the preserved private profile

## Goal and evidence

After a reboot the verified hyprbars was not loaded: `hyprctl -j plugin list`
returned `[]`. The private `~/.config/hypr/hyprland.lua` still loaded the legacy
`~/.local/lib/omabuntu/hyprbars.so` (0.56 build, 2026-10-25), which fails the
Hyprland 0.57 version check. The verified 0.57 manager build
(`/var/cache/hyprpm/muha/hyprland-plugins/hyprbars.so`, receipt
`~/.local/state/omabuntu/hyprpm.json` `activated=true`, sha `f5a1d4ae…`) exists,
but nothing loads it at login.

The reviewed durable route is the explicit persistent login grant
(`tools/plugin_login.py`, invoked from an owned `omabuntu-activation.lua` via
`install.sh --session-activate --enable-plugin-login --apply`), which rechecks
receipts, hashes, repository pins, header fingerprints and compositor ABI at
every `hyprland.start` before one `hyprpm reload`.

Read-only evidence on this machine:

- `./install.sh --session-config --plain` is BLOCKED: "Existing unowned Hyprland
  profile is not overwritten or merged automatically." The private entry has
  user lines; `--adopt-managed` cannot adopt it (adoption is blocked by user
  lines), and the project never replaces a private profile.
- `./install.sh --session-activate --plain` is BLOCKED fourfold: "Prepare the
  generic session before activation" (`~/.local/state/omabuntu/session-config.json`
  is absent), and the existing `hyprpaper.conf`, `omabuntu-shell.service`,
  `omabuntu-shell-wait.py` are "not installer-owned".
- `plugin_login.verify` itself requires `session-activation.json` with
  `plugin_login_enabled: true`, `library: None`, the matching release name and
  owned activation/titlebar file hashes. Hand-crafting that receipt would be
  forging it, which the project refuses.
- Selected release `release-0.1.7` is a manager bundle (`native/hyprpm.json`,
  plugin pin `d2427d4d…`), with `helpers/plugin_login.py` present.

## Decision

Route B (owned activation with the receipt-checked login grant) is **not
available on this machine without abandoning the preserved private profile**;
adopting/replacing that profile is refused by design, and receipts may not be
forged. Route A (the private `hyprland.start` loader pointing at the verified
manager artifact, applied 2026-11-01 with backup
`~/.config/hypr/hyprland.lua.bak-20261101T140149Z`) therefore stays as the
documented bridge: fail-closed (the compositor refuses ABI-mismatched plugin
bytes), one line, reversible.

Residual weaknesses of A, to be fixed in the repository rather than worked
around locally:

1. The managed snippet `config/hypr/omabuntu-managed.lua` still attempts the
   legacy `~/.local/lib/omabuntu/hyprbars.so` load at every config parse — for
   manager-mode bundles this is a wrong-mode load attempt (and log noise) that
   the bundle mode can decide at packaging/deployment time.
2. The private loader path is machine-specific and unchecked; fresh public
   installs must keep using the owned activation route (they do).

## Proposed follow-up (plan 071, not started)

- Render/ship the managed snippet per bundle mode: manager bundles
  (`native/hyprpm.json`) deploy a snippet **without** the legacy artifact
  load; legacy bundles (`native/hyprbars.so`) keep it. Untouched installed
  snippets are replaced by the normal snippet adoption path.
- Tests for both modes and for the adoption; documentation update.
- Requires explicit consent; nothing is implemented in plan 070.

## Safety and exclusions

No receipt is forged, no private profile adopted or replaced, no service,
package or compositor change, no plugin load in this plan. `make
plugins-repair-apply` (one unforced `hyprpm reload` for the running session)
remains the separately approved live step. Clean-VM/login acceptance stays
outstanding.

## Tasks

- [x] Gather read-only evidence for both routes on this machine.
- [x] Record the decision: A stays as the bridge, B is blocked by profile
      preservation, the durable fix moves to the repository (plan 071).
- [ ] On consent: implement plan 071 (bundle-mode-aware managed snippet) and
      deliver it through a later signed release.

## Result

Plan 070 documents why the reboot lost the titlebars (legacy loader), why the
receipt-checked login grant cannot be installed on this preserved private
profile, and that A is the best available bridge here. No file outside the
private profile backup was changed; the repository follow-up (071) awaits
approval.