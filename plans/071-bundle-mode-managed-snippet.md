# Bundle-mode-aware managed snippet

## Goal and evidence

The installer-managed snippet `config/hypr/omabuntu-managed.lua` contains the
legacy titlebar artifact load:

```lua
local titlebars = home .. "/.local/lib/omabuntu/hyprbars.so"
local artifact = io.open(titlebars, "r")
if artifact then
  artifact:close()
  hl.plugin.load(titlebars)
end
```

That load is the **legacy bundle** mode (`native/hyprbars.so` deployed to
`~/.local/lib/omabuntu/`). For **manager bundles** (`native/hyprpm.json`, the
default for every new build and every public release), plugin loading is owned
by the explicit activation/login grant (`tools/plugin_login.py`, receipt-checked
`hyprpm reload`), and the artifact load is a wrong-mode attempt: on machines
where a stale legacy artifact exists it fails the compositor version check at
every config parse (log noise; plan 070 recorded it losing the titlebars after a
reboot until the private loader bridge was applied).

Evidence: `package_user.prepare` stages `config/hypr/omabuntu-managed.lua`
verbatim into every bundle (tools/package_user.py, staging loop) while the same
`prepare` already decides the bundle mode (`plugin_build is None` →
`stage_manager_policy`, else `stage_plugin`). `session_config.adoptable`
compares an installed untouched snippet against the *release's* copy of the
template, so a per-release rendered variant stays consistent with adoption.
The generic fresh profile (`session-template.lua.in`) never includes the
managed snippet, so fresh public installs are unaffected; the rendered variant
matters for snippet adoption and for documented bundle content.

## Shape

- `tools/package_user.py` gains `managed_snippet(data, *, manager)`:
  - legacy mode (`manager=False`) returns the template bytes unchanged;
  - manager mode replaces the exact legacy load block (comment included) with
    a manager note. The `local home` binding stays, because the saved-workspace
    loader below uses it. A witness check (`count == 1`) refuses template drift.
- `prepare` renders the staged `hypr/omabuntu-managed.lua` per bundle mode
  (`plugin_build is None` → manager). All other staged config bytes unchanged.
- The checkout template and `make hypr-settings` stay as they are; this is a
  packaging-time render, not a new deployment mode.
- Tests in `tests/test_publication_cleanup.py` for both modes, the preserved
  `home` binding and the drift refusal; documentation in
  `docs/plugin-management.md` and `docs/user-installation.md`.

## Discovered gap (recorded, not implemented here)

`config/hypr/session-template.lua.in` sets only `no_donation_nag`, not
`no_update_news`: the generic fresh profile still gets the update-news popup
that plan 067 suppressed only in the managed snippet. That is a separate
change with its own review (plan 072 candidate), not part of this packaging
render.

## Safety and exclusions

No plugin load, no deployment, no service or package change. The render only
changes which bytes a **bundle** records; installed snippets on this machine
stay untouched (the plan-070 bridge remains). Legacy bundles keep the exact
current behavior. No commit/push/release in this task beyond the reviewed
commit.

## Tasks

- [x] Add `managed_snippet` and render the staged snippet per bundle mode.
- [x] Add the mode tests and update the two documents.
- [x] Run the full suite and record the plan-072 candidate gap.

## Result

`tools/package_user.py` renders `config/hypr/omabuntu-managed.lua` per bundle
mode at packaging time: manager bundles (`plugin_build is None`, every new
build and public release) ship the snippet without the legacy
`~/.local/lib/omabuntu/hyprbars.so` load, keeping the `home` binding for the
workspace loader; legacy bundles ship the template unchanged. A witness check
refuses template drift. Four new tests in `tests/test_publication_cleanup.py`;
full suite 1035 tests OK. `docs/plugin-management.md` and
`docs/user-installation.md` document the render. Installed snippets on the
development machine are untouched; the plan-070 bridge remains until a later
signed release ships this render.