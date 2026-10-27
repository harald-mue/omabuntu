pragma Singleton
import QtQml

// One discovery lease across all trial bars. Never adopt another client's scan.
QtObject {
  property var owners: []
  property var startedAdapter: null
  function acquire(owner, adapter) {
    if (owners.indexOf(owner) < 0) owners = owners.concat([owner]);
    if (adapter && adapter.enabled && !adapter.discovering) {
      adapter.discovering = true;
      startedAdapter = adapter;
    }
  }
  function release(owner) {
    owners = owners.filter(function(value) { return value !== owner; });
    if (owners.length === 0 && startedAdapter) {
      startedAdapter.discovering = false;
      startedAdapter = null;
    }
  }
}
