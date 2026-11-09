import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Carpetas de la biblioteca: las que encontró «Buscar música». Quitar una la saca de la biblioteca (con sus subcarpetas) y la
// excluye de las búsquedas siguientes; los archivos del disco no se tocan. Las excluidas se pueden volver a incluir.
Popup {
    id: root
    property var folders: []
    property var excluded: []
    property var pending: null            // carpeta que espera confirmación: { path, name, total }
    property string message: ""
    property alias list: folderRepeater   // para las pruebas
    signal toastRequested(string text)

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(700, Overlay.overlay ? Overlay.overlay.width - 48 : 700)
    height: Math.min(620, Overlay.overlay ? Overlay.overlay.height - 48 : 620)
    padding: 24
    background: Rectangle { color: Theme.panel; radius: 12; border.color: Theme.border; border.width: 1 }
    Overlay.modal: Rectangle { color: Theme.scrim }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function openDialog() { pending = null; message = ""; refresh(); open() }
    function refresh() { folders = libraryFolders.folders(); excluded = libraryFolders.excluded() }
    function askRemove(path, name, total) { pending = { path: path, name: name, total: total } }
    function confirmRemove() {
        var target = pending
        pending = null
        var r = libraryFolders.removeFolder(target.path)
        refresh()
        if (r.ok) toastRequested(r.removed + " canciones quitadas de la biblioteca (los archivos siguen en el disco)")
        else message = r.error
    }
    function includeAgain(path) {
        if (libraryFolders.includeAgain(path)) {
            refresh()
            toastRequested("Vuelve a \u00abBuscar m\u00fasica\u00bb para traerla de nuevo a la biblioteca")
        }
    }

    contentItem: ColumnLayout {
        spacing: 12
        Text {
            Layout.fillWidth: true
            text: "Carpetas de la biblioteca"
            color: Theme.text
            font.pixelSize: 22
            font.weight: Font.Bold
        }
        Text {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.textDim
            font.pixelSize: 13
            text: "Son las carpetas donde \u00abBuscar m\u00fasica\u00bb encontr\u00f3 m\u00fasica. Al quitar una, sus canciones salen de la biblioteca y no vuelven en las b\u00fasquedas siguientes. Tus archivos no se borran ni se mueven."
        }

        // Confirmación (reemplaza a la lista mientras está pendiente)
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.pending !== null
            spacing: 14
            Item { Layout.fillHeight: true }
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.text
                font.pixelSize: 15
                text: root.pending
                      ? "\u00bfQuitar \u00ab" + root.pending.name + "\u00bb de la biblioteca?"
                      : ""
            }
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.textDim
                font.pixelSize: 13
                text: root.pending
                      ? "Se quitar\u00e1n " + root.pending.total + " canciones, con todas sus subcarpetas, y tambi\u00e9n saldr\u00e1n de las listas de reproducci\u00f3n donde est\u00e9n. Los archivos NO se borran: siguen en el disco. No volver\u00e1n a aparecer al buscar m\u00fasica, salvo que las vuelvas a incluir desde esta ventana."
                      : ""
            }
            Text { Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; color: Theme.textFaint; font.pixelSize: 11; text: root.pending ? root.pending.path : "" }
            Row {
                Layout.alignment: Qt.AlignRight
                spacing: 10
                PillButton { label: "Cancelar"; onClicked: root.pending = null }
                PillButton { label: "Quitar de la biblioteca"; primary: true; onClicked: root.confirmRemove() }
            }
            Item { Layout.fillHeight: true }
        }

        // Lista de carpetas
        Flickable {
            id: scroller
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.pending === null
            contentHeight: body.height
            clip: true
            ScrollBar.vertical: ScrollBar { }
            Column {
                id: body
                width: scroller.width - 12
                spacing: 4
                Repeater {
                    id: folderRepeater
                    model: root.folders
                    delegate: Rectangle {
                        width: body.width
                        height: 40
                        radius: 8
                        color: rowMouse.containsMouse ? Theme.surfaceHover : "transparent"
                        MouseArea { id: rowMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                        Text {
                            anchors { left: parent.left; leftMargin: 8 + modelData.depth * 18; right: countText.left; rightMargin: 10; verticalCenter: parent.verticalCenter }
                            text: modelData.name
                            color: Theme.text
                            font.pixelSize: 13
                            elide: Text.ElideMiddle
                        }
                        Text {
                            id: countText
                            anchors { right: removeButton.left; rightMargin: 12; verticalCenter: parent.verticalCenter }
                            text: modelData.total + (modelData.total === 1 ? " canci\u00f3n" : " canciones")
                            color: Theme.textDim
                            font.pixelSize: 12
                        }
                        PillButton {
                            id: removeButton
                            anchors { right: parent.right; rightMargin: 6; verticalCenter: parent.verticalCenter }
                            height: 30
                            radius: 15
                            enabled: !scanner.busy
                            label: "Quitar"
                            onClicked: root.askRemove(modelData.path, modelData.name, modelData.total)
                        }
                    }
                }
                Text {
                    visible: root.folders.length === 0
                    width: parent.width
                    wrapMode: Text.WordWrap
                    color: Theme.textDim
                    font.pixelSize: 13
                    text: "Todav\u00eda no hay carpetas con m\u00fasica. Usa \u00abBuscar m\u00fasica\u2026\u00bb en el men\u00fa Archivo."
                }
                Text {
                    visible: root.excluded.length > 0
                    topPadding: 14
                    width: parent.width
                    wrapMode: Text.WordWrap
                    color: Theme.textSoft
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    text: "Excluidas (no se incluyen al buscar m\u00fasica)"
                }
                Repeater {
                    id: excludedRepeater
                    model: root.excluded
                    delegate: Rectangle {
                        width: body.width
                        height: 40
                        radius: 8
                        color: exMouse.containsMouse ? Theme.surfaceHover : "transparent"
                        MouseArea { id: exMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                        Text {
                            anchors { left: parent.left; leftMargin: 8; right: includeButton.left; rightMargin: 10; verticalCenter: parent.verticalCenter }
                            text: (modelData.kind === "file" ? "Canci\u00f3n: " : "") + modelData.path
                            color: Theme.textDim
                            font.pixelSize: 12
                            elide: Text.ElideMiddle
                        }
                        PillButton {
                            id: includeButton
                            anchors { right: parent.right; rightMargin: 6; verticalCenter: parent.verticalCenter }
                            height: 30
                            radius: 15
                            label: "Volver a incluir"
                            onClicked: root.includeAgain(modelData.path)
                        }
                    }
                }
            }
        }
        Text { Layout.fillWidth: true; visible: root.message !== ""; text: root.message; color: Theme.danger; font.pixelSize: 13; wrapMode: Text.WordWrap }
        Row {
            Layout.alignment: Qt.AlignRight
            visible: root.pending === null
            PillButton { label: "Cerrar"; primary: true; onClicked: root.close() }
        }
    }
}
