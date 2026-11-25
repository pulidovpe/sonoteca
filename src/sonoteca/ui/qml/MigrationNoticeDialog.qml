import QtQuick
import QtQuick.Controls
import "."

// Aviso tras actualizar la base de datos: qué pasó y dónde quedó la copia de seguridad anterior
Popup {
    id: root
    property var info: ({})

    function showIfNeeded() {
        info = library.migrationNotice()
        if (info.migrated) open()
    }

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 520
    padding: 24
    background: Rectangle { color: Theme.panel; radius: 12; border.color: Theme.border; border.width: 1 }
    Overlay.modal: Rectangle { color: Theme.scrim }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    contentItem: Column {
        spacing: 14
        Text { text: "Tu biblioteca se actualiz\u00f3"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold; width: parent.width; wrapMode: Text.WordWrap }
        Text {
            width: parent.width
            text: "Sonoteca pas\u00f3 tu base de datos de la versi\u00f3n " + root.info.fromVersion + " a la " + root.info.toVersion + ". Se conservan tus canciones, listas y reproducciones."
            color: Theme.textDim
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
        Text {
            visible: root.info.backup !== ""
            width: parent.width
            text: "Antes de actualizar se guard\u00f3 una copia de seguridad:"
            color: Theme.textDim
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
        TextEdit {
            visible: root.info.backup !== ""
            width: parent.width
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.WrapAnywhere
            text: root.info.backup
            color: Theme.text
            font.pixelSize: 13
        }
        Text {
            width: parent.width
            text: "Las versiones anteriores de Sonoteca ya no podr\u00e1n abrir esta biblioteca. Conserva la copia si quieres volver atr\u00e1s."
            color: Theme.textFaint
            font.pixelSize: 13
            wrapMode: Text.WordWrap
        }
        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { visible: root.info.folderUrl !== ""; label: "Abrir carpeta de la copia"; onClicked: Qt.openUrlExternally(root.info.folderUrl) }
            PillButton { label: "Entendido"; primary: true; onClicked: root.close() }
        }
    }
}
