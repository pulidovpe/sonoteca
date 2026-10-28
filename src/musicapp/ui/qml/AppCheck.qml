import QtQuick
import QtQuick.Controls
import "."

CheckBox {
    id: root
    indicator: Rectangle {
        implicitWidth: 18
        implicitHeight: 18
        x: root.leftPadding
        y: root.height / 2 - height / 2
        radius: 4
        color: root.checked ? Theme.accent : "transparent"
        border.color: root.checked ? Theme.accent : Theme.textDim
        Text { anchors.centerIn: parent; text: "\u2713"; visible: root.checked; color: "#000000"; font.pixelSize: 12; font.weight: Font.Bold }
    }
    contentItem: Text {
        text: root.text
        color: Theme.text
        font.pixelSize: 13
        leftPadding: root.indicator.width + 10
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
    }
}
