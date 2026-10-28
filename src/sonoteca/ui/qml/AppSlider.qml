import QtQuick
import QtQuick.Controls
import "."

Slider {
    id: root
    implicitHeight: 16
    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: root.availableWidth
        height: 4
        radius: 2
        color: "#4d4d52"
        Rectangle {
            width: root.visualPosition * parent.width
            height: parent.height
            radius: 2
            color: root.hovered || root.pressed ? Theme.accent : "#ffffff"
            Behavior on color { ColorAnimation { duration: Theme.fast } }
        }
    }
    handle: Rectangle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: 12
        height: 12
        radius: 6
        color: "#ffffff"
        opacity: root.hovered || root.pressed ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
    }
}
