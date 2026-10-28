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
    property int albumId: 0   // > 0: miniatura de la portada del álbum
    property int count: 0    // filas de la lista (para reordenar arrastrando)
    property bool compact: false   // true: panel estrecho (sin contador de reproducciones; acciones sobre la duración al pasar el ratón)
    signal reorderRequested(int dst)
    property bool current: false
    property bool playing: false
    signal activated()
    signal menuRequested()
    signal editRequested()
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
        anchors { fill: parent; leftMargin: row.compact ? 6 : 12; rightMargin: row.compact ? 6 : 12 }
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
        x: row.compact ? 10 : 28
        width: row.compact ? 24 : 28
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
    Rectangle {
        id: thumb
        visible: row.albumId > 0
        width: visible ? (row.compact ? 36 : 40) : 0
        height: row.compact ? 36 : 40
        radius: 4
        color: Theme.placeholder
        anchors { left: marker.right; leftMargin: 6; verticalCenter: parent.verticalCenter }
        Image {
            anchors.fill: parent
            source: row.albumId > 0 ? "image://cover/" + row.albumId + "?v=" + Theme.dataRevision : ""
            sourceSize.width: 80
            sourceSize.height: 80
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
        }
    }
    Column {
        anchors { left: thumb.right; leftMargin: row.compact ? 8 : 10; right: row.compact ? dur.left : actions.left; rightMargin: row.compact ? 8 : 12; verticalCenter: parent.verticalCenter }
        spacing: 2
        Text { width: parent.width; text: row.title; color: row.current ? Theme.accent : Theme.text; font.pixelSize: 15; elide: Text.ElideRight }
        Text { width: parent.width; text: row.subtitle; color: Theme.textDim; font.pixelSize: 12; elide: Text.ElideRight }
    }
    Rectangle {   // en el modo compacto las acciones tapan la duración: fondo para que se lean
        visible: row.compact && hover.hovered
        anchors { fill: actions; margins: -2 }
        radius: 6
        color: Theme.surfaceRaised
    }
    Row {
        id: actions
        anchors { right: row.compact ? parent.right : (playsText.visible ? playsText.left : dur.left); rightMargin: row.compact ? 10 : 12; verticalCenter: parent.verticalCenter }
        spacing: 2
        opacity: hover.hovered ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        IconButton { width: 30; height: 30; iconSize: 16; svg: Theme.iconMore; onClicked: row.menuRequested() }
        IconButton { width: 30; height: 30; iconSize: 12; svg: Theme.iconClose; onClicked: row.removeRequested() }
    }
    Text {
        id: playsText
        visible: !row.compact && row.plays >= 0
        text: "\u25b6 " + row.plays
        anchors { right: dur.left; rightMargin: 16; verticalCenter: parent.verticalCenter }
        color: Theme.textDim
        font.pixelSize: 12
    }
    Text {
        id: dur
        text: Theme.fmt(row.duration)
        anchors { right: parent.right; rightMargin: row.compact ? 14 : 28; verticalCenter: parent.verticalCenter }
        color: Theme.textDim
        font.pixelSize: row.compact ? 12 : 14
        opacity: row.compact && hover.hovered ? 0 : 1
    }
}
