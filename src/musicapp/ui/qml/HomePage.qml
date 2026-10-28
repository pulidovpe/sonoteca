import QtQuick
import QtQuick.Controls
import "."

// Inicio: tus listas y lo más escuchado (álbumes, artistas y canciones)
Item {
    id: page
    property var homeData: (Theme.dataRevision, player.statsRevision, playlists.revision, library.home())
    readonly property bool empty: homeData.albums.length === 0 && homeData.artists.length === 0
                                  && homeData.tracks.length === 0 && homeData.lists.length === 0
    readonly property var trackIds: homeData.tracks.map(function (x) { return x.id })
    signal albumClicked(int albumId)
    signal artistClicked(int artistId, string name)
    signal playlistClicked(int playlistId)
    signal menuRequested(var ids)
    property alias scrollItem: flick

    Text {
        id: title
        text: "Inicio"
        color: Theme.text
        font.pixelSize: 30
        font.weight: Font.Bold
        anchors { left: parent.left; top: parent.top; leftMargin: 24; topMargin: 8 }
    }
    Flickable {
        id: flick
        clip: true
        anchors { left: parent.left; right: parent.right; top: title.bottom; bottom: parent.bottom; topMargin: 12 }
        contentWidth: width
        contentHeight: col.height + 24
        ScrollBar.vertical: ScrollBar { }

        Column {
            id: col
            width: flick.width
            spacing: 6

            Text {
                visible: page.empty
                x: 24
                width: parent.width - 48
                wrapMode: Text.WordWrap
                color: Theme.textDim
                font.pixelSize: 14
                text: "Todav\u00eda no hay nada que mostrar. Escucha canciones y aqu\u00ed aparecer\u00e1n tus \u00e1lbumes, artistas y canciones m\u00e1s escuchados; tus listas tambi\u00e9n aparecer\u00e1n en este espacio."
            }

            // ---- Listas ----
            Text { visible: page.homeData.lists.length > 0; x: 24; text: "Tus listas"; color: Theme.text; font.pixelSize: 18; font.weight: Font.Bold }
            ListView {
                id: listsRail
                visible: page.homeData.lists.length > 0
                width: parent.width
                height: visible ? 92 : 0
                orientation: ListView.Horizontal
                spacing: 12
                leftMargin: 24
                rightMargin: 24
                clip: true
                model: page.homeData.lists
                delegate: Rectangle {
                    width: 200
                    height: 80
                    radius: Theme.radius
                    color: listMouse.containsMouse ? Theme.surfaceHover : Theme.surface
                    Behavior on color { ColorAnimation { duration: Theme.fast } }
                    Column {
                        anchors { fill: parent; margins: 14 }
                        spacing: 4
                        Text { width: parent.width; text: modelData.name; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        Text {
                            width: parent.width
                            color: Theme.textDim
                            font.pixelSize: 12
                            elide: Text.ElideRight
                            text: Theme.plural(modelData.tracks, "canci\u00f3n", "canciones") + (modelData.plays > 0 ? " \u00b7 \u25b6 " + modelData.plays : "")
                        }
                    }
                    MouseArea { id: listMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.playlistClicked(modelData.id) }
                }
            }

            // ---- \u00c1lbumes m\u00e1s escuchados ----
            Text { visible: page.homeData.albums.length > 0; x: 24; text: "\u00c1lbumes m\u00e1s escuchados"; color: Theme.text; font.pixelSize: 18; font.weight: Font.Bold }
            ListView {
                id: albumsRail
                visible: page.homeData.albums.length > 0
                width: parent.width
                height: visible ? 250 : 0
                orientation: ListView.Horizontal
                leftMargin: 16
                rightMargin: 16
                clip: true
                model: page.homeData.albums
                delegate: AlbumCard {
                    width: 186
                    height: 246
                    albumId: modelData.id
                    title: modelData.displayTitle
                    subtitle: modelData.artist + " \u00b7 \u25b6 " + modelData.plays
                    onClicked: page.albumClicked(modelData.id)
                }
            }

            // ---- Artistas m\u00e1s escuchados ----
            Text { visible: page.homeData.artists.length > 0; x: 24; text: "Artistas m\u00e1s escuchados"; color: Theme.text; font.pixelSize: 18; font.weight: Font.Bold }
            ListView {
                id: artistsRail
                visible: page.homeData.artists.length > 0
                width: parent.width
                height: visible ? 250 : 0
                orientation: ListView.Horizontal
                leftMargin: 16
                rightMargin: 16
                clip: true
                model: page.homeData.artists
                delegate: AlbumCard {
                    width: 186
                    height: 246
                    coverSource: "image://cover/artist/" + modelData.id + "?v=" + Theme.dataRevision
                    title: modelData.name
                    subtitle: "\u25b6 " + modelData.plays + " \u00b7 " + Theme.plural(modelData.tracks, "pista", "pistas")
                    onClicked: page.artistClicked(modelData.id, modelData.name)
                }
            }

            // ---- Canciones m\u00e1s escuchadas ----
            Text { visible: page.homeData.tracks.length > 0; x: 24; text: "Canciones m\u00e1s escuchadas"; color: Theme.text; font.pixelSize: 18; font.weight: Font.Bold }
            Repeater {
                model: page.homeData.tracks
                delegate: TrackRow {
                    width: col.width
                    number: (index + 1).toString()
                    title: modelData.title
                    subtitle: modelData.artist + " \u00b7 " + modelData.album
                    duration: Theme.fmt(modelData.duration)
                    plays: modelData.plays
                    trackId: modelData.id
                    current: player.currentId === modelData.id
                    onActivated: player.playTrackIds(page.trackIds, index)
                    onContextRequested: page.menuRequested([modelData.id])
                }
            }
        }
    }
}
