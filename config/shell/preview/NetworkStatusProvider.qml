import QtQml
import Quickshell.Networking
import "NetworkPresentation.js" as Presentation

// Passive native property subscription. No scanner, connectivity probe,
// activation, password lookup, settings mutation or disconnect call.
QtObject {
  readonly property var state: Presentation.snapshot(
    Networking.backend === NetworkBackendType.NetworkManager,
    Networking.devices ? Networking.devices.values : [],
    { Wired:DeviceType.Wired, Wifi:DeviceType.Wifi },
    Networking.connectivity,
    { Portal:NetworkConnectivity.Portal, Limited:NetworkConnectivity.Limited,
      Full:NetworkConnectivity.Full, None:NetworkConnectivity.None },
    Networking.canCheckConnectivity && Networking.connectivityCheckEnabled)
}
