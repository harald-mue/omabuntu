// Ported subset of Omarchy's shell/plugins/menu/MenuModel.js at pinned
// commit 03ff1eff3812933f7088484533784d2f63eaf19a (MIT; the notice is
// preserved in licenses/Omarchy-MIT.txt). The functions below keep the
// upstream bodies; only the needed subset ships here. Deliberately absent,
// with their reasons recorded in plans/002-command-menu.md and
// docs/menu-surface.md: the JSONC parser and merge (the reviewed Python
// helper tools/menu_model.py parses and merges the definitions instead), the
// pacman/package guard machinery (no apt equivalent is approved), dmenu
// select/input modes, translation catalogs, and app-row merging (no desktop
// entry rows run through this menu; the app grid stays its own surface).

function item(items, id) {
  return items && items[id] ? items[id] : null
}

// Route resolution port: an exact id beats any alias, underscores normalize
// to dashes, and unknown strings fall through as the literal id so a
// misspelling still attempts to open it.
function resolveRoute(items, input) {
  var raw = String(input || "").toLowerCase().replace(/_/g, "-")
  if (!raw || raw === "go" || raw === "menu") return "root"
  if (item(items, raw)) return raw
  var order = Object.keys(items || {})
  for (var i = 0; i < order.length; i++) {
    var entry = item(items, order[i])
    if (!entry || !entry.aliases) continue
    for (var j = 0; j < entry.aliases.length; j++) {
      var alias = String(entry.aliases[j] || "").toLowerCase().replace(/_/g, "-")
      if (alias === raw) return entry.id
    }
  }
  return raw
}

function slugify(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "item"
}

function depthFor(items, id) {
  var depth = 0
  var current = item(items, id)
  var guard = 0

  while (current && current.parent && current.parent !== "root" && guard < 32) {
    depth += 1
    current = item(items, current.parent)
    guard += 1
  }

  return depth
}

function pathFor(items, id) {
  var labels = []
  var current = item(items, id)
  var guard = 0

  while (current && current.id !== "root" && guard < 32) {
    labels.unshift(current.label)
    current = item(items, current.parent)
    guard += 1
  }

  return labels.join(" \u2039 ")
}

function parentPathFor(items, id) {
  var entry = item(items, id)
  if (!entry || !entry.parent || entry.parent === "root") return ""
  return pathFor(items, entry.parent)
}

function isDescendantOf(items, id, ancestorId) {
  if (ancestorId === "root") return id !== "root"

  var current = item(items, id)
  var guard = 0
  while (current && current.parent && guard < 32) {
    if (current.parent === ancestorId) return true
    current = item(items, current.parent)
    guard += 1
  }

  return false
}

function childCount(items, itemOrder, id) {
  var count = 0
  var order = Array.isArray(itemOrder) ? itemOrder : []
  for (var i = 0; i < order.length; i++) {
    var entry = item(items, order[i])
    if (entry && entry.parent === id) count += 1
  }
  return count
}

function isVisible(items, itemOrder, whenResults, entry, depth) {
  if (!entry) return false
  if (entry.when && whenResults && whenResults[entry.id] === false) return false
  if (entry.kind !== "menu" && entry.kind !== "link") return true
  if (entry.provider) return true

  var guard = depth || 0
  if (guard >= 32) return false

  var target = entry.kind === "link" ? entry.target : entry.id
  var order = Array.isArray(itemOrder) ? itemOrder : []
  for (var i = 0; i < order.length; i++) {
    var child = item(items, order[i])
    if (child && child.parent === target && isVisible(items, itemOrder, whenResults, child, guard + 1)) return true
  }

  return false
}

function isDisabled(disabledResults, entry) {
  if (!entry || !entry.disabled) return false
  return !!(disabledResults && disabledResults[entry.id])
}

function labelFor(entry, checkedResults, disabledResults) {
  if (!entry) return ""
  var marked = (entry.checked && checkedResults && checkedResults[entry.id]) || isDisabled(disabledResults, entry)
  return marked ? entry.label + " \u2713" : entry.label
}

function searchableToken(value) {
  return String(value || "").replace(/[._-]+/g, " ")
}

