import QtQuick
import "."

Item {
    id: root
    property string number: ""
    property string title
    property string subtitle: ""
    property string badge: ""
    property string duration: ""
    property int plays: -1   // < 0: no se muestra
    property int trackId: 0  // > 0: se puede arrastrar a una lista de la barra lateral
    property bool current: false
    signal activated()
    signal contextRequested()
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
            visible: root.subtitle !== ""
            text: root.subtitle
            color: Theme.textDim
            font.pixelSize: 12
            elide: Text.ElideRight
        }
    }
    Text {
        id: playsText
        visible: root.plays >= 0
        text: "\u25b6 " + root.plays
        color: Theme.textDim
        font.pixelSize: 12
        anchors { right: badgeBox.left; rightMargin: 14; verticalCenter: parent.verticalCenter }
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
        anchors.right: dur.left
        anchors.rightMargin: visible ? 16 : 0
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
        anchors.right: parent.right
        anchors.rightMargin: 28
        anchors.verticalCenter: parent.verticalCenter
        color: Theme.textDim
        font.pixelSize: 14
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
        anchors.right: playsText.visible ? playsText.left : (badgeBox.visible ? badgeBox.left : dur.left)
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        onClicked: root.contextRequested()
    }
}
