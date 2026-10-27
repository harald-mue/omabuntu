# Package mapping

Package mapping is capability-based, not a translation of the source package list.

| Capability | Candidate | Current policy |
|---|---|---|
| Compositor | hyprland | Inspect existing installation before any change |
| Desktop shell | quickshell | No local APT candidate; [pinned build investigation](quickshell.md) |
| Session management | uwsm | Use only if appropriate for existing startup |
| Qt/QML | Qt 6 runtime and selected QML modules | Derive requirements from active loading paths |
| Terminal | ghostty | Existing target package; no installation required yet |
| Audio | pipewire, wireplumber | Preserve existing Ubuntu services |
| Networking/Bluetooth | network-manager, bluez | Preserve corporate configuration |
| Portals | xdg-desktop-portal-hyprland and session backends | Verify selection, do not globally replace |
| Clipboard | wl-clipboard | Preserve privacy; never import history |
| Capture | Omasnap or an explicitly agreed alternative | Packaging and licensing unresolved |
| Lock/idle | Existing approved mechanism first | No automatic activation |

APT candidates depend on enabled sources, architecture, and metadata freshness.
No additional source was added. The exact packages the running desktop needs —
including the ones added for the screen lock and for building the hyprbars
titlebar plugin — are recorded in [installed dependencies](../docs/dependencies.md).
