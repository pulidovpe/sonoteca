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
    function removeAt(i) { playlists.removeAt(playlistId, i) }

    property alias cover: heroCover   // para las pruebas
    property alias nameText: heroName
    property alias descriptionText: heroDescription
    property alias hero: heroBox

    Rectangle {
        id: heroBox
        height: 270
        anchors { left: parent.left; right: parent.right; top: parent.top }
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.heroTop }
            GradientStop { position: 1.0; color: Theme.bg }
        }
        // Misma portada y mismo tamaño que en un álbum; con varios álbumes es un collage
        PlaylistCover {
            id: heroCover
            x: 24; y: 40
            width: 190; height: 190
            fallback: Theme.coverColor(page.playlistId)
            albumIds: (playlists.revision, Theme.dataRevision, playlists.coverAlbums(page.playlistId))
        }
        Column {
            anchors.left: heroCover.right
            anchors.leftMargin: 24
            anchors.right: parent.right
            anchors.rightMargin: 24
            anchors.verticalCenter: heroCover.verticalCenter
            spacing: 8
            Text { text: "LISTA"; color: Theme.textDim; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1.5 }
            Text {
                id: heroName
                width: parent.width
                text: page.info.name || ""
                color: Theme.text
                font.pixelSize: 38
                font.weight: Font.Bold
                elide: Text.ElideRight
            }
            Text {
                id: heroDescription
                width: parent.width
                color: Theme.textDim
                font.pixelSize: 14
                elide: Text.ElideRight
                text: (page.info.description ? page.info.description + " \u00b7 " : "")
                      + Theme.plural(page.items.length, "canci\u00f3n", "canciones")
                      + (page.items.length > 0 ? ", " + Theme.fmtLong(page.info.duration || 0) : "")
            }
            Flow {
                width: parent.width
                spacing: 12
                PillButton { height: 44; label: "Reproducir"; primary: true; enabled: page.items.length > 0; onClicked: page.playAll() }
                PillButton { height: 44; label: "Agregar a la lista de reproducci\u00f3n"; enabled: page.items.length > 0; onClicked: player.addToQueue(page.ids) }
                PillButton { height: 44; label: "Renombrar"; onClicked: page.renameRequested(page.playlistId, page.info.name || "") }
                PillButton { height: 44; label: "Eliminar"; onClicked: page.deleteRequested(page.playlistId, page.info.name || "") }
            }
        }
    }
    Text {
        visible: page.items.length === 0
        width: parent.width - 48
        anchors { left: parent.left; top: heroBox.bottom; leftMargin: 24; topMargin: 24 }
        wrapMode: Text.WordWrap
        color: Theme.textDim
        font.pixelSize: 14
        text: "La lista est\u00e1 vac\u00eda. Agrega canciones con clic derecho \u25b8 Agregar a una lista\u2026, o guarda aqu\u00ed la lista actual."
    }
    ListView {
        id: list
        clip: true
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; top: heroBox.bottom; topMargin: 8 }
        model: page.items
        delegate: ListTrackRow {
            width: list.width
            position: modelData.position
            title: modelData.title
            subtitle: modelData.artist + " \u00b7 " + modelData.album
            duration: modelData.duration
            plays: (player.statsRevision, player.playsOf(modelData.id))
            trackId: modelData.id
            albumId: modelData.albumId
            count: page.items.length
            onReorderRequested: (dst) => playlists.moveTrack(page.playlistId, index, dst)
            current: player.currentId === modelData.id
            playing: player.playing
            onActivated: player.playTrackIds(page.ids, index)
            onMenuRequested: page.menuRequested([modelData.id])
            onEditRequested: page.editRequested([modelData.id])
            onRemoveRequested: page.removeAt(index)
        }
        ScrollBar.vertical: ScrollBar { }
    }
}