function leafIdFor(id) {
  var parts = String(id || "").split(".")
  return parts.length > 0 ? parts[parts.length - 1] : id
}

function nameSearchText(entry) {
  if (!entry) return ""
  var aliases = []
  var values = (Array.isArray(entry.aliases) ? entry.aliases : []).concat(Array.isArray(entry.searchTerms) ? entry.searchTerms : [])
  for (var i = 0; i < values.length; i++) aliases.push(searchableToken(values[i]))
  return [entry.label, searchableToken(leafIdFor(entry.id)), aliases.join(" ")].join(" ").toLowerCase()
}

function termInSearchWords(term, text) {
  var words = String(text || "").toLowerCase().split(/\s+/)
  for (var i = 0; i < words.length; i++) {
    if (words[i] === term) return true
  }
  return false
}

function descriptionTextMatches(query, text) {
  var terms = String(query || "").toLowerCase().trim().split(/\s+/)
  for (var i = 0; i < terms.length; i++) {
    if (terms[i] && !termInSearchWords(terms[i], text)) return false
  }
  return true
}

function matchesQuery(entry, query, visible) {
  if (!entry || entry.id === "root") return false
  if (!visible) return false

  var nameText = nameSearchText(entry)
  var descriptionText = String(entry.description || "").toLowerCase()
  var terms = String(query || "").toLowerCase().trim().split(/\s+/)

  for (var i = 0; i < terms.length; i++) {
    if (!terms[i]) continue
    if (nameText.indexOf(terms[i]) >= 0) continue
    if (termInSearchWords(terms[i], descriptionText)) continue
    return false
  }

  return true
}

function searchScore(items, entry, query) {
  var needle = String(query || "").toLowerCase().trim()
  var label = entry.label.toLowerCase()
  var nameText = nameSearchText(entry)
  var descriptionText = String(entry.description || "").toLowerCase()
  var score = 80

  if (label === needle) score = entry.parent === "root" ? 2 : 0
  else if (label.indexOf(needle) === 0) score = 10
  else if (label.indexOf(needle) >= 0) score = 30
  else if (nameText.indexOf(needle) >= 0) score = 40
  else if (descriptionTextMatches(needle, descriptionText)) score = 60

  if (entry.kind === "menu" || entry.kind === "link") score -= 2

  return score * 1000 + depthFor(items, entry.id) * 25 + entry.order
}

function displayRow(items, itemOrder, checkedResults, disabledResults, entry, detail, score, section) {
  var target = entry.kind === "link" ? entry.target : entry.id
  return {
    itemId: entry.id,
    disabled: isDisabled(disabledResults, entry),
    kind: entry.kind,
    icon: entry.icon,
    iconFont: entry.iconFont || "",
    font: entry.font || "",
    label: labelFor(entry, checkedResults, disabledResults),
    target: target,
    detail: detail || "",
    path: pathFor(items, entry.id),
    childCount: (entry.kind === "menu" || entry.kind === "link") ? childCount(items, itemOrder, target) : 0,
    action: entry.action || "",
    provider: entry.provider || "",
    score: score || 0,
    section: section || ""
  }
}

// Provider rows carry the id of the submenu that produced them, so a provider
// that runs again drops its previous batch without disturbing static children
// declared in the definitions. Returns fresh objects; never mutate the maps
// in place (upstream comment preserved: a lost QML var write duplicated rows).
function swapProviderRows(items, itemOrder, menuId, rows) {
  var source = items || ({})
  var order = Array.isArray(itemOrder) ? itemOrder : []
  var incoming = Array.isArray(rows) ? rows : []
  var nextItems = ({})
  var nextOrder = []

  for (var i = 0; i < order.length; i++) {
    var id = order[i]
    var existing = source[id]
    if (!existing || existing.providerMenu === menuId) continue
    nextItems[id] = existing
    nextOrder.push(id)
  }

  for (var j = 0; j < incoming.length; j++) {
    var row = incoming[j]
    if (!row || !row.id || nextItems[row.id]) continue
    row.providerMenu = menuId
    row.order = nextOrder.length
    nextItems[row.id] = row
    nextOrder.push(row.id)
  }

  return { items: nextItems, itemOrder: nextOrder }
}
