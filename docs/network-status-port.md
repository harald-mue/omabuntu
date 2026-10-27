# Network status port

## Scope

The live bar no longer uses this view. Connection behavior is documented in
[network control](network-control.md). This file remains the regression record
for the earlier read-only status slice, **not the complete Omarchy network panel**.
NetworkStatusView composes the unchanged original BarIconButton and PopupCard.
It uses the unchanged original network Model.js for glyph selection. The
interface rows and status text are authored adapters, not a copy of the
original full configuration page. The popup labels its limited scope.

The original model was fetched individually from commit
03ff1eff3812933f7088484533784d2f63eaf19a, matched to the pinned Git tree and
reference bytes, and reviewed before import. Per-file provenance is in
upstream/clock-preview.json. The full MIT notice remains in vendor/omarchy/LICENSE.
The model contains dormant enterprise-connect command strings and a captive
portal URL. This view never references or executes either. Model import is
trusted code, not a sandbox or a grant to run those routes.

## Native backend and boundaries

NetworkStatusProvider reads Quickshell.Networking's NetworkManager backend:
backend availability, device type/name/connected state, connected Wi-Fi name
and signal, and cached connectivity. It subscribes to native properties, not
shell-command output. NetworkPresentation copies primitives before passing
them to delegates; no live WifiNetwork wrapper is retained in the view model.
Labels are rendered as plain text, not rich text.

- No activation, deactivation, forget, Wi-Fi toggle or profile edit.
- No nmSettings/secret reads, credential prompt, QR export or clipboard access.
- No active scan, nmcli/ip/iw command, network helper or HTTP request.
- No call to Networking.checkConnectivity; only already-cached state is shown.
- No DNS, band, route, firewall, certificate, proxy or VPN changes.
- Wired is preferred when wired and Wi-Fi are connected, matching Omarchy's
  display policy. This is **not** a default-route detector or VPN health check.
- An unavailable backend is unknown, not disconnected. Disabled connectivity
  checking gives unknown Internet status. Missing AP strength stays unknown.
- When the backend disappears, stale connected devices are not displayed.

Pinned Quickshell sources reviewed: src/network/nm/backend.cpp,
src/network/nm/wireless.cpp and src/network/wifi.hpp. Backend initialization
reads properties/devices/access points/settings. Explicit scan requests are
behind scannerEnabled; the provider never enables it. Importing the native
backend is not a generic permission boundary; safety here depends on the
reviewed inputs and absence of mutating API calls.

## Validation

169 Python contracts pass without starting Qt or DBus. Explicit contained checks:

```sh
python3 tools/check_tray_port.py --suite network --run --build-dir work/builds/<build-id>
```

Seven actual isolated Qt fixtures cover unavailable, disconnected, wired-first,
Wi-Fi signal/name, restricted connectivity, AP churn/device removal and a
deliberate assertion-negative control. They create the real view and original
UI dependencies with primitive inputs and a synthetic tray, never native
Networking or a host DBus connection. Mutating fake methods throw if called.
Original icon thresholds, frozen snapshots, stale-model rejection, and disabled
connectivity probes are checked. Positive cases require no warnings/errors;
the negative control must exit exactly 42 with its deliberate assertion.

Final network report: work/network-port/20261024T134509.609787Z/report.json.
Tray regression: work/tray-port/20261024T134516.414052Z/report.json.
Clock regression: work/clock-preview/20261024T134520.994782Z/report.json.
All report unchanged staged runtime artifacts. Earlier reports are retained.

Live run: work/clock-trial/20261024T134549.341765Z, pid 340301, 3600-second grant.
Three 26px surfaces and a reserved top area on every output remain. The app
shortcut remains registered. There is still a host-portal warning about the
unregistered org.quickshell app ID; no new QML/network error was logged at
startup. Live popup contents and pointer behavior need user acceptance.

## Change, backup and rollback

Project files only; no active Hyprland configuration was edited or reloaded.
The previous timed process was verified and replaced, and its staged files
remain intact. Stop only the verified TrialShell process to remove the surfaces
and subscriptions. No running applications or NetworkManager service is stopped.
A first live staging at work/clock-trial/20261024T134324.313080Z was replaced by
the final stale-backend guard version; it remains as evidence.

Full network configuration, audio/Bluetooth/monitor/power panels and workspace
modes remain separate unfinished portions of the bar port. This status slice
does not satisfy network-configuration acceptance.
