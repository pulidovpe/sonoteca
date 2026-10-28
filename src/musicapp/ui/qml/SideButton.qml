import QtQuick
import "."

Item {
    id: root
    property string label
    property string hint: ""
    property bool active: false
    signal clicked()
    implicitHeight: 44

    Rectangle {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        radius: 8
        color: mouse.containsMouse ? Theme.surfaceHover : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    Rectangle {
        width: 4
        height: root.active ? 22 : 0
        radius: 2
        color: Theme.accent
        anchors.verticalCenter: parent.verticalCenter
        Behavior on height { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
    }
    Text {
        text: root.label
        x: 24
        anchors.verticalCenter: parent.verticalCenter
        color: root.active ? Theme.text : Theme.textDim
        font.pixelSize: 15
        font.weight: root.active ? Font.DemiBold : Font.Normal
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    Text {
        text: root.hint
        visible: root.hint !== ""
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        color: Theme.textDim
        font.pixelSize: 12
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
