import QtQuick
import QtQuick.Controls
import "."

// Ventana de error al arrancar: no se pudo abrir o actualizar la base de datos. El motivo en claro y dónde están los datos.
ApplicationWindow {
    id: win
    visible: true
    width: 640
    height: 460
    minimumWidth: 480
    minimumHeight: 360
    title: "Sonoteca"
    color: Theme.bg

    Column {
        anchors { fill: parent; margins: 32 }
        spacing: 16
        Text { width: parent.width; text: startupError.title; color: Theme.text; font.pixelSize: 24; font.weight: Font.Bold; wrapMode: Text.WordWrap }
        Text { width: parent.width; text: startupError.message; color: Theme.textSoft; font.pixelSize: 15; wrapMode: Text.WordWrap }
        Text { visible: startupError.backup !== ""; width: parent.width; text: "Copia de seguridad:"; color: Theme.textDim; font.pixelSize: 13 }
        TextEdit {
            visible: startupError.backup !== ""
            width: parent.width
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.WrapAnywhere
            text: startupError.backup
            color: Theme.text
            font.pixelSize: 13
        }
        Text { width: parent.width; text: "Detalles t\u00e9cnicos:"; color: Theme.textDim; font.pixelSize: 13 }
        TextEdit {
            id: details
            width: parent.width
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.WrapAnywhere
            text: startupError.details
            color: Theme.textFaint
            font.pixelSize: 12
        }
        Row {
            spacing: 10
            PillButton { label: "Abrir carpeta de datos"; onClicked: Qt.openUrlExternally(startupError.folderUrl) }
            PillButton { label: "Copiar detalles"; onClicked: { details.selectAll(); details.copy(); details.deselect() } }
            PillButton { label: "Salir"; primary: true; onClicked: Qt.quit() }
        }
    }
}
