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
    // Canciones añadidas con «Reproducir a continuación»: se distinguen con bandas de acento a ambos lados.
    // upNextTop/upNextBottom marcan el primer y el último de un grupo seguido, para cerrar el recuadro.
    property bool upNext: false
    property bool upNextTop: false
    property bool upNextBottom: false
    // Columnas según el ancho (Theme.tier): pista · nombre con artista debajo · álbum · año · reproducciones
    property string artist: ""
    property string album: ""
    property string year: ""
    readonly property int tier: Theme.tier(width)
    readonly property bool showAlbum: tier >= 2 && album !== ""
    readonly property bool showYear: width >= Theme.yearMin && year !== ""
    readonly property bool showPlays: tier >= 3 && plays >= 0
    readonly property string line2: artist !== "" ? artist : subtitle
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
    HoverHandler { id: hover; enabled: !DragState.inputBlocked }
    Rectangle {   // fondo y bandas de las canciones «a continuación»
        visible: row.upNext
        anchors {
            fill: parent
            leftMargin: row.compact ? 6 : 12
            rightMargin: row.compact ? 6 : 12
            topMargin: row.upNextTop ? 3 : 0
            bottomMargin: row.upNextBottom ? 3 : 0
        }
        color: Qt.alpha(Theme.accent, 0.09)
        Rectangle { width: 4; height: parent.height; radius: 2; color: Theme.accent; anchors.left: parent.left }
        Rectangle { width: 4; height: parent.height; radius: 2; color: Theme.accent; anchors.right: parent.right }
    }
    Rectangle {
        anchors { fill: parent; leftMargin: row.compact ? 6 : 12; rightMargin: row.compact ? 6 : 12 }
        radius: 6
        color: hover.hovered ? Theme.surfaceHover : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    MouseArea {
        anchors.fill: parent
        enabled: !DragState.inputBlocked
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
        anchors { left: thumb.right; leftMargin: row.compact ? 8 : 10; right: row.compact ? cells.left : actions.left; rightMargin: row.compact ? 8 : 12; verticalCenter: parent.verticalCenter }
        spacing: 2
        Text { width: parent.width; text: row.title; color: row.current ? Theme.accent : Theme.text; font.pixelSize: 15; elide: Text.ElideRight }
        Text { width: parent.width; text: row.line2; color: Theme.textDim; font.pixelSize: 12; elide: Text.ElideRight }
    }
    Rectangle {   // en el modo compacto las acciones tapan la duración: fondo para que se lean
        visible: row.compact && hover.hovered
        anchors { fill: actions; margins: -2 }
        radius: 6
        color: Theme.surfaceRaised
    }
    Row {
        id: actions
        anchors { right: row.compact ? parent.right : cells.left; rightMargin: row.compact ? 10 : 12; verticalCenter: parent.verticalCenter }
        spacing: 2
        opacity: hover.hovered ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        IconButton { width: 30; height: 30; iconSize: 16; svg: Theme.iconMore; onClicked: row.menuRequested() }
        IconButton { width: 30; height: 30; iconSize: 12; svg: Theme.iconClose; onClicked: row.removeRequested() }
    }
    // Columnas de la derecha, en este orden: álbum, año, reproducciones y duración
    Row {
        id: cells
        anchors { right: parent.right; rightMargin: row.compact ? 14 : 28; verticalCenter: parent.verticalCenter }
        spacing: row.compact ? 10 : 16
        Text {
            visible: row.showAlbum
            width: Theme.albumColumn(row.width)
            text: row.album
            color: Theme.textDim
            font.pixelSize: 13
            elide: Text.ElideRight
        }
        Text { visible: row.showYear; width: row.compact ? Theme.yearColumnCompact : Theme.yearColumn; text: row.year; color: Theme.textDim; font.pixelSize: 13 }
        Text { visible: row.showPlays; width: Theme.playsColumn; text: "▶ " + row.plays; color: Theme.textDim; font.pixelSize: 12 }
        Text {
            id: dur
            text: Theme.fmt(row.duration)
            color: Theme.textDim
            font.pixelSize: row.compact ? 12 : 14
            opacity: row.compact && hover.hovered ? 0 : 1
        }
    }
}
