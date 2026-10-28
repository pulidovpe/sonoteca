import QtQuick
import QtQuick.Controls
import "."

// Elegir a qué lista guardada agregar canciones
Popup {
    id: root
    property var ids: []
    property var lists: []
    property string error: ""
    signal newRequested(var ids)

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 460
    padding: 24
    background: Rectangle { color: "#1d1d1f"; radius: 12; border.color: "#2e2e32"; border.width: 1 }
    Overlay.modal: Rectangle { color: "#99000000" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function openFor(newIds) {
        ids = newIds
        error = ""
        lists = playlists.lists()
        open()
    }
    function add(playlistId) {
        var result = playlists.addTracks(playlistId, ids)
        if (!result.ok) { error = result.error; return }
        close()
    }
    function createNew() {
        close()
        newRequested(ids)
    }
    Connections {
        target: playlists
        function onChanged() { if (root.visible) root.lists = playlists.lists() }
    }

    contentItem: Column {
        spacing: 14
        Column {
            width: parent.width
            spacing: 2
            Text { text: "Agregar a una lista"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold }
            Text { text: Theme.plural(root.ids.length, "canci\u00f3n", "canciones"); color: Theme.textDim; font.pixelSize: 13 }
        }
        Text {
            width: parent.width
            visible: root.lists.length === 0
            wrapMode: Text.WordWrap
            color: Theme.textDim
            font.pixelSize: 13
            text: "Todav\u00eda no tienes listas. Crea la primera."
        }
        ListView {
            id: pickList
            width: parent.width
            height: Math.min(contentHeight, 260)
            visible: root.lists.length > 0
            clip: true
            spacing: 4
            model: root.lists
            delegate: Rectangle {
                width: pickList.width
                height: 48
                radius: 8
                color: rowMouse.containsMouse ? Theme.surfaceHover : "#232325"
                Behavior on color { ColorAnimation { duration: Theme.fast } }
                Column {
                    anchors { left: parent.left; leftMargin: 14; right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
                    Text { width: parent.width; text: modelData.name; color: Theme.text; font.pixelSize: 14; elide: Text.ElideRight }
                    Text { text: Theme.plural(modelData.tracks, "canci\u00f3n", "canciones"); color: Theme.textDim; font.pixelSize: 11 }
                }
                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.add(modelData.id)
                }
            }
            ScrollBar.vertical: ScrollBar { }
        }
        Text { width: parent.width; visible: root.error !== ""; text: root.error; color: "#ff6b6b"; font.pixelSize: 13; wrapMode: Text.WordWrap }
        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { label: "Cancelar"; onClicked: root.close() }
            PillButton { label: "Nueva lista\u2026"; primary: true; onClicked: root.createNew() }
        }
    }
}
