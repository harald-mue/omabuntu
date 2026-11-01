# Local installation repair diagnosis

## Goal and evidence

Diagnose the user's reported long-broken local desktop after the signed v0.1.3
application update reported success but deferred profile preparation and plugin
reconciliation. An application update is not a complete repair of private Lua,
preferences, services or native manager state. Do not describe it as such.

Compare selected immutable release and recorded process state, compositor version
and configuration errors, owned session/activation receipts and the exact failure
of healthy manager reuse. Reference Hyprland 0.57.0 commit
0aa6745f705f2c4b0a5004eb019ef76e5bbdb426, plugin commit
d2427d4d15b36df40468f5a58bbd67cdba19835d and Omarchy reference
03ff1eff3812933f7088484533784d2f63eaf19a if later visual comparison is needed.

## Safety and proposed shape

This request starts with read-only targeted diagnosis. Keep raw process/config
errors, receipts, logs and inventory under ignored private work/. Do not print
private configuration or collect screenshots. Do not run manager mutation,
package installation, live rules, service actions, desktop writes, reloads or
session transitions. No commit/push/publication is approved by this request.
Read private configuration only if needed and never execute/evaluate arbitrary
Lua as part of diagnosis.

Report separately what the update verified, what the diagnostics establish and
which visible failures still need user description. A later installer repair
path must preview affected owned/unowned paths, back them up, preserve GNOME and
private data and obtain explicit consent before desktop or manager actions. No
blind reset of private profiles, wallpaper or preferences; no boot/PAM/security
changes. This diagnosis is not approval to implement or apply those repairs.

## Tasks

- [x] Capture targeted private read-only state and the hidden reuse failure.
- [x] Separate actual faults from intentional guards and missing evidence.
- [x] Explain a concrete repair scope and request any needed visible symptoms.

## Read-only outcome

The selected signed application and its recorded bar process are current. The
compositor reports no configuration errors and the bounded current bar-log read
has no matched fatal/QML-error indicators; neither fact establishes correct
visual behavior. Manager build/library/header/repository checks pass up to live
state comparison: the persisted activation/enablement state is true, but the
current session has no loaded plugin. The installer hides that precise reuse
failure and falls back to the generic enabled-plugin preparation blocker.

The generic session receipt is absent. Existing private profile and older
wallpaper/unit/wait paths are not covered by current installer ownership receipts.
Their protection explains skipped adoption, not their correctness. No private
profile was evaluated, changed or reset. Raw paths/state remain in ignored work/.

A repair needs independent consent to reload the already verified enabled plugin
and to review/back up any private/legacy session-file integration; rebuilding or
blindly replacing the profile is not justified by these findings. Additional
visible layout/menu/shortcut failures require user description before defining
that part of the repair. No live action or source repair implementation occurred.
