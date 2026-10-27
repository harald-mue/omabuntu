"""Derived Omarchy clock calendar. Vendor parents stay byte-identical.

The sealed read-only label is a different extraction and stays in
check_clock_preview.derive_clock. This module admits the original popup
surface and the bar button that opens it. It does not admit Shell IPC or the
privileged timezone picker.
"""


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Clock calendar extraction witness differs")
    return text.replace(old, new)


def derive_calendar(data):
    """Original month grid, with the IPC panel base removed."""
    text = data.decode()
    text = replace(text, '''Panel {
  id: root
  moduleName: "omarchy.clock"
  ipcTarget: "omarchy.clock"
  manageIpc: false
''', '''Item {
  id: root
  // The IPC panel base is not admitted. show/hide only flip opened.
  // A bar may keep the same object in session memory; this file does not
  // write configuration.
  property QtObject bar: null
  property string moduleName: "omarchy.clock"
  property var settings: ({})
  property bool opened: false
  property bool popoutSwitchClosing: false
  property alias controller: panelController

  function setting(name, fallback) {
    var value = settings ? settings[name] : undefined
    return value === undefined || value === null ? fallback : value
  }

  function closeForPopoutSwitch() {
    popoutSwitchClosing = true
    close()
    Qt.callLater(function() { popoutSwitchClosing = false })
  }

  QtObject {
    id: panelController
    function show() { root.opened = true }
    function hide() { root.opened = false }
  }
''')
    for forbidden in ("Process {", "ShellIpc", "Quickshell.Io", "omarchy-", "execDetached", "timedatectl", "sudo"):
        if forbidden in text:
            raise ValueError("Unsafe clock calendar surface: " + forbidden)
    return ("// Derived from the pinned Omarchy clock Panel.qml, MIT; see LICENSE.\n"
            "// Original calendar surface. No IPC, helper, or system timezone change.\n" + text).encode()


def derive_host(data):
    """Bar button that opens the derived calendar. Middle click stays unwired."""
    text = data.decode()
    text = replace(text, "import Quickshell.Io\n", "")
    text = replace(text, '''// Date/time label for the bar, and the host for the calendar popup.
//
// Left click reveals the calendar \u2014 asking "what is the date?" is what a
// click on a clock means \u2014 right click walks the common label formats, and
// middle click opens the timezone picker.
''', '''// Derived from Omarchy clock/BarWidget.qml, MIT; see LICENSE.
// Left click opens the calendar. Right click cycles the label. Middle click
// is excluded: the original timezone picker is a privileged system change.
''')
    text = replace(text, '''  ShellIpc {
    target: "omarchy.clock"

    function refresh(): void { root.broadcast("refresh") }
    function cycleFormat(): void { root.cycleFormat() }
    function toggleWeekStart(): void { root.toggleWeekStart() }
    function open(): void { root.open() }
    function close(): void { root.close() }
    function show(): void { root.open() }
    function hide(): void { root.close() }
    function toggle(): void { root.togglePanel() }
  }

''', "")
    text = replace(text, 'source: Qt.resolvedUrl("Panel.qml")', 'source: Qt.resolvedUrl("CalendarPanel.qml")')
    text = replace(text, '''    onPressed: function(b) {
      if (b === Qt.RightButton) root.cycleFormat()
      else if (b === Qt.MiddleButton) { if (root.bar) root.bar.run("omarchy-menu-timezone") }
      else root.togglePanel()
    }
''', '''    onPressed: function(b) {
      // Middle click is excluded: the original timezone picker changes the system clock.
      if (b === Qt.RightButton) root.cycleFormat()
      else if (b !== Qt.MiddleButton) root.togglePanel()
    }
''')
    for forbidden in ("ShellIpc", "Quickshell.Io", ".run(", "omarchy-menu", "timedatectl", "sudo", "Process {"):
        if forbidden in text:
            raise ValueError("Unsafe clock host: " + forbidden)
    if 'source: Qt.resolvedUrl("CalendarPanel.qml")' not in text or "function togglePanel()" not in text:
        raise ValueError("Clock host lost the calendar")
    return text.encode()
