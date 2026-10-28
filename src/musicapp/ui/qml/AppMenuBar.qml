import QtQuick
import QtQuick.Controls
import "."

MenuBar {
    id: root
    implicitHeight: 32
    background: Rectangle {
        color: "#0a0a0b"
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#26262a" }
    }
    delegate: MenuBarItem {
        id: item
        implicitHeight: 32
        leftPadding: 12
        rightPadding: 12
        contentItem: Text {
            text: item.text
            color: Theme.text
            font.pixelSize: 13
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            anchors { fill: parent; topMargin: 3; bottomMargin: 3 }
            radius: 4
            color: item.highlighted ? Theme.surfaceHover : "transparent"
        }
    }
}
