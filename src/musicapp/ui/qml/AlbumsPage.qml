import QtQuick
import QtQuick.Controls
import "."

Item {
    id: page
    property int artistId: 0
    property string heading: "Álbumes"
    property int decade: 0
    signal albumClicked(int albumId)
    signal needInternet()
    signal editArtistRequested(int artistId, string artistName)
    signal menuRequested(var ids)
    property alias artistHeaderItem: artistHeader  // para las pruebas

    property var albums: (Theme.dataRevision, library.albums(artistId, 0, decade))
    property var decades: (Theme.dataRevision, library.decades())
    // En la página de un artista con varios álbumes: primero sus canciones destacadas (hasta 2 por álbum)
    property var topTracks: (Theme.dataRevision, player.statsRevision, artistId > 0 ? library.artistTopTracks(artistId) : [])
    property var topIds: topTracks.map(function (x) { return x.id })
    readonly property bool showTop: artistId > 0 && topTracks.length > 0
    // Máximo 5 a la vista; si hay más, se muestran 4 y un botón para ver todas
    property bool topExpanded: false
    readonly property bool topHasMore: topTracks.length > 5
    readonly property var shownTop: (topExpanded || !topHasMore) ? topTracks : topTracks.slice(0, 4)

    Text {
        id: title
        text: page.heading
        color: Theme.text
        font.pixelSize: 30
        font.weight: Font.Bold
        elide: Text.ElideRight
        anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: 24; rightMargin: page.artistId > 0 ? 160 : 24; topMargin: 8 }
    }
    PillButton {
        id: editArtistButton
        visible: page.artistId > 0
        label: "Editar tags"
        onClicked: page.editArtistRequested(page.artistId, page.heading)
        anchors { right: parent.right; rightMargin: 24; verticalCenter: title.verticalCenter }
    }
    Text {
        id: count
        text: page.albums.length + (page.albums.length === 1 ? " álbum" : " álbumes")
        color: Theme.textDim
        font.pixelSize: 13
        anchors { left: parent.left; top: title.bottom; leftMargin: 24; topMargin: 2 }
    }
    ArtistHeader {
        id: artistHeader
        visible: page.artistId > 0
        artistId: page.artistId
        artistName: page.heading
        onNeedInternet: page.needInternet()
        height: visible ? implicitHeight : 0
        anchors { left: parent.left; right: parent.right; top: count.bottom; leftMargin: 24; rightMargin: 24; topMargin: 12 }
    }
    Flow {
        id: chips
        visible: page.artistId === 0 && page.decades.length > 0
        spacing: 8
        anchors { left: parent.left; right: parent.right; top: count.bottom; leftMargin: 24; rightMargin: 24; topMargin: 14 }
        Chip { label: "Todos"; active: page.decade === 0; onClicked: page.decade = 0 }
        Repeater {
            model: page.decades
            Chip {
                label: modelData.decade + "s"
                active: page.decade === modelData.decade
                onClicked: page.decade = modelData.decade
            }
        }
    }
    GridView {
        id: grid
        clip: true
        anchors {
            left: parent.left; right: parent.right; bottom: parent.bottom
            top: chips.visible ? chips.bottom : (artistHeader.visible ? artistHeader.bottom : count.bottom)
            leftMargin: 16; rightMargin: 8; topMargin: 12
        }
        property int columns: Math.max(2, Math.floor(width / 190))
        cellWidth: Math.floor(width / columns)
        cellHeight: cellWidth + 76
        model: page.albums
        header: Item {
            width: grid.width
            height: page.showTop ? topColumn.height : 0
            visible: page.showTop
            Column {
                id: topColumn
                width: parent.width - 8
                Text { text: "Canciones destacadas"; leftPadding: 12; height: 40; verticalAlignment: Text.AlignVCenter; color: Theme.text; font.pixelSize: 18; font.weight: Font.Bold }
                Repeater {
                    model: page.shownTop
                    delegate: TrackRow {
                        width: topColumn.width
                        number: (index + 1).toString()
                        title: modelData.title
                        subtitle: modelData.album
                        duration: Theme.fmt(modelData.duration)
                        plays: modelData.plays
                        trackId: modelData.id
                        current: player.currentId === modelData.id
                        onActivated: player.playTrackIds(page.topIds, index)
                        onContextRequested: page.menuRequested([modelData.id])
                    }
                }
                PillButton {
                    x: 12
                    height: 32
                    visible: page.topHasMore
                    label: page.topExpanded ? "Mostrar menos" : "Mostrar m\u00e1s (" + (page.topTracks.length - 4) + ")"
                    onClicked: page.topExpanded = !page.topExpanded
                }
                Text { text: "\u00c1lbumes"; leftPadding: 12; height: 52; verticalAlignment: Text.AlignBottom; bottomPadding: 6; color: Theme.text; font.pixelSize: 18; font.weight: Font.Bold }
            }
        }
        delegate: AlbumCard {
            width: grid.cellWidth
            height: grid.cellHeight
            albumId: modelData.id
            title: modelData.displayTitle
            subtitle: modelData.artist + (modelData.year > 0 ? " · " + modelData.year : "")
            onClicked: page.albumClicked(modelData.id)
        }
        populate: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 280 } }
        ScrollBar.vertical: ScrollBar { }
    }
}
