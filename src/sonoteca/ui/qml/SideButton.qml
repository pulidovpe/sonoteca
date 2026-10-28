import QtQuick
import "."

// Botón de la barra lateral: solo icono. `label` es el texto del tooltip; `badge` un contador opcional en la esquina.
Item {
    id: root
    property string label
    property string icon                   // path SVG en un lienzo de 24x24 (uno de los iconos de Theme)
    property var badge: ""                 // "" = sin insignia
    property bool active: false
    property alias hovered: mouse.containsMouse
    signal clicked()
    implicitHeight: 52

    Accessible.role: Accessible.Button
    Accessible.name: root.label

    Rectangle {
        width: 48
        height: 44
        anchors.centerIn: parent
        radius: 12
        color: root.active ? Theme.accentSoft : (mouse.containsMouse ? Theme.surfaceHover : "transparent")
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    Rectangle {
        width: 3
        height: root.active ? 22 : 0
        radius: 2
        color: Theme.accent
        anchors.verticalCenter: parent.verticalCenter
        Behavior on height { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
    }
    Icon {
        anchors.centerIn: parent
        svg: root.icon
        size: 24
        color: root.active ? Theme.accent : (mouse.containsMouse ? Theme.text : Theme.textDim)
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    Rectangle {
        id: badgeBox
        visible: String(root.badge) !== ""
        height: 16
        width: Math.max(16, badgeText.implicitWidth + 8)
        radius: 8
        color: Theme.accent
        x: parent.width / 2 + 6
        y: 4
        Text {
            id: badgeText
            anchors.centerIn: parent
            text: Number(root.badge) > 99 ? "99+" : String(root.badge)
            color: Theme.textOnAccent
            font.pixelSize: 10
            font.weight: Font.Bold
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
    AppToolTip {
        visible: mouse.containsMouse && root.label !== ""
        text: root.label + (badgeBox.visible ? "  \u00b7  " + root.badge : "")
        x: root.width + 2
        y: (root.height - height) / 2
    }
}
