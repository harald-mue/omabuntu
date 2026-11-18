# Enable the original activation-focus policy

## Goal and evidence

Apply the user's explicit approval to adopt Omarchy's activation-focus rule in
the existing Hyprland configuration and reload it. Plan 123 verified original
Omarchy v4.5.0 commit `ac2690cd7be4f47e4a255f5e2e78d904d436b068` enables
`misc.focus_on_activate`, while the inspected session currently leaves the
reviewed Hyprland 0.57.0 default false/unset. The original setting permits eligible
application activation requests, including a singleton browser window on another
workspace; it is not an unconditional application-launch/focus guarantee.

## Current gap and proposed shape

Make one persistent addition to the existing misc block without replacing the
profile or modifying launcher behavior. Save exact original bytes, permissions,
hash, runtime focus/autoreload options and a title-free desktop snapshot under
ignored private work/. Temporarily guard automatic reload during staging, reload
explicitly, verify true/config-error-free and unchanged monitor/window/layout
state, then restore the previous autoreload option. A caught failure restores the
backed-up configuration only if the staged content still matches, then reloads
and verifies recovery rather than overwriting concurrent edits.

## Safety and exclusions

Approval covers this global desktop focus policy and a config reload. It does
not authorize new browser windows, synthetic activation/workspace switches,
profile/tab/history inspection, browser command changes, bar restart, installation,
services, security policy, GNOME, authentication, logout/reboot, commit or push.
Do not edit the separate reference package or private output geometry. This is a
local personal-profile change, not a silent change of every release's defaults.
A real browser click test remains user-controlled; successful option collection
is not proof of browser activation behavior or complete launcher parity.

## Tasks

- [x] Revalidate the supported API, original source rule and live prestate.
- [x] Back up the affected file and record prior runtime/snapshot state.
- [x] Apply the exact one-line focus policy and reload under the autoreload guard.
- [x] Verify the active option, config errors and preserved window/output/layout state.
- [x] Record recovery evidence and the remaining user-controlled browser test.

## Outcome

The exact one-line personal-profile addition was applied and configuration
reloaded successfully. The active option reports true/explicitly set. There are
no config errors, the previous autoreload value is restored, and the title-free
desktop snapshot matches the pre-change state. The private transaction includes
the original file bytes/permissions/hash, runtime options and recovery guard.
No application was launched, focused or moved and no bar restart was performed.
The browser click test was subsequently confirmed positively by the owner, who
requested integration for installations and updates. Plan 125 handles that
separate repository implementation. Published artifacts remain unchanged;
`docs/browser-launch-focus-parity.md` distinguishes the initial discrepancy,
applied local correction and subsequent source-default integration.
