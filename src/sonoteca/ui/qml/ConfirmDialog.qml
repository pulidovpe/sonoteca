import QtQuick
import QtQuick.Controls
import "."

Popup {
    id: root
    property string heading: ""
    property string message: ""
    property string confirmLabel: "Aceptar"
    property var action: null

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 460
    padding: 24
    background: Rectangle { color: "#1d1d1f"; radius: 12; border.color: "#2e2e32"; border.width: 1 }
    Overlay.modal: Rectangle { color: "#99000000" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function ask(newHeading, newMessage, newConfirmLabel, newAction) {
        heading = newHeading
        message = newMessage
        confirmLabel = newConfirmLabel
        action = newAction
        open()
    }
    function confirm() {
        close()
        if (action) action()
    }

    contentItem: Column {
        spacing: 14
        Text { text: root.heading; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold; width: parent.width; wrapMode: Text.WordWrap }
        Text { width: parent.width; text: root.message; color: Theme.textDim; font.pixelSize: 14; wrapMode: Text.WordWrap }
        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { label: "Cancelar"; onClicked: root.close() }
            PillButton { label: root.confirmLabel; primary: true; onClicked: root.confirm() }
        }
    }
}
