# Show imported WebP stills in the picker preview

## Goal and evidence

Theme background stills are upstream WebP files. The background picker
showed an empty preview because the system Qt 6.10.2 installation shipped
only GIF/ICO/JPEG/SVG image plugins, so `QImageReader` could not decode
WebP. hyprpaper decodes WebP itself, which is why the wallpaper still
changed while the preview stayed blank.

The user installed `qt6-image-formats-plugins` 6.10.2-1 from Ubuntu
resolute/universe (57 kB, provides `libqwebp.so`, depends on libwebp7).
Read-only verification:

- `/usr/lib/x86_64-linux-gnu/qt6/plugins/imageformats/libqwebp.so` exists
  and links the system libwebp.
- An offscreen Quickshell probe against a release still reports
  `PROBE 1 6336 2688` (Image.Ready) with the full source size.

## Shape and exclusions

Use the installed Qt plugin; no asset conversion, no new thumbnail cache
and no runtime helper. The picker keeps using the recorded still path.
No autostart, wallpaper engine, codec change or asset import is added.

## Tasks

- [x] Confirm the plugin file and its libwebp linkage.
- [x] Prove WebP decode with an offscreen Quickshell Image probe.
- [x] Restart only the Omabuntu shell after explicit user approval so the
      running process rescans its image plugins (PID 680725, .23, clean log).
- [x] Record the dependency and the verification in WORKLOG.
