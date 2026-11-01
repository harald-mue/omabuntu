# Public-install theme artwork

## Goal and evidence

A normal `curl … install.sh` install of a public release currently installs an
artwork-free bundle (redistribution of the Omarchy stills/previews is not
cleared), so the themes/backgrounds menus lose the Omarchy images until a local
checkout build is selected. The user wants the normal installer itself to check
the backgrounds and download them from the pinned remote into private user
storage when they are missing.

Evidence compared: `tools/download_backgrounds.py` (pinned manifest, integrity
lock, no-redirect fetch, atomic no-overwrite materialize), `background_backend`
assets resolution and `resolve_recorded` rebasing, `theme_backend.preview_path`,
`wallpaper_record.default_still` (session wallpaper record), `published_install`
flow, Omarchy artwork origin commit `03ff1eff3812933f7088484533784d2f63eaf19a`
recorded in `upstream/theme-backgrounds.json` with per-file sizes/blob hashes.
No upstream code changes; no new third-party assets are redistributed.

## Shape

- New `tools/user_artwork.py`: plan/apply for the pinned manifest into
  `~/.local/share/omabuntu/artwork` (XDG_DATA_HOME respected, symlink refusal
  inherited from the existing safe paths). Apply reuses the existing verified
  `materialize`/`fetch` (no redirects, size/hash checks, atomic non-overwriting
  writes, pinned raw.githubusercontent URLs only), writes a 0600 receipt, and
  requires the exact plan digest. Plan is read-only.
- Runtime fallback: `background_backend` resolves theme assets to the private
  artwork directory when the release bundle ships none; `theme_backend` does the
  same for picker previews; `resolve_recorded` also rebases recorded stills onto
  the private directory; `wallpaper_record.default_still` falls back to it so the
  next-login wallpaper record works on public releases.
- `published_install` offers the download with one `[Y/n]` after installation
  when the selected release is artwork-free and files are missing; complete or
  release-bundled artwork skips the prompt. Failure is reported and never
  silently treated as success; nothing else is blocked by it.
- Make `artwork`/`artwork-apply` targets and installer documentation.

## Safety and exclusions

One ordinary `[Y/n]` covers this single network download scope; the digest
recheck still guards apply. No service action, compositor reload, plugin load,
profile edit or package change. Images remain private user data; public bundles
and releases stay artwork-free. The receipt records source, notice and hashes.
No commit/push/publication in this task. Local unit/fixture results are not
clean-VM acceptance; a stock-VM curl install still needs a real run.

## Tasks

- [x] Back up affected sources and write plan 065 (this file).
- [x] Implement user_artwork plan/apply with receipt and strict rechecks.
- [x] Add runtime asset/preview/record/default-still fallbacks.
- [x] Offer the download once in the published flow; add Make targets and docs.
- [x] Regressions: fallbacks, conflicts, digest, prompts, receipt.
- [x] Full tests, clean-source and whitespace; report and request commit consent.

## Result

`tools/user_artwork.py` plans/downloads the pinned Omarchy theme set into
`~/.local/share/omabuntu/artwork` using the existing verified `materialize`
path (pinned URLs/sizes/blob hashes, no redirects, atomic no-overwrite writes),
writes a 0600 receipt and rechecks manifest/destination/digest on apply.
The published installer offers this once after installation when the selected
release ships no `config/menu/backgrounds`; complete artwork or release-local
artwork skips the question, failures are reported without silent success.
Menus (`theme_ids`/`theme_backgrounds`), picker previews, recorded-still
rebasing and the next-login wallpaper record fall back to the private
directory. `make artwork`/`artwork-apply` and docs/installer.md document it.
All 1011 tests passed isolated from real HOME, clean-source and whitespace
passed. The real machine already carries a downloaded set (user-run
`make artwork-apply`), confirming the flow; that is not clean-VM acceptance.
No commit/push/publication yet; releases stay artwork-free.