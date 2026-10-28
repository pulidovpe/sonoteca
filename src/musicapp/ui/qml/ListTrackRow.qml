import QtQuick
import "."

// Fila de una lista de reproducción (la cola o una lista guardada)
Item {
    id: row
    property int position: 0
    property string title
    property string subtitle
    property real duration: 0
    property int plays: -1   // < 0: no se muestra
    property int trackId: 0
    property int count: 0    // filas de la lista (para reordenar arrastrando)
    signal reorderRequested(int dst)
    property bool current: false
    property bool playing: false
    signal activated()
    signal menuRequested()
    signal editRequested()
    signal moveUp()
    signal moveDown()
    signal removeRequested()
    height: 56
    opacity: dragHandler.active ? 0.45 : 1

    TrackDragHandler {
        id: dragHandler
        ids: row.trackId > 0 ? [row.trackId] : []
        label: row.title
        position: row.position
        count: row.count
        rowHeight: row.height
        onReorderRequested: (dst) => row.reorderRequested(dst)
    }
    HoverHandler { id: hover }
    Rectangle {
        anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
        radius: 6
        color: hover.hovered ? Theme.surfaceHover : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: (m) => { if (m.button === Qt.RightButton) row.menuRequested() }
        onDoubleClicked: (m) => { if (m.button === Qt.LeftButton) row.activated() }
    }
    Item {
        id: marker
        x: 28
        width: 28
        height: parent.height
        Icon {
            anchors.centerIn: parent
            visible: row.current
            svg: row.playing ? Theme.iconPlay : Theme.iconPause
            size: 14
            color: Theme.accent
        }
        Text {
            anchors.centerIn: parent
            visible: !row.current
            text: row.position + 1
            color: Theme.textDim
            font.pixelSize: 13
        }
    }
    Column {
        anchors { left: marker.right; leftMargin: 8; right: actions.left; rightMargin: 12; verticalCenter: parent.verticalCenter }
        spacing: 2
        Text { width: parent.width; text: row.title; color: row.current ? Theme.accent : Theme.text; font.pixelSize: 15; elide: Text.ElideRight }
        Text { width: parent.width; text: row.subtitle; color: Theme.textDim; font.pixelSize: 12; elide: Text.ElideRight }
    }
    Row {
        id: actions
        anchors { right: playsText.visible ? playsText.left : dur.left; rightMargin: 12; verticalCenter: parent.verticalCenter }
        spacing: 2
        opacity: hover.hovered ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        IconButton { width: 30; height: 30; iconSize: 16; svg: Theme.iconMore; onClicked: row.menuRequested() }
        IconButton { width: 30; height: 30; iconSize: 13; svg: Theme.iconUp; onClicked: row.moveUp() }
        IconButton { width: 30; height: 30; iconSize: 13; svg: Theme.iconDown; onClicked: row.moveDown() }
        IconButton { width: 30; height: 30; iconSize: 12; svg: Theme.iconClose; onClicked: row.removeRequested() }
    }
    Text {
        id: playsText
        visible: row.plays >= 0
        text: "\u25b6 " + row.plays
        anchors { right: dur.left; rightMargin: 16; verticalCenter: parent.verticalCenter }
        color: Theme.textDim
        font.pixelSize: 12
    }
    Text {
        id: dur
        text: Theme.fmt(row.duration)
        anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
        color: Theme.textDim
        font.pixelSize: 14
    }
}
