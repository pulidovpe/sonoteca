import QtQuick
import QtQuick.Controls
import "."

Item {
    id: page
    property var lists: (playlists.revision, playlists.lists())
    property bool gridMode: prefs.boolValue("playlists.grid", false)      // se guarda entre sesiones
    function setGrid(on) { gridMode = on; prefs.setBool("playlists.grid", on) }
    signal openPlaylist(int playlistId)
    signal menuRequested(int playlistId, string name)
    signal newRequested()
    signal foldersRequested()    // crear listas a partir de carpetas de la biblioteca

    Text {
        id: title
        text: "Listas de reproducci\u00f3n"
        color: Theme.text
        font.pixelSize: 30
        font.weight: Font.Bold
        anchors { left: parent.left; top: parent.top; leftMargin: 24; topMargin: 8 }
    }
    Text {
        id: sub
        text: Theme.plural(page.lists.length, "lista", "listas")
        color: Theme.textDim
        font.pixelSize: 13
        anchors { left: parent.left; top: title.bottom; leftMargin: 24; topMargin: 2 }
    }
    PillButton {
        id: newButton
        label: "Nueva lista"
        primary: true
        anchors { left: parent.left; top: sub.bottom; leftMargin: 24; topMargin: 12 }
        onClicked: page.newRequested()
    }
    PillButton {
        id: foldersButton
        label: "Crear desde carpetas\u2026"
        anchors { left: newButton.right; leftMargin: 10; verticalCenter: newButton.verticalCenter }
        onClicked: page.foldersRequested()
    }
    Row {
        spacing: 4
        visible: page.lists.length > 0
        anchors { right: parent.right; rightMargin: 24; verticalCenter: newButton.verticalCenter }
        IconButton { id: rowsButton; svg: Theme.iconRows; toolTip: "Ver en lista"; active: !page.gridMode; onClicked: page.setGrid(false) }
        IconButton { id: gridButton; svg: Theme.iconGrid; toolTip: "Ver en cuadr\u00edcula"; active: page.gridMode; onClicked: page.setGrid(true) }
    }
    property alias rowsToggle: rowsButton        // para las pruebas
    property alias gridToggle: gridButton
    Text {
        visible: page.lists.length === 0
        width: parent.width - 48
        anchors { left: parent.left; top: newButton.bottom; leftMargin: 24; topMargin: 24 }
        wrapMode: Text.WordWrap
        color: Theme.textDim
        font.pixelSize: 14
        text: "Todav\u00eda no tienes listas. Crea una, o guarda la lista actual desde \u00abReproduciendo\u00bb. Tambi\u00e9n puedes hacer clic derecho en una canci\u00f3n \u25b8 Agregar a una lista\u2026"
    }
    Item {
        id: body
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; top: newButton.bottom; topMargin: 12 }
        ListView {
            id: list
            visible: !page.gridMode
            clip: true
            anchors.fill: parent
            model: page.lists
            delegate: Item {
                width: list.width
                height: 64
                HoverHandler { id: rowHover }        // independiente de los MouseArea de encima (el botón ⋮ no apaga el resaltado)
                Rectangle {
                    anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                    radius: 8
                    color: rowHover.hovered ? Theme.surfaceHover : "transparent"
                    Behavior on color { ColorAnimation { duration: Theme.fast } }
                }
                PlaylistCover {
                    id: icon
                    x: 24
                    anchors.verticalCenter: parent.verticalCenter
                    width: 48; height: 48
                    fallback: Theme.coverColor(modelData.id)
                    albumIds: (playlists.revision, Theme.dataRevision, playlists.coverAlbums(modelData.id))
                }
                Column {
                    anchors { left: icon.right; leftMargin: 16; right: parent.right; rightMargin: 64; verticalCenter: parent.verticalCenter }
                    spacing: 2
                    Text { width: parent.width; text: modelData.name; color: Theme.text; font.pixelSize: 15; elide: Text.ElideRight }
                    Text {
                        width: parent.width
                        text: Theme.plural(modelData.tracks, "canci\u00f3n", "canciones") + (modelData.tracks > 0 ? " \u00b7 " + Theme.fmtLong(modelData.duration) : "")
                        color: Theme.textDim
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                }
                MouseArea {
                    id: mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    cursorShape: Qt.PointingHandCursor
                    onClicked: (m) => {
                        if (m.button === Qt.RightButton) page.menuRequested(modelData.id, modelData.name)
                        else page.openPlaylist(modelData.id)
                    }
                }
                IconButton {
                    width: 30; height: 30; iconSize: 16
                    svg: Theme.iconMore
                    toolTip: "M\u00e1s opciones"
                    enabled: rowHover.hovered
                    opacity: rowHover.hovered ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                    anchors { right: parent.right; rightMargin: 24; verticalCenter: parent.verticalCenter }
                    onClicked: page.menuRequested(modelData.id, modelData.name)
                }
            }
            ScrollBar.vertical: ScrollBar { }
        }
        GridView {
            id: grid
            visible: page.gridMode
            clip: true
            anchors { fill: parent; leftMargin: 16; rightMargin: 8 }
            property int columns: Math.max(2, Math.floor(width / 190))
            cellWidth: Math.floor(width / columns)
            cellHeight: cellWidth + 76
            model: page.lists
            delegate: Item {
                width: grid.cellWidth
                height: grid.cellHeight
                Rectangle {
                    anchors { fill: parent; margins: 8 }
                    radius: Theme.radius
                    color: cardHover.hovered ? Theme.surfaceHover : Theme.surface
                    scale: cardHover.hovered ? 1.03 : 1.0
                    Behavior on color { ColorAnimation { duration: Theme.fast } }
                    Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
                    HoverHandler { id: cardHover }        // el botón ⋮ de encima no debe apagar el resaltado
                    Column {
                        anchors { fill: parent; margins: 12 }
                        spacing: 10
                        PlaylistCover {
                            width: parent.width
                            height: width
                            fallback: Theme.coverColor(modelData.id)
                            albumIds: (playlists.revision, Theme.dataRevision, playlists.coverAlbums(modelData.id))
                        }
                        Text { width: parent.width; text: modelData.name; color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        Text {
                            width: parent.width
                            text: Theme.plural(modelData.tracks, "canci\u00f3n", "canciones") + (modelData.tracks > 0 ? " \u00b7 " + Theme.fmtLong(modelData.duration) : "")
                            color: Theme.textDim
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }
                    }
                    MouseArea {
                        id: cardMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        cursorShape: Qt.PointingHandCursor
                        onClicked: (m) => {
                            if (m.button === Qt.RightButton) page.menuRequested(modelData.id, modelData.name)
                            else page.openPlaylist(modelData.id)
                        }
                    }
                    Rectangle {
                        width: 30; height: 30; radius: 15
                        color: Theme.surface
                        opacity: cardHover.hovered ? 0.9 : 0
                        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                        anchors { top: parent.top; right: parent.right; topMargin: 16; rightMargin: 16 }
                    }
                    IconButton {
                        width: 30; height: 30; iconSize: 16
                        svg: Theme.iconMore
                        toolTip: "M\u00e1s opciones"
                        enabled: cardHover.hovered
                        opacity: cardHover.hovered ? 1 : 0
                        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                        anchors { top: parent.top; right: parent.right; topMargin: 16; rightMargin: 16 }
                        onClicked: page.menuRequested(modelData.id, modelData.name)
                    }
                }
            }
            ScrollBar.vertical: ScrollBar { }
        }
    }
}
