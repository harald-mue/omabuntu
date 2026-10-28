"""Reviewed Elsewhen extraction: the original panel, without network or clock changes.

Vendor parents stay byte-identical. The staged panel keeps the city list in
the running process. Open-Meteo, GitHub profiles, notification delivery and
timedatectl set-timezone are removed. Offsets come from the read-only helper.
"""


def _strip_shell_ipc(text):
    opener = "ShellIpc {"
    start = text.find(opener)
    if start < 0 or text.find(opener, start + 1) != -1:
        raise ValueError("Elsewhen IPC witness differs")
    line = text.rfind("\n", 0, start) + 1
    depth = 0
    end = None
    for index, char in enumerate(text[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        raise ValueError("Elsewhen IPC block is unbalanced")
    if text[end:end + 1] == "\n":
        end += 1
    text = text[:line] + text[end:]
    if "ShellIpc" in text:
        raise ValueError("Elsewhen IPC removal differs")
    return text


def _cut(text, start, end, replacement):
    a = text.find(start)
    b = text.find(end, a if a >= 0 else 0)
    if a < 0 or b < 0 or a >= b:
        raise ValueError("Elsewhen extraction witness differs: " + start[:70])
    return text[:a] + replacement + text[b:]


def derive_model(data):
    text = data.decode()
    text = _cut(
        text,
        "function probeCommand(",
        "function parseOffset(",
        "function probeCommand(helper, ids, withLocal) {\n"
        "  var argv = [\"/usr/bin/python3\", String(helper || \"\"), \"probe\"]\n"
        "  if (withLocal) argv.push(\"--local\")\n"
        "  return argv.concat(ids || [])\n"
        "}\n\n",
    )
    text = _cut(
        text,
        "// argv that moves this machine's clock",
        "// ---- people\n",
        "// The system timezone is not changed from this panel.\n"
        "function timezoneCommand() { return [] }\n\n",
    )
    text = _cut(
        text,
        "// argv that refreshes each handle's cached profile",
        "function parseProfiles(",
        "function profilesCommand() { return [] }\n\n",
    )
    text = _cut(
        text,
        "function geocodeUrl(",
        "function pickGeocode(",
        "function geocodeUrl() { return \"\" }\n\n",
    )
    text = _cut(
        text,
        "function forecastUrl(",
        "function parseForecast(",
        "function forecastUrl() { return \"\" }\n\n",
    )
    return (
        "// Derived from Omarchy elsewhen/Model.js. Jason Fried, MIT.\n"
        "// Probe argv calls the read-only Omabuntu helper. Timezone changes,\n"
        "// place search and profile fetch are not available in this port.\n" + text
    ).encode()


def derive_panel(data):
    text = data.decode()
    marker = "updateEntryInline(root.moduleName"
    if text.count(marker) != 1:
        raise ValueError("Elsewhen persistence witness differs")
    start = text.rfind("\n    if (root.bar && root.bar.shell", 0, text.index(marker))
    end = text.index("\n", text.index(marker))
    text = text[:start] + text[end:]
    text = _cut(
        text,
        "    if (next.zoneChange !== \"\")",
        "    applyHere(next)\n",
        "    // Another zone updates this panel only. The machine clock stays put.\n",
    )
    note = text.find("omarchy-notification-send")
    if note < 0:
        raise ValueError("Elsewhen notification witness differs")
    line = text.rfind("\n", 0, note) + 1
    line_end = text.index("\n", note)
    text = text[:line] + "  function notify(title) { }" + text[line_end:]
    text = _cut(text, "  function fetchProfiles() {", "  function startPeopleEdit(",
                "  function fetchProfiles() {}\n\n")
    text = _cut(text, "  function requestPlaces(text) {", "  function lookupPlaces() {",
                "  function requestPlaces(text) {}\n\n")
    text = _cut(text, "  function lookupPlaces() {", "  function placesFor(text) {",
                "  function lookupPlaces() {}\n\n")
    text = _cut(text, "  function refreshFacts() {", "  function coordsFor(key) {",
                "  function refreshFacts() {\n    publishFacts()\n  }\n\n")
    text = _cut(text, "  function fetchWeather() {", "  function publishFacts() {",
                "  function fetchWeather() {\n    publishFacts()\n  }\n\n")
    probe = "Model.probeCommand("
    if text.count(probe) != 2:
        raise ValueError("Elsewhen probe witness differs")
    text = text.replace(probe, "Model.probeCommand(Quickshell.env(\"OMABUNTU_ELSEWHEN_HELPER\"), ")
    catalog = '["timedatectl", "list-timezones"]'
    if text.count(catalog) != 1:
        raise ValueError("Elsewhen catalogue witness differs")
    text = text.replace(catalog, '["/usr/bin/python3", Quickshell.env("OMABUNTU_ELSEWHEN_HELPER"), "zones"]')
    text = _cut(text, "  FileView {\n    id: zoneTab\n", "  // Heavy on the way out",
                "")
    text = _strip_shell_ipc(text)
    return (
        "// Derived from Omarchy elsewhen/Panel.qml. Jason Fried, MIT.\n"
        "// Original world-clock panel. Cities stay in this process: no shell.json\n"
        "// write, weather fetch, profile fetch, notification helper, or timezone change.\n" + text
    ).encode()


def _retarget_dir(text):
    old = 'Quickshell.env("OMARCHY_PATH") + "/shell/plugins/panels/elsewhen"'
    new = 'Quickshell.env("OMABUNTU_ELSEWHEN_DIR")'
    if text.count(old) != 1:
        raise ValueError("Elsewhen data-directory witness differs")
    return text.replace(old, new)


def derive_globe(data):
    text = _retarget_dir(data.decode())
    old = "Model.probeCommand(zones, false)"
    if text.count(old) != 1:
        raise ValueError("Elsewhen globe probe witness differs")
    text = text.replace(
        old,
        "Model.probeCommand(Quickshell.env(\"OMABUNTU_ELSEWHEN_HELPER\"), zones, false)",
    )
    return (
        "// Derived from Omarchy elsewhen/Globe.qml. Jason Fried, MIT.\n"
        "// Land and cities load from the staged directory. Offsets use the read-only helper.\n" + text
    ).encode()


def derive_base_panel(data):
    text = _strip_shell_ipc(data.decode())
    old = "import Quickshell.Io\n"
    if text.count(old) != 1:
        raise ValueError("Shared panel IO import differs")
    text = text.replace(old, "", 1)
    return (
        "// Derived from Omarchy Ui/Panel.qml, MIT.\n"
        "// IPC registration is not staged. The button opens and closes the panel directly.\n" + text
    ).encode()


def derive_miniglobe(data):
    text = _retarget_dir(data.decode())
    return (
        "// Derived from Omarchy elsewhen/MiniGlobe.qml. Jason Fried, MIT.\n"
        "// Land loads from the staged directory.\n" + text
    ).encode()
