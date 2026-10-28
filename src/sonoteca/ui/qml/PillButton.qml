import QtQuick
import "."

Rectangle {
    id: root
    property string label
    property bool primary: false
    signal clicked()
    height: 38
    width: t.width + 36
    radius: 19
    opacity: enabled ? 1 : 0.4
    color: primary ? (mouse.containsMouse ? Theme.accentHover : Theme.accent)
                   : (mouse.containsMouse ? Theme.surfaceHover : Theme.surfaceRaised)
    Behavior on color { ColorAnimation { duration: Theme.fast } }
    Text {
        id: t
        anchors.centerIn: parent
        text: root.label
        color: root.primary ? Theme.onAccent : Theme.text
        font.pixelSize: 14
        font.weight: Font.DemiBold
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
