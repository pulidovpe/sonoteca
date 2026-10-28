import QtQuick
import QtQuick.Controls
import "."

MenuItem {
    id: item
    implicitWidth: 280
    implicitHeight: 32
    leftPadding: 14
    rightPadding: 14
    readonly property string shortcutText: item.action && item.action.shortcut
        ? String(item.action.shortcut).replace("Ctrl+", Qt.platform.os === "osx" ? "\u2318" : "Ctrl+")
        : ""
    contentItem: Item {
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: item.text
            color: item.enabled ? Theme.text : Theme.textFaint
            font.pixelSize: 13
        }
        Text {
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            text: item.shortcutText
            color: Theme.textDim
            font.pixelSize: 12
        }
    }
    background: Rectangle {
        anchors.fill: parent
        radius: 4
        color: item.highlighted && item.enabled ? Theme.surfaceHover : "transparent"
    }
}
