import QtQuick
import QtQuick.Controls
import "."

// Aviso al agregar a una lista canciones que ya están en ella
Popup {
    id: root
    property int listId: 0
    property string listName: ""
    property var ids: []
    property int dupCount: 0
    readonly property int total: ids.length
    readonly property bool all: dupCount >= total

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 480
    padding: 24
    background: Rectangle { color: Theme.panel; radius: 12; border.color: Theme.border; border.width: 1 }
    Overlay.modal: Rectangle { color: Theme.scrim }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function openFor(playlistId, newIds, count) {
        listId = playlistId
        ids = newIds
        dupCount = count
        var info = playlists.info(playlistId)
        listName = info && info.name ? info.name : ""
        open()
    }
    signal failed(string text)
    function report(r) { if (!r.ok) failed(r.error) }
    function addAnyway() { close(); report(playlists.addTracks(listId, ids)) }
    function addNewOnly() { close(); report(playlists.addNewTracks(listId, ids)) }

    contentItem: Column {
        spacing: 14
        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Theme.text
            font.pixelSize: 20
            font.weight: Font.Bold
            text: root.total === 1 ? "Esa canci\u00f3n ya est\u00e1 en la lista"
                  : root.all ? "Esas canciones ya est\u00e1n en la lista"
                  : root.dupCount + " de " + root.total + " canciones ya est\u00e1n en la lista"
        }
        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Theme.textDim
            font.pixelSize: 14
            text: root.total === 1 ? "\u00ab" + root.listName + "\u00bb ya incluye esta canci\u00f3n. \u00bfQuieres agregarla de nuevo?"
                  : root.all ? "\u00ab" + root.listName + "\u00bb ya incluye todas. \u00bfQuieres agregarlas de nuevo?"
                  : "Puedes agregar solo las que a\u00fan no est\u00e1n en \u00ab" + root.listName + "\u00bb o todas, repitiendo las que ya tiene."
        }
        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { label: "Cancelar"; onClicked: root.close() }
            PillButton { visible: !root.all; label: "Agregar solo las nuevas"; primary: true; onClicked: root.addNewOnly() }
            PillButton { label: root.all ? "Agregar de nuevo" : "Agregar todas"; primary: root.all; onClicked: root.addAnyway() }
        }
    }
}
