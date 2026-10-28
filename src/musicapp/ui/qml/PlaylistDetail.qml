import QtQuick
import QtQuick.Controls
import "."

Item {
    id: page
    property int playlistId: 0
    property var info: (playlists.revision, Theme.dataRevision, playlists.info(playlistId))
    property var items: (playlists.revision, Theme.dataRevision, playlists.tracks(playlistId))
    property var ids: items.map(function (x) { return x.id })
    signal menuRequested(var ids)
    signal editRequested(var ids)
    signal renameRequested(int playlistId, string name)
    signal deleteRequested(int playlistId, string name)

    function playAll() { if (ids.length > 0) player.playTrackIds(ids, 0) }
    function moveUp(i) { if (i > 0) playlists.moveTrack(playlistId, i, i - 1) }
    function moveDown(i) { if (i < items.length - 1) playlists.moveTrack(playlistId, i, i + 1) }
    function removeAt(i) { playlists.removeAt(playlistId, i) }

    Text {
        id: title
        text: page.info.name || ""
        color: Theme.text
        font.pixelSize: 30
        font.weight: Font.Bold
        elide: Text.ElideRight
        anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: 24; rightMargin: 24; topMargin: 8 }
    }
    Text {
        id: sub
        text: Theme.plural(page.items.length, "canci\u00f3n", "canciones") + (page.items.length > 0 ? " \u00b7 " + Theme.fmtLong(page.info.duration || 0) : "")
        color: Theme.textDim
        font.pixelSize: 13
        anchors { left: parent.left; top: title.bottom; leftMargin: 24; topMargin: 2 }
    }
    Flow {
        id: buttons
        spacing: 10
        anchors { left: parent.left; right: parent.right; top: sub.bottom; leftMargin: 24; rightMargin: 24; topMargin: 12 }
        PillButton { label: "Reproducir"; primary: true; enabled: page.items.length > 0; onClicked: page.playAll() }
        PillButton { label: "Agregar a la lista de reproducci\u00f3n"; enabled: page.items.length > 0; onClicked: player.addToQueue(page.ids) }
        PillButton { label: "Renombrar"; onClicked: page.renameRequested(page.playlistId, page.info.name || "") }
        PillButton { label: "Eliminar"; onClicked: page.deleteRequested(page.playlistId, page.info.name || "") }
    }
    Text {
        visible: page.items.length === 0
        width: parent.width - 48
        anchors { left: parent.left; top: buttons.bottom; leftMargin: 24; topMargin: 24 }
        wrapMode: Text.WordWrap
        color: Theme.textDim
        font.pixelSize: 14
        text: "La lista est\u00e1 vac\u00eda. Agrega canciones con clic derecho \u25b8 Agregar a una lista\u2026, o guarda aqu\u00ed la lista actual."
    }
    ListView {
        id: list
        clip: true
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; top: buttons.bottom; topMargin: 12 }
        model: page.items
        delegate: ListTrackRow {
            width: list.width
            position: modelData.position
            title: modelData.title
            subtitle: modelData.artist + " \u00b7 " + modelData.album
            duration: modelData.duration
            plays: (player.statsRevision, player.playsOf(modelData.id))
            trackId: modelData.id
            count: page.items.length
            onReorderRequested: (dst) => playlists.moveTrack(page.playlistId, index, dst)
            current: player.currentId === modelData.id
            playing: player.playing
            onActivated: player.playTrackIds(page.ids, index)
            onMenuRequested: page.menuRequested([modelData.id])
            onEditRequested: page.editRequested([modelData.id])
            onMoveUp: page.moveUp(index)
            onMoveDown: page.moveDown(index)
            onRemoveRequested: page.removeAt(index)
        }
        ScrollBar.vertical: ScrollBar { }
    }
}
