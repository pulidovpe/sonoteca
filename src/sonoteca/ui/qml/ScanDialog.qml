import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "."

// Buscar música en el disco: se elige dónde mirar y se indexa. Se abre sola si la biblioteca está
// vacía (primera vez) y siempre desde Archivo ▸ Buscar música…
Popup {
    id: root
    property var folders: []          // [{path, label, checked}]
    property bool done: false
    property string summary: ""
    property int seen: 0
    property string current: ""
    property string error: ""
    property bool firstRun: false
    signal finished(int added)
    property alias folderRepeater: folderRepeater

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 600
    padding: 24
    closePolicy: scanner.busy ? Popup.NoAutoClose : (Popup.CloseOnEscape | Popup.CloseOnPressOutside)
    background: Rectangle { color: "#1d1d1f"; radius: 12; border.color: "#2e2e32"; border.width: 1 }
    Overlay.modal: Rectangle { color: "#99000000" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function openDialog(isFirstRun) {
        firstRun = !!isFirstRun
        folders = scanner.suggestedFolders()
        done = false
        summary = ""
        error = ""
        seen = 0
        current = ""
        open()
    }
    function selectedPaths() {
        var out = []
        for (var i = 0; i < folders.length; i++) if (folders[i].checked) out.push(folders[i].path)
        return out
    }
    function setChecked(index, value) {
        var copy = folders.slice()
        copy[index] = { path: copy[index].path, label: copy[index].label, checked: value }
        folders = copy
    }
    function addFolder(path) {
        for (var i = 0; i < folders.length; i++) {
            if (folders[i].path === path) { setChecked(i, true); return }
        }
        folders = folders.concat([{ path: path, label: path, checked: true }])
    }
    function start() {
        error = ""
        var chosen = selectedPaths()
        if (chosen.length === 0) { error = "Marca al menos una carpeta."; return }
        scanner.scan(chosen)
    }

    Connections {
        target: scanner
        function onProgress(count, path) { root.seen = count; root.current = path }
        function onScanFinished(result) {
            root.done = true
            root.summary = result.added + " canciones nuevas, " + result.updated + " actualizadas"
                           + (result.removed > 0 ? ", " + result.removed + " quitadas" : "")
                           + (result.errors > 0 ? " (" + result.errors + " archivos con problemas)" : "") + "."
            root.finished(result.added)
        }
        function onScanError(message) { root.error = message }
    }
    FolderDialog {
        id: folderDialog
        title: "Elegir carpeta con m\u00fasica"
        onAccepted: root.addFolder(library.localPath(selectedFolder.toString()))
    }

    contentItem: Column {
        spacing: 14
        Text {
            width: parent.width
            text: root.firstRun ? "Bienvenido: busquemos tu m\u00fasica" : "Buscar m\u00fasica"
            color: Theme.text
            font.pixelSize: 22
            font.weight: Font.Bold
        }
        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Theme.textDim
            font.pixelSize: 13
            text: root.firstRun
                  ? "Tu biblioteca est\u00e1 vac\u00eda. Marca las carpetas donde tienes m\u00fasica o videos y la app las revisar\u00e1. No modifica ni mueve tus archivos."
                  : "Marca las carpetas que quieres revisar. Solo se leen los archivos nuevos o cambiados; lo que ya no exista se quita de la biblioteca."
        }
        Flickable {
            width: parent.width
            height: Math.min(folderColumn.height, 210)
            contentHeight: folderColumn.height
            clip: true
            visible: !root.done
            Column {
                id: folderColumn
                width: parent.width
                spacing: 4
                Repeater {
                    id: folderRepeater
                    model: root.folders
                    delegate: AppCheck {
                        width: folderColumn.width
                        enabled: !scanner.busy
                        checked: modelData.checked
                        text: modelData.label + (modelData.label !== modelData.path ? "  \u00b7  " + modelData.path : "")
                        onToggled: root.setChecked(index, checked)
                    }
                }
                Text {
                    visible: root.folders.length === 0
                    width: parent.width
                    wrapMode: Text.WordWrap
                    color: Theme.textDim
                    font.pixelSize: 13
                    text: "No encontr\u00e9 carpetas habituales. Usa \u00abA\u00f1adir otra carpeta\u2026\u00bb."
                }
            }
        }
        PillButton { visible: !root.done; enabled: !scanner.busy; label: "A\u00f1adir otra carpeta\u2026"; onClicked: folderDialog.open() }

        Column {
            width: parent.width
            spacing: 6
            visible: scanner.busy
            ProgressBar { width: parent.width; indeterminate: true }
            Text { width: parent.width; text: root.seen + " archivos revisados"; color: Theme.text; font.pixelSize: 13 }
            Text { width: parent.width; text: root.current; color: Theme.textDim; font.pixelSize: 11; elide: Text.ElideMiddle }
        }
        Text { width: parent.width; visible: root.done; text: "Listo: " + root.summary; color: Theme.accent; font.pixelSize: 14; wrapMode: Text.WordWrap }
        Text { width: parent.width; visible: root.error !== ""; text: root.error; color: "#ff6b6b"; font.pixelSize: 13; wrapMode: Text.WordWrap }

        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { visible: !root.done; enabled: !scanner.busy; label: root.firstRun ? "M\u00e1s tarde" : "Cancelar"; onClicked: root.close() }
            PillButton { visible: !root.done; primary: true; enabled: !scanner.busy; label: "Buscar m\u00fasica"; onClicked: root.start() }
            PillButton { visible: root.done; primary: true; label: "Listo"; onClicked: root.close() }
        }
    }
}
