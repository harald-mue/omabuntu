import QtQuick
import qs.Ui as Ui
import qs.Commons

// Original toolkit controls inside the original panel; no separate agent window.
Column {
  id: root
  required property var session
  required property var owner
  property color foreground: Color.foreground
  property string fontFamily: Style.font.family
  readonly property var prompt: session ? session.prompt : null
  readonly property bool needsInput: !!prompt && (prompt.kind === "RequestPinCode" || prompt.kind === "RequestPasskey")
  readonly property string promptKey: prompt ? prompt.id : ""
  visible: !!session && (!!session.pending || session.uncertain)
  spacing: Style.space(8)
  onPromptKeyChanged: {
    codeInput.clear()
    if(needsInput)Qt.callLater(function(){codeInput.forceActiveFocus()})
    else if(prompt&&!prompt.displayOnly)Qt.callLater(function(){rejectButton.forceActiveFocus()})
  }
  Component.onDestruction: codeInput.clear()
  function submit(accept) {
    if (!prompt) return
    var id=prompt.id,value=codeInput.text
    codeInput.clear()
    session.answer(id,accept,value)
    value=""
  }
  Ui.PanelSeparator { width:parent.width;foreground:root.foreground }
  Ui.PanelSectionHeader { text:"BLUETOOTH PAIRING";foreground:root.foreground;fontFamily:root.fontFamily }
  Text {
    width:parent.width;textFormat:Text.PlainText;wrapMode:Text.Wrap
    font.family:root.fontFamily;font.pixelSize:Style.font.body;color:root.foreground
    text:!root.session ? "" : root.session.uncertain ? "Outcome uncertain. Check the device before explicitly acknowledging; no automatic retry or restoration."
      : (root.session.pending ? root.session.pending.label+" · "+root.session.pending.address : "")
  }
  Text {
    width:parent.width;textFormat:Text.PlainText;wrapMode:Text.Wrap
    font.family:root.fontFamily;font.pixelSize:Style.font.bodySmall;color:root.foreground
    text:!root.prompt?"Waiting for the device…":root.prompt.kind==="RequestPinCode"?"Enter the device PIN (1–16 letters or digits)."
      :root.prompt.kind==="RequestPasskey"?"Enter the numeric device passkey (up to six digits)."
      :root.prompt.kind==="RequestConfirmation"?"Confirm that this code matches the device: "+root.prompt.code
      :root.prompt.kind==="DisplayPinCode"?"Type this code on the device: "+root.prompt.code
      :root.prompt.kind==="DisplayPasskey"?"Type this code on the device: "+root.prompt.code+" · "+root.prompt.entered+"/6 entered"
      :root.prompt.kind==="AuthorizeService"?"Allow this device service for this request only? "+root.prompt.uuid
      :"Allow pairing with this locally selected device?"
    visible:!root.session||!root.session.uncertain
  }
  Ui.TextField {
    id:codeInput
    width:parent.width;visible:root.needsInput;enabled:visible
    foreground:root.foreground;password:true;maximumLength:root.prompt&&root.prompt.kind==="RequestPasskey"?6:16
    inputMethodHints:Qt.ImhNoPredictiveText|Qt.ImhSensitiveData
    onAccepted:if(root.needsInput)root.submit(true)
    Keys.onEscapePressed:event=>{root.submit(false);event.accepted=true}
  }
  Row {
    spacing:Style.space(8)
    Ui.Button {
      focusable:true
      visible:!!root.prompt&&!root.prompt.displayOnly
      text:root.needsInput?"Submit":"Confirm"
      foreground:root.foreground;fontFamily:root.fontFamily
      iconText:"󰄬";onClicked:root.submit(true)
    }
    Ui.Button {
      id:rejectButton
      focusable:true
      visible:!!root.prompt&&!root.prompt.displayOnly
      text:"Reject";foreground:root.foreground;fontFamily:root.fontFamily
      iconText:"󰅖";onClicked:root.submit(false)
    }
    Ui.Button {
      focusable:true
      visible:!!root.session&&!!root.session.pending
      text:"Cancel request";foreground:root.foreground;fontFamily:root.fontFamily
      iconText:"󰅖";onClicked:{codeInput.clear();root.session.cancel()}
    }
    Ui.Button {
      focusable:true
      visible:!!root.session&&root.session.uncertain&&!root.session.pending
      text:"Acknowledge uncertainty";foreground:root.foreground;fontFamily:root.fontFamily
      onClicked:root.session.acknowledge()
    }
  }
}
