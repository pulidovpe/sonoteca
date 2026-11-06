import QtQuick
import "."

// Fila de canción. Columnas según el ancho (Theme.tier): pista · nombre con el artista debajo · álbum · año · reproducciones.
// Ancho amplio: todas; medio: hasta el álbum (+ año); estrecho: pista, nombre y año. La duración y el menú ⋮ se mantienen siempre.
Item {
    id: root
    property string number: ""
    property string title
    property string artist: ""      // segunda línea del nombre
    // album y year: si la página no los da (undefined) no hay columna; si los da, la columna existe en TODAS las filas
    // (aunque una canción no tenga el dato), para que las columnas queden alineadas entre canciones
    property var album: undefined
    property var year: undefined
    property string subtitle: ""    // texto libre cuando no hay artista (p. ej. «Por revisar»)
    property string badge: ""
    property string duration: ""
    property int plays: -1          // < 0: no se muestra
    property int trackId: 0         // > 0: se puede arrastrar a una lista de la barra lateral
    property bool current: false
    signal activated()
    signal contextRequested()
    readonly property int tier: Theme.tier(width)
    readonly property bool showAlbum: tier >= 2 && album !== undefined
    readonly property bool showYear: width >= Theme.yearMin && year !== undefined
    readonly property bool showPlays: tier >= 3 && plays >= 0
    readonly property string line2: artist !== "" ? artist : subtitle
    height: 52
    opacity: dragHandler.active ? 0.45 : 1

    HoverHandler { id: rowHover; enabled: !DragState.inputBlocked }
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
        Item {   // título; la etiqueta (p. ej. VIDEO) va al final de esta columna, sin desplazar las demás
            width: parent.width
            height: titleText.implicitHeight
            Text {
                id: titleText
                anchors { left: parent.left; right: badgeBox.visible ? badgeBox.left : parent.right; rightMargin: badgeBox.visible ? 8 : 0 }
                text: root.title
                color: root.current ? Theme.accent : Theme.text
                font.pixelSize: 15
                elide: Text.ElideRight
            }
            Rectangle {
                id: badgeBox
                visible: root.badge !== ""
                anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                width: badgeText.width + 14
                height: 20
                radius: 4
                color: "transparent"
                border.color: Theme.textDim
                border.width: 1
                Text {
                    id: badgeText
                    anchors.centerIn: parent
                    text: root.badge
                    color: Theme.textDim
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                }
            }
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
    // Columnas de la derecha, en este orden: álbum, año, reproducciones y duración (todas de ancho fijo)
    Row {
        id: cells
        anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
        spacing: 16
        Text {
            visible: root.showAlbum
            width: Theme.albumColumn(root.width)
            text: root.album ? root.album : ""
            color: Theme.textDim
            font.pixelSize: 13
            elide: Text.ElideRight
        }
        Text {
            visible: root.showYear
            width: Theme.yearColumn
            text: root.year ? root.year : ""
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
        Text {
            id: dur
            text: root.duration
            width: Theme.durationColumn
            horizontalAlignment: Text.AlignRight
            color: Theme.textDim
            font.pixelSize: 14
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: !DragState.inputBlocked
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
