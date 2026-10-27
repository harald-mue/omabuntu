.pragma library

// Geometry data only. No QML, URLs, commands, environment or mutable settings API.
function prepare(text) {
  try {
    if (typeof text !== "string" || text.length > 4096 || !text.trim()) return null;
    var value = JSON.parse(text);
    if (value === null || typeof value !== "object" || Array.isArray(value)
        || JSON.stringify(Object.keys(value).sort()) !== JSON.stringify(
          ["bar_size", "schema_version", "spacer_size", "vertical"])) return null;
    if (value.schema_version !== 1 || typeof value.vertical !== "boolean"
        || !Number.isInteger(value.bar_size) || value.bar_size < 1 || value.bar_size > 256
        || !Number.isInteger(value.spacer_size) || value.spacer_size < 0 || value.spacer_size > 4096)
      return null;
    return Object.freeze({schema_version: 1, vertical: value.vertical,
                          bar_size: value.bar_size, spacer_size: value.spacer_size});
  } catch (error) {
    return null;
  }
}
