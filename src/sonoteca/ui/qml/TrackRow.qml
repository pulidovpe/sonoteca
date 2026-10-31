import QtQuick
import "."

// Fila de canción. Columnas según el ancho (Theme.tier): pista · nombre con el artista debajo · álbum · año · reproducciones.
// Ancho amplio: todas; medio: hasta el álbum; mínimo: pista y nombre. La duración y el menú ⋮ se mantienen siempre.
Item {
    id: root
    property string number: ""
    property string title
    property string artist: ""      // segunda línea del nombre
    property string album: ""
    property string year: ""
    property string subtitle: ""    // texto libre cuando no hay artista (p. ej. «Por revisar»)
    property string badge: ""
    property string duration: ""
    property int plays: -1          // < 0: no se muestra
    property int trackId: 0         // > 0: se puede arrastrar a una lista de la barra lateral
    property bool current: false
    signal activated()
    signal contextRequested()
    readonly property int tier: Theme.tier(width)
    readonly property bool showAlbum: tier >= 2 && album !== ""
    readonly property bool showYear: tier >= 3 && year !== ""
    readonly property bool showPlays: tier >= 3 && plays >= 0
    readonly property string line2: artist !== "" ? artist : subtitle
    height: 52
    opacity: dragHandler.active ? 0.45 : 1

    HoverHandler { id: rowHover }
    TrackDragHandler { id: dragHandler; ids: root.trackId > 0 ? [root.trackId] : []; label: root.title }

    Rectangle {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        radius: 6
        color: mouse.containsMouse ? Theme.surfaceHover : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    Text {
        id: num
        text: root.number
        x: 28
        width: root.number === "" ? 0 : 36
        anchors.verticalCenter: parent.verticalCenter
        color: Theme.textDim
        font.pixelSize: 14
    }
    Column {
        anchors.left: num.right
        anchors.leftMargin: root.number === "" ? 0 : 8
        anchors.right: moreButton.left
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        Text {
            width: parent.width
            text: root.title
            color: root.current ? Theme.accent : Theme.text
            font.pixelSize: 15
            elide: Text.ElideRight
        }
        Text {
            width: parent.width
            visible: root.line2 !== ""
            text: root.line2
            color: Theme.textDim
            font.pixelSize: 12
            elide: Text.ElideRight
        }
    }
    // Columnas de la derecha, en este orden: álbum, año, reproducciones, etiqueta y duración
    Row {
        id: cells
        anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
        spacing: 16
        Text {
            visible: root.showAlbum
            width: Theme.albumColumn(root.width)
            text: root.album
            color: Theme.textDim
            font.pixelSize: 13
            elide: Text.ElideRight
        }
        Text {
            visible: root.showYear
            width: Theme.yearColumn
            text: root.year
            color: Theme.textDim
            font.pixelSize: 13
        }
        Text {
            visible: root.showPlays
            width: Theme.playsColumn
            text: "\u25b6 " + root.plays
            color: Theme.textDim
            font.pixelSize: 12
        }
        Rectangle {
            id: badgeBox
            visible: root.badge !== ""
            width: visible ? badgeText.width + 14 : 0
            height: 20
            radius: 4
            color: "transparent"
            border.color: Theme.textDim
            border.width: 1
            anchors.verticalCenter: parent.verticalCenter
            Text {
                id: badgeText
                anchors.centerIn: parent
                text: root.badge
                color: Theme.textDim
                font.pixelSize: 10
                font.weight: Font.DemiBold
            }
        }
        Text {
            id: dur
            text: root.duration
            width: root.duration === "" ? 0 : implicitWidth
            color: Theme.textDim
            font.pixelSize: 14
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: (m) => { if (m.button === Qt.RightButton) root.contextRequested() }
        onDoubleClicked: (m) => { if (m.button === Qt.LeftButton) root.activated() }
    }
    // Botón de opciones (⋮): aparece al pasar el ratón y abre el menú con todas las acciones
    IconButton {
        id: moreButton
        width: 28
        height: 28
        iconSize: 16
        svg: Theme.iconMore
        enabled: rowHover.hovered
        opacity: rowHover.hovered ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        anchors.right: cells.left
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        onClicked: root.contextRequested()
    }
}
