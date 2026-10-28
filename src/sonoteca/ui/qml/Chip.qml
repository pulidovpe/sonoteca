import QtQuick
import "."

Rectangle {
    id: root
    property string label
    property bool active: false
    signal clicked()
    height: 32
    width: t.width + 28
    radius: 16
    color: active ? Theme.accent : (mouse.containsMouse ? Theme.surfaceHover : Theme.surface)
    Behavior on color { ColorAnimation { duration: Theme.fast } }

    Text {
        id: t
        anchors.centerIn: parent
        text: root.label
        color: root.active ? Theme.textOnAccent : Theme.text
        font.pixelSize: 13
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
