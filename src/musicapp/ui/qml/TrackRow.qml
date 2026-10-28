import QtQuick
import "."

Item {
    id: root
    property string number: ""
    property string title
    property string subtitle: ""
    property string badge: ""
    property string duration: ""
    property bool current: false
    signal activated()
    signal contextRequested()
    height: 52

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
        anchors.right: badgeBox.left
        anchors.rightMargin: 70
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
    // Acceso visible al editor: aparece al pasar el ratón
    Text {
        id: editHint
        visible: mouse.containsMouse || hintMouse.containsMouse
        text: "Más"
        color: hintMouse.containsMouse ? Theme.accent : Theme.textDim
        font.pixelSize: 12
        anchors.right: badgeBox.visible ? badgeBox.left : dur.left
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        MouseArea {
            id: hintMouse
            anchors { fill: parent; margins: -6 }
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.contextRequested()
        }
    }
}
