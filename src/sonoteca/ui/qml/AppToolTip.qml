import QtQuick
import QtQuick.Controls
import "."

// Tooltip con el estilo del tema (el predeterminado de Qt es claro y desentona)
ToolTip {
    id: tip
    delay: 350
    padding: 8
    leftPadding: 10
    rightPadding: 10
    contentItem: Text {
        text: tip.text
        color: Theme.text
        font.pixelSize: 12
        lineHeight: 1.25
    }
    background: Rectangle {
        color: Theme.panel
        border.color: Theme.border
        radius: 6
    }
}
