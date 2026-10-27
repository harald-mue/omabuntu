import QtQml
import "LoadPolicy.js" as Policy

// Deliberately nonvisual and disconnected from the original shell. The shipped
// catalog is empty; only the isolated test harness supplies trusted fixtures.
QtObject {
  id: gate

  property string configurationText: ""
  property var reviewedCatalog: ({})
  readonly property int activeCount: _owned.length
  readonly property int loadAttempts: _loadAttempts
  readonly property string state: _state
  readonly property string reason: _reason

  signal objectCreated(string componentId, QtObject instance)

  property bool _ready: false
  property bool _begun: false
  property bool _revoked: false
  property int _generation: 0
  property int _loadAttempts: 0
  property string _state: "blocked"
  property string _reason: "No configuration or reviewed catalog"
  property var _owned: []

  function revoke(message) {
    _revoked = true;
    _generation++;
    var previous = _owned;
    _owned = [];
    _state = "blocked";
    _reason = String(message || "Load approval revoked");
    for (var i = 0; i < previous.length; i++) previous[i].destroy();
  }

  function reload() {
    // Revocation is sticky for this host instance. Never recreate objects while
    // Qt may still be processing deferred destruction from the old generation.
    revoke("Reload requires a fresh reviewed host instance");
  }

  function start() {
    if (_begun || _revoked) {
      revoke("Repeated start is not an activation grant");
      return false;
    }
    _begun = true;
    var token = ++_generation;
    var plan = Policy.evaluate(configurationText, reviewedCatalog);
    if (!plan.ok) {
      revoke(plan.reason);
      return false;
    }
    if (!plan.entries.length) {
      _state = "empty";
      _reason = plan.reason;
      return true;
    }
    for (var i = 0; i < plan.entries.length; i++) {
      if (_revoked || token !== _generation) return false;
      var entry = plan.entries[i];
      _loadAttempts++;
      var component = Qt.createComponent(entry.url, Component.PreferSynchronous);
      if (_revoked || token !== _generation || component.status !== Component.Ready) {
        var failure = component.errorString();
        component.destroy();
        revoke("Component preparation failed or approval changed: " + failure);
        return false;
      }
      var object = component.createObject(null);
      component.destroy();
      if (!object || _revoked || token !== _generation) {
        if (object) object.destroy();
        revoke("Object creation failed or approval changed");
        return false;
      }
      var next = _owned.slice();
      next.push(object);
      _owned = next;
      objectCreated(entry.id, object);
      if (_revoked || token !== _generation) return false;
    }
    _state = "fixtures-loaded";
    _reason = "Nonvisual fixtures only; not original-plugin approval";
    return true;
  }

  onConfigurationTextChanged: if (_ready) revoke("Configuration changed");
  onReviewedCatalogChanged: if (_ready) revoke("Reviewed catalog replaced");
  Component.onCompleted: {
    _ready = true;
    start();
  }
  Component.onDestruction: {
    var remaining = _owned;
    _owned = [];
    for (var i = 0; i < remaining.length; i++) remaining[i].destroy();
  }
}
