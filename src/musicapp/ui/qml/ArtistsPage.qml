import QtQuick
import QtQuick.Controls
import "."

Item {
    id: page
    property var artists: (Theme.dataRevision, library.artists())
    signal artistClicked(int artistId, string name)

    Text {
        id: title
        text: "Artistas"
        color: Theme.text
        font.pixelSize: 30
        font.weight: Font.Bold
        anchors { left: parent.left; top: parent.top; leftMargin: 24; topMargin: 8 }
    }
    Text {
        id: count
        text: page.artists.length + (page.artists.length === 1 ? " artista" : " artistas")
        color: Theme.textDim
        font.pixelSize: 13
        anchors { left: parent.left; top: title.bottom; leftMargin: 24; topMargin: 2 }
    }
    GridView {
        id: grid
        clip: true
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; top: count.bottom; leftMargin: 16; rightMargin: 8; topMargin: 12 }
        property int columns: Math.max(2, Math.floor(width / 190))
        cellWidth: Math.floor(width / columns)
        cellHeight: cellWidth + 76
        model: page.artists
        delegate: AlbumCard {
            width: grid.cellWidth
            height: grid.cellHeight
            coverSource: "image://cover/artist/" + modelData.id + "?v=" + Theme.dataRevision
            title: modelData.name
            subtitle: Theme.plural(modelData.albums, "álbum", "álbumes") + " · " + Theme.plural(modelData.tracks, "pista", "pistas")
            onClicked: page.artistClicked(modelData.id, modelData.name)
        }
        populate: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 280 } }
        ScrollBar.vertical: ScrollBar { }
    }
}
