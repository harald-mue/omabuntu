pragma Singleton
import QtQml

// Narrow compatibility adapter, NOT the original Omarchy Style singleton.
// Only the spacer base fallback is provided; no probes, watchers or theme IO.
QtObject {
  readonly property QtObject bar: QtObject {
    readonly property int sizeHorizontal: 32
  }
}
