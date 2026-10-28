import QtQuick
import QtQuick.Controls
import "."

Item {
    id: page
    property string query: ""
    property var results: (Theme.dataRevision, library.searchAll(query))
    property var ids: results.tracks.map(function (x) { return x.id })
    readonly property bool empty: results.artists.length + results.albums.length + results.tracks.length === 0
    signal albumClicked(int albumId)
    signal artistClicked(int artistId, string name)
    signal editRequested(var ids)
    signal menuRequested(var ids)

    Flickable {
        id: flick
        anchors.fill: parent
        contentWidth: width
        contentHeight: col.height + 32
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { }

        Column {
            id: col
            width: flick.width
            spacing: 6

            Text {
                x: 24
                width: parent.width - 48
                text: "Resultados para \u201c" + page.query + "\u201d"
                color: Theme.text
                font.pixelSize: 30
                font.weight: Font.Bold
                elide: Text.ElideRight
            }
            Text {
                x: 24
                visible: page.empty
                text: page.query.trim().length < 2 ? "Escribe al menos 2 letras." : "Sin resultados. Prueba con otras palabras (no importan acentos ni mayúsculas)."
                color: Theme.textDim
                font.pixelSize: 14
            }

            Text { x: 24; visible: page.results.artists.length > 0; topPadding: 14; text: "Artistas"; color: Theme.text; font.pixelSize: 20; font.weight: Font.DemiBold }
            ListView {
                visible: page.results.artists.length > 0
                width: parent.width
                height: visible ? 266 : 0
                orientation: ListView.Horizontal
                leftMargin: 16
                clip: true
                model: page.results.artists
                delegate: AlbumCard {
                    width: 190
                    height: 266
                    coverSource: "image://cover/artist/" + modelData.id + "?v=" + Theme.dataRevision
                    title: modelData.name
                    subtitle: modelData.subtitle
                    onClicked: page.artistClicked(modelData.id, modelData.name)
                }
            }

            Text { x: 24; visible: page.results.albums.length > 0; topPadding: 14; text: "Álbumes"; color: Theme.text; font.pixelSize: 20; font.weight: Font.DemiBold }
            ListView {
                visible: page.results.albums.length > 0
                width: parent.width
                height: visible ? 266 : 0
                orientation: ListView.Horizontal
                leftMargin: 16
                clip: true
                model: page.results.albums
                delegate: AlbumCard {
                    width: 190
                    height: 266
                    albumId: modelData.id
                    title: modelData.title
                    subtitle: modelData.subtitle
                    onClicked: page.albumClicked(modelData.id)
                }
            }

            Text { x: 24; visible: page.results.tracks.length > 0; topPadding: 14; text: "Canciones"; color: Theme.text; font.pixelSize: 20; font.weight: Font.DemiBold }
            Repeater {
                model: page.results.tracks
                delegate: TrackRow {
                    width: col.width
                    title: modelData.title
                    subtitle: modelData.subtitle
                    badge: modelData.badge
                    duration: modelData.duration > 0 ? Theme.fmt(modelData.duration) : ""
                    current: player.currentId === modelData.id
                    trackId: modelData.id
                    onActivated: player.playTrackIds(page.ids, index)
                    onContextRequested: page.menuRequested([modelData.id])
                }
            }
        }
    }
}
