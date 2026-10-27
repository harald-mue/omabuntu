# Compatibility and evidence

No Ubuntu desktop deployment is supported or validated yet.

## Source reference

The private reference records Omarchy 4.5.0rc1-1, Hyprland 0.56.2,
Quickshell 0.3.2.r7.g2b4501a-1, and Qt 6.12.0.
These are observed source versions, not established minimum requirements.
The reference records 248 active bindings and 40 shell manifests.

## Initial target observations

The following is a deliberately limited, manually selected summary of local
read-only inventory, not a supported package-source recommendation:

| Capability | Observed target state | Remaining work |
|---|---|---|
| OS | Ubuntu 26.04.1 LTS | Confirm future supported update range |
| Hyprland | Matching clean 0.56.2 commit; staged native Lua profile parses successfully | Interactive behavior, helper parity, and session tests remain open |
| Current session | GNOME on Wayland | Collect runtime evidence from an approved Hyprland session |
| Quickshell | Pinned 0.3.2 compiled and staged privately with expected revision | Optimized shaders and isolated imports/type probes pass; assess warnings, live services, and shell |
| Qt | Qt 6.10.2 runtime/development stack builds the pinned runtime | 9 Qt module probes pass; graphical and complete shell API acceptance remain open |
| UWSM | Package 0.25.2+ds-1 installed | Inspect actual session startup, avoid double wrapping |
| Ghostty | Package 1.3.0 installed | Check launch and theme compatibility |
| Hyprland portal | Package 1.4.1 installed | Verify portal selection and real screen sharing |
| Lock/idle | No validated path for this project | Preserve existing mechanisms; require separate acceptance |

Package data is not runtime proof. A missing qmake executable does not establish
that Qt runtime libraries are absent. A missing APT candidate can reflect stale
or incomplete local metadata. No APT refresh or source modification was performed.
An existing third-party PPA is not automatically approved for this project.

## Compatibility gates

1. Verify the exact installed/running Hyprland build, Lua language, events,
   dispatchers, window/layer rules, and config load path.
2. Verify Quickshell QML modules and PAM/Polkit features; do not infer them
   from a version string or from a working bar.
3. Check transitive helper calls and block Arch/system-management routes.
4. Verify Ubuntu authentication, account policy, and recovery before locking.
5. Validate laptop displays, scaling, portals, and service ownership.

Official starting points, to be checked against the actual target version before
implementation:

- https://wiki.hypr.land/
- https://github.com/hyprwm/Hyprland
- https://quickshell.org/docs/
- https://github.com/quickshell-mirror/quickshell

Initial version-specific source review is recorded in [research](research.md).
It confirms native Lua feasibility, not complete configuration or runtime acceptance.
See the [capability matrix](capability-matrix.md) and
[Quickshell investigation](../packages/quickshell.md) for remaining gates.
