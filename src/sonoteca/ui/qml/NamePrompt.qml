import QtQuick
import QtQuick.Controls
import "."

// Pide un nombre. `handler(nombre)` devuelve "" si todo salió bien o el mensaje de error a mostrar.
Popup {
    id: root
    property string heading: ""
    property string confirmLabel: "Guardar"
    property string error: ""
    property var handler: null
    property alias fieldItem: field

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 460
    padding: 24
    background: Rectangle { color: Theme.panel; radius: 12; border.color: Theme.border; border.width: 1 }
    Overlay.modal: Rectangle { color: Theme.scrim }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function ask(newHeading, initial, newConfirmLabel, newHandler) {
        heading = newHeading
        confirmLabel = newConfirmLabel
        handler = newHandler
        error = ""
        field.reset(initial, false)
        open()
        field.forceFocus()
    }
    function submit() {
        var message = handler ? handler(field.text) : ""
        if (message) { error = message; return }
        close()
    }

    contentItem: Column {
        spacing: 14
        Text { text: root.heading; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold; width: parent.width; wrapMode: Text.WordWrap }
        EditorField { id: field; width: parent.width; key: "name"; label: "Nombre"; onAccepted: root.submit() }
        Text { width: parent.width; visible: root.error !== ""; text: root.error; color: Theme.danger; font.pixelSize: 13; wrapMode: Text.WordWrap }
        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { label: "Cancelar"; onClicked: root.close() }
            PillButton { label: root.confirmLabel; primary: true; onClicked: root.submit() }
        }
    }
}
