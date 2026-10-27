.pragma library

// This prototype admits only reviewed, nonvisual probe components. It is not an
// OS sandbox, source-code reviewer, or production original-shell integration.
var protectedIds = [
  "omarchy.background", "omarchy.dock", "omarchy.lock", "omarchy.notifications",
  "omarchy.polkit", "omarchy.battery", "omarchy.idle", "omarchy.media",
  "omarchy.nightlight", "omarchy.remote-session"
];

function plainObject(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  var prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function exactKeys(value, expected) {
  if (!plainObject(value)) return false;
  var keys = Object.keys(value).sort();
  return JSON.stringify(keys) === JSON.stringify(expected.slice().sort());
}

function validId(value) {
  return typeof value === "string" && /^[a-z][a-z0-9.-]{0,63}$/.test(value)
    && protectedIds.indexOf(value) === -1;
}

function fixtureUrl(value) {
  if (typeof value !== "string" || value.length > 512
      || value.indexOf("file:///probe/components/") !== 0) return false;
  var decoded;
  try { decoded = decodeURIComponent(value); } catch (error) { return false; }
  if (decoded.indexOf("file:///probe/components/") !== 0
      || /[\\\x00-\x20?#]/.test(decoded) || !decoded.endsWith(".qml")) return false;
  var segments = decoded.split("/");
  return segments.indexOf("..") === -1 && segments.indexOf(".") === -1;
}

function deny(reason) {
  return { ok: false, entries: [], reason: reason };
}

function evaluate(text, catalog) {
  try {
    if (typeof text !== "string" || !text.trim() || text.length > 65536)
      return deny("Missing or oversized configuration");
    var config = JSON.parse(text);
    if (!exactKeys(config, ["schema_version", "components"])
        || config.schema_version !== 1 || !Array.isArray(config.components)
        || config.components.length > 16) return deny("Invalid configuration schema");
    if (!plainObject(catalog) || Object.keys(catalog).length > 16)
      return deny("Invalid reviewed catalog");
    var keys = Object.keys(catalog);
    var reviewed = Object.create(null);
    for (var i = 0; i < keys.length; i++) {
      var key = keys[i];
      var record = catalog[key];
      var url = record && record.url;
      if (!validId(key) || !exactKeys(record, ["kind", "url", "capabilities"])
          || ["bar", "widget"].indexOf(record.kind) === -1
          || !Array.isArray(record.capabilities) || record.capabilities.length !== 0
          || !fixtureUrl(url)) return deny("Catalog contains an unreviewed component");
      reviewed[key] = url;
    }
    var ids = [];
    var entries = [];
    for (var j = 0; j < config.components.length; j++) {
      var id = config.components[j];
      if (!validId(id) || ids.indexOf(id) !== -1
          || !Object.prototype.hasOwnProperty.call(catalog, id))
        return deny("Unknown, protected, or duplicate component");
      ids.push(id);
      entries.push({ id: id, url: reviewed[id] });
    }
    // Validate the entire plan before any URL lookup or component preparation.
    return { ok: true, entries: entries, reason: ids.length ? "Reviewed fixture plan" : "Empty plan" };
  } catch (error) {
    return deny("Invalid configuration or catalog");
  }
}
