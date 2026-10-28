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
    property alias artistHeaderItem: artistHeader  // para las pruebas

    property var albums: (Theme.dataRevision, library.albums(artistId, 0, decade))
    property var decades: (Theme.dataRevision, library.decades())

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
