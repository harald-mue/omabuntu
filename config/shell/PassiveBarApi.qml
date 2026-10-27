import QtQml
import "PassiveContract.js" as Contract

// Constructor-owned input; only the readonly geometry view is a widget API.
// This object is not a security sandbox for arbitrary QML or its trusted owner.
QtObject {
  required property string snapshotJson
  readonly property var snapshot: Contract.prepare(snapshotJson)
  readonly property bool valid: snapshot !== null
  readonly property bool vertical: valid ? snapshot.vertical : false
  readonly property int barSize: valid ? snapshot.bar_size : 0
}
