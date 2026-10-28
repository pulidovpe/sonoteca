import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtCore
import "."

// Archivo \u25b8 Exportar / Importar biblioteca. Importar prepara el cambio y se aplica al volver a abrir la app.
Item {
    id: root
    signal toastRequested(string text, int ms)
    property alias importDialog: importPopup
    property alias resetDialog: resetPopup
    property alias exportFile: exportFile

    function exportLibrary() { exportFile.open() }
    function importLibrary() { importFile.open() }
    function resetLibrary() { resetPopup.begin() }

    FileDialog {
        id: exportFile
        title: "Exportar biblioteca"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "sonoteca"
        nameFilters: ["Biblioteca de Sonoteca (*.sonoteca)"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: {
            root.toastRequested("Exportando la biblioteca\u2026", 3000)
            portable.exportLibrary(library.localPath(selectedFile.toString()))
        }
        Component.onCompleted: currentFile = currentFolder + "/" + portable.defaultExportName()
    }
    FileDialog {
        id: importFile
        title: "Importar biblioteca"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Biblioteca de Sonoteca (*.sonoteca)"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: importPopup.begin(library.localPath(selectedFile.toString()))
    }
    FolderDialog {
        id: musicFolder
        title: "Carpeta donde est\u00e1 tu m\u00fasica en este equipo"
        onAccepted: importPopup.musicRoot = library.localPath(selectedFolder.toString())
    }
    Connections {
        target: portable
        function onExportFinished(result) {
            if (result.ok) root.toastRequested("Biblioteca exportada: " + result.manifest.tracks + " canciones, "
                                               + result.manifest.playlists + " listas", 6000)
            else root.toastRequested("No se pudo exportar: " + result.error, 8000)
        }
    }

    Popup {
        id: importPopup
        property string path: ""
        property var info: ({})
        property string musicRoot: ""
        property string stage: "confirm"     // confirm | restart
        property string error: ""
        property alias rootField: rootField
        property alias importButton: importButton

        modal: true
        focus: true
        closePolicy: stage === "restart" ? Popup.NoAutoClose : Popup.CloseOnEscape
        anchors.centerIn: Overlay.overlay
        width: Math.min(580, Overlay.overlay ? Overlay.overlay.width - 48 : 580)
        padding: 24
        background: Rectangle { color: Theme.panel; radius: 12; border.color: Theme.border; border.width: 1 }
        Overlay.modal: Rectangle { color: Theme.scrim }

        function begin(file) {
            var r = portable.inspectImport(file)
            if (!r.ok) { root.toastRequested("No se puede importar: " + r.error, 8000); return }
            path = file
            info = r
            musicRoot = r.manifest.music_root || ""
            error = ""
            stage = "confirm"
            open()
        }
        function doImport() {
            var r = portable.stageImport(path, musicRoot)
            if (!r.ok) { error = r.error; return }
            stage = "restart"
        }

        contentItem: Column {
            spacing: 14
            Text {
                width: parent.width; wrapMode: Text.WordWrap; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold
                text: importPopup.stage === "restart" ? "Importaci\u00f3n preparada" : "Importar biblioteca"
            }
            Column {
                width: parent.width
                spacing: 10
                visible: importPopup.stage === "confirm"
                Text {
                    width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 14
                    text: "El archivo tiene " + Theme.plural(importPopup.info.manifest ? importPopup.info.manifest.tracks : 0, "canci\u00f3n", "canciones")
                          + ", " + Theme.plural(importPopup.info.manifest ? importPopup.info.manifest.albums : 0, "\u00e1lbum", "\u00e1lbumes")
                          + ", " + Theme.plural(importPopup.info.manifest ? importPopup.info.manifest.artists : 0, "artista", "artistas")
                          + " y " + Theme.plural(importPopup.info.manifest ? importPopup.info.manifest.playlists : 0, "lista", "listas")
                          + (importPopup.info.manifest && importPopup.info.manifest.created ? " (exportado el " + importPopup.info.manifest.created.substring(0, 10) + ")" : "") + "."
                }
                Rectangle {
                    width: parent.width; height: warn.implicitHeight + 20; radius: 8; color: Theme.warnBg; border.color: Theme.warnBorder
                    Text {
                        id: warn
                        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 12 }
                        wrapMode: Text.WordWrap; color: Theme.warn; font.pixelSize: 13
                        text: "Esto REEMPLAZA tu biblioteca actual (" + Theme.plural(importPopup.info.currentTracks || 0, "canci\u00f3n", "canciones")
                              + ", listas, letras y portadas descargadas). Antes se guarda una copia en la carpeta de datos, dentro de \u00abbackups\u00bb. No se tocan tus archivos de m\u00fasica."
                    }
                }
                Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 13
                       text: "Carpeta de la m\u00fasica en este equipo. D\u00e9jala igual si la m\u00fasica est\u00e1 en la misma ruta; c\u00e1mbiala si importas en otro equipo o la moviste." }
                Row {
                    width: parent.width
                    spacing: 8
                    Rectangle {
                        width: parent.width - chooseButton.width - 8; height: 36; radius: 8; color: Theme.field
                        border.color: rootField.activeFocus ? Theme.accent : Theme.border
                        TextField {
                            id: rootField
                            anchors.fill: parent
                            leftPadding: 10
                            color: Theme.text
                            font.pixelSize: 13
                            selectByMouse: true
                            background: null
                            text: importPopup.musicRoot
                            onTextEdited: importPopup.musicRoot = text
                        }
                    }
                    PillButton { id: chooseButton; height: 36; label: "Elegir\u2026"; onClicked: musicFolder.open() }
                }
                Text { visible: importPopup.error !== ""; width: parent.width; wrapMode: Text.WordWrap; color: Theme.danger; font.pixelSize: 13; text: importPopup.error }
            }
            Text {
                visible: importPopup.stage === "restart"
                width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 14
                text: "Cierra Sonoteca y vuelve a abrirla para terminar la importaci\u00f3n. Nada cambia hasta entonces."
            }
            Row {
                anchors.right: parent.right
                spacing: 10
                PillButton { visible: importPopup.stage === "confirm"; label: "Cancelar"; onClicked: importPopup.close() }
                PillButton { id: importButton; visible: importPopup.stage === "confirm"; label: "Importar"; primary: true; onClicked: importPopup.doImport() }
                PillButton { visible: importPopup.stage === "restart"; label: "Cerrar Sonoteca"; primary: true; onClicked: Qt.quit() }
            }
        }
    }

    // Empezar desde cero: vac\u00eda la biblioteca al volver a abrir la app (con copia de seguridad opcional)
    Popup {
        id: resetPopup
        property string stage: "confirm"     // confirm | restart
        property string error: ""
        property alias keepBackup: keepBackup
        property alias resetButton: resetButton

        modal: true
        focus: true
        closePolicy: stage === "restart" ? Popup.NoAutoClose : Popup.CloseOnEscape
        anchors.centerIn: Overlay.overlay
        width: Math.min(560, Overlay.overlay ? Overlay.overlay.width - 48 : 560)
        padding: 24
        background: Rectangle { color: Theme.panel; radius: 12; border.color: Theme.border; border.width: 1 }
        Overlay.modal: Rectangle { color: Theme.scrim }

        function begin() { stage = "confirm"; error = ""; keepBackup.checked = true; open() }
        function doReset() {
            var r = portable.stageReset(keepBackup.checked)
            if (!r.ok) { error = r.error; return }
            stage = "restart"
        }

        contentItem: Column {
            spacing: 14
            Text {
                width: parent.width; wrapMode: Text.WordWrap; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold
                text: resetPopup.stage === "restart" ? "Todo listo para empezar de cero" : "Empezar desde cero"
            }
            Column {
                width: parent.width
                spacing: 10
                visible: resetPopup.stage === "confirm"
                Text {
                    width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 14
                    text: "Se vaciar\u00e1 la biblioteca: canciones indexadas, listas, letras, contadores, y las portadas y fotos descargadas. "
                          + "No se borra ni se modifica ning\u00fan archivo de m\u00fasica, y se conservan tus ajustes (internet, servidores y claves). "
                          + "Al volver a abrir Sonoteca empezar\u00e1 con una biblioteca vac\u00eda lista para buscar m\u00fasica."
                }
                CheckBox {
                    id: keepBackup
                    checked: true
                    text: "Guardar antes una copia de seguridad (carpeta \u00abbackups\u00bb de los datos)"
                    contentItem: Text { text: keepBackup.text; color: Theme.text; font.pixelSize: 13; leftPadding: keepBackup.indicator.width + 8; wrapMode: Text.WordWrap; verticalAlignment: Text.AlignVCenter }
                }
                Text {
                    visible: !keepBackup.checked
                    width: parent.width; wrapMode: Text.WordWrap; color: Theme.danger; font.pixelSize: 13
                    text: "Sin copia de seguridad no se podr\u00e1 recuperar la biblioteca (salvo que antes la hayas exportado)."
                }
                Text { visible: resetPopup.error !== ""; width: parent.width; wrapMode: Text.WordWrap; color: Theme.danger; font.pixelSize: 13; text: resetPopup.error }
            }
            Text {
                visible: resetPopup.stage === "restart"
                width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 14
                text: "Cierra Sonoteca y vuelve a abrirla para terminar. Hasta entonces no cambia nada."
            }
            Row {
                anchors.right: parent.right
                spacing: 10
                PillButton { visible: resetPopup.stage === "confirm"; label: "Cancelar"; onClicked: resetPopup.close() }
                PillButton { id: resetButton; visible: resetPopup.stage === "confirm"; label: "Vaciar y empezar de cero"; primary: true; onClicked: resetPopup.doReset() }
                PillButton { visible: resetPopup.stage === "restart"; label: "Cerrar Sonoteca"; primary: true; onClicked: Qt.quit() }
            }
        }
    }
}
