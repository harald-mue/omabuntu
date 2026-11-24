import QtQuick
import qs.Commons
import qs.Ui

// Capability rows inside the original audio panel, not a replacement panel.
Column {
  id: root
  required property var bridge
  property var controller: null
  property color foreground: Color.foreground
  property string fontFamily: Style.font.family
  readonly property bool available: !!controller && controller.advancedAudioAvailable === true
  readonly property bool expanded: available && controller.advancedAudio
  readonly property var entries: buildEntries()
  readonly property var actions: entries.filter(function(row) { return row.kind === "action" })
  visible: available && bridge !== null
  enabled: available
  spacing: Style.space(6)

  function buildEntries() {
    if (!available || !bridge) return []
    var rows = [], cursor = 0
    function header(text) { rows.push(Object.freeze({kind:"header", text:text, index:-1})) }
    function action(id, op, text, enabled, fields, selected) {
      rows.push(Object.freeze({kind:"action", id:bridge.scope+":"+id, op:op, text:text,
        enabled:!!enabled, fields:Object.freeze(fields || {}), selected:!!selected, index:cursor++}))
    }
    action(expanded ? "page-back" : "page-open", expanded ? "back" : "open",
      expanded ? "Back to audio" : "Advanced audio", true)
    if (!expanded) return Object.freeze(rows)
    action("query", "query", bridge.granted ? "Refresh audio devices / reconnect events"
      : "Allow local audio queries (connection risk)", !bridge.inFlight)
    if (bridge.granted) action("revoke", "revoke", "Stop optional audio queries", true)
    if (bridge.known) {
      bridge.snapshot.cards.forEach(function(card) {
        header(card.name)
        Object.keys(card.profiles).filter(function(name) {
          var p = card.profiles[name]
          return name !== "off" && p.available && p.sinks + p.sources > 0
        }).sort(function(a,b) { return card.profiles[b].priority - card.profiles[a].priority })
        .forEach(function(name) {
          action("review:"+card.serial+":"+name, "review", card.profiles[name].description || name,
            bridge.writable, {card:card.name, profile:name}, card.active_profile === name)
        })
      })
    }
    if (bridge.pendingReview) {
      header("Review: " + bridge.pendingReview.profile + " — " + bridge.pendingReview.notice)
      action("apply:"+bridge.reviewKey, "apply", "Apply reviewed profile (may interrupt calls)", bridge.writable)
    }
    bridge.recovery.profile_history.filter(function(r) {
      return ["prepared", "applied", "restore-prepared"].indexOf(r.status) >= 0
    }).slice(-1).forEach(function(r) {
      header("Profile recovery: " + r.status + ". Restore changes only the prior profile name, not topology, defaults or streams.")
      action("restore:"+r.id, "restore", "Restore previous profile (may interrupt calls)", bridge.known && !bridge.busy, {id:r.id})
      if (r.status !== "applied")
        action("ack-profile:"+r.id, "ack-profile", "Acknowledge unresolved profile; do NOT restore", !bridge.busy, {id:r.id})
    })
    bridge.recovery.control_history.filter(function(r) { return r.status === "prepared" }).slice(-1).forEach(function(r) {
      action("ack-control:"+r.id, "ack-control", "Acknowledge uncertain gain/mute; do NOT restore", !bridge.busy, {id:r.id})
    })
    return Object.freeze(rows)
  }
  function invoke(row) {
    // A stale delegate/cursor cannot silently select a different capability.
    if (!available || !row || !row.enabled || !entries.some(function(current) {
      return current.id === row.id && JSON.stringify(current) === JSON.stringify(row)
    })) return false
    switch (row.op) {
      case "open": if (!controller) return false; controller.advancedAudio = true; return true
      case "back": if (!controller) return false; controller.advancedAudio = false; return true
      case "query": return bridge.grantQueries()
      case "revoke": bridge.revoke(); return true
      case "review": return bridge.reviewProfile(row.fields.card, row.fields.profile)
      case "apply": return bridge.applyProfile()
      case "restore": return bridge.restoreProfile(row.fields.id)
      case "ack-profile": return bridge.acknowledgeProfile(row.fields.id)
      case "ack-control": return bridge.acknowledgeControl(row.fields.id)
    }
    return false
  }
  function activate(index) {
    return Number.isInteger(index) && index >= 0 && index < actions.length ? invoke(actions[index]) : false
  }
  Component.onCompleted: if (controller) controller.profileControls = root
  Component.onDestruction: if (controller && controller.profileControls === root) controller.profileControls = null
  onActionsChanged: {
    // Membership/approval changes revoke the old positional cursor. A new
    // movement/hover must admit the current row rather than retargeting Enter.
    if (controller && controller.focusSection === "profiles") {
      controller.cursorActive = false
      controller.selectedIndex = 0
    }
  }

  Button {
    objectName:"audioAdvancedNavigation"
    width:parent.width
    focusable:true
    iconText:root.expanded ? "󰁍" : "󰒓"
    tooltipText:root.expanded ? "Return to audio controls" : "Device profiles, virtual inputs and recovery"
    foreground:root.foreground
    fontFamily:root.fontFamily
    leftAlign:true
    text:root.expanded ? "Back to audio" : "Advanced audio"
    enabled:root.actions.length > 0
    hasCursor:!!root.controller && root.controller.cursorActive
      && root.controller.focusSection === "profiles" && root.controller.selectedIndex === 0
    onHovered:function(on) {
      if (on && root.controller) {
        root.controller.focusSection = "profiles"; root.controller.selectedIndex = 0; root.controller.cursorActive = true
      }
    }
    onHasCursorChanged: if (hasCursor) root.controller.ensureCursorVisible(this)
    onClicked:root.activate(0)
  }
  PanelSeparator { visible:root.expanded; width:parent.width; foreground:root.foreground }
  PanelSectionHeader {
    visible:root.expanded
    text:"DEVICE PROFILES AND VIRTUAL INPUTS"
    foreground:root.foreground
    fontFamily:root.fontFamily
  }
  Text {
    width:parent.width
    wrapMode:Text.Wrap
    textFormat:Text.PlainText
    color:root.foreground
    font.family:root.fontFamily
    font.pixelSize:Style.font.bodySmall
    visible:root.expanded
    text:"Optional local pactl access. Connecting can socket-activate a stopping audio transport. Profile changes affect this user's other desktops and can interrupt calls. No automatic service start, retry or profile change."
  }
  Text {
    width:parent.width
    wrapMode:Text.Wrap
    textFormat:Text.PlainText
    color:root.foreground
    font.family:root.fontFamily
    font.pixelSize:Style.font.bodySmall
    visible:root.expanded && !!root.bridge && (root.bridge.busy || root.bridge.errorText !== "" || (root.bridge.known && !root.bridge.writable))
    text:!root.bridge ? "" : root.bridge.errorText || (root.bridge.busy
      ? "Audio request in progress; outcome not yet accepted."
      : "Audio writes are blocked; inspect the retained recovery entries below.")
  }
  Repeater {
    model:root.entries.slice(1)
    Column {
      id: entryRow
      required property var modelData
      width:root.width
      PanelSectionHeader {
        visible:entryRow.modelData.kind === "header"
        width:parent.width
        text:visible ? entryRow.modelData.text : ""
        foreground:root.foreground
        fontFamily:root.fontFamily
        wrapMode:Text.Wrap
      }
      Button {
        id: actionButton
        visible:entryRow.modelData.kind === "action"
        width:parent.width
        focusable:true
        leftAlign:true
        foreground:root.foreground
        fontFamily:root.fontFamily
        text:visible ? entryRow.modelData.text : ""
        enabled:visible && entryRow.modelData.enabled === true
        selected:entryRow.modelData.selected === true
        hasCursor:!!root.controller && root.controller.cursorActive
          && root.controller.focusSection === "profiles" && root.controller.selectedIndex === entryRow.modelData.index
        onHovered:function(on) {
          if (on && root.controller) {
            root.controller.focusSection = "profiles"
            root.controller.selectedIndex = entryRow.modelData.index
            root.controller.cursorActive = true
          }
        }
        onHasCursorChanged: if (hasCursor) root.controller.ensureCursorVisible(actionButton)
        onClicked:root.invoke(entryRow.modelData)
      }
    }
  }
}
