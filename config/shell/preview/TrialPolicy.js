.pragma library

// Fixed diagnostic profile, not arbitrary component/command configuration.
function prepare(text) {
  try {
    if (typeof text !== "string" || text.length > 4096 || !text.trim()) return null;
    var p = JSON.parse(text);
    if (p === null || typeof p !== "object" || Array.isArray(p)) return null;
    if (JSON.stringify(Object.keys(p).sort()) === JSON.stringify(["lifetime", "schema_version", "scope"])
        && p.schema_version === 1 && p.scope === "bar-session-v1" && p.lifetime === "session")
      return Object.freeze({schema_version:1, scope:p.scope, lifetime:"session"});
    if (JSON.stringify(Object.keys(p).sort()) !== JSON.stringify(["duration_seconds", "schema_version", "scope"].sort())
        || p.schema_version !== 1 || p.scope !== "clock-bar-trial-v1"
        || typeof p.duration_seconds !== "number" || !Number.isInteger(p.duration_seconds)
        || p.duration_seconds < 5 || p.duration_seconds > 3600) return null;
    return Object.freeze({schema_version:1, scope:p.scope, duration_seconds:p.duration_seconds});
  } catch (error) { return null; }
}
