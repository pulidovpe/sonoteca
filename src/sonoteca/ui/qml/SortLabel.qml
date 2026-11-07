import QtQuick
import "."

// Título de una columna; si tiene `key`, al pulsarlo se ordena por esa columna (flecha en la activa)
Item {
    id: root
    property string text: ""
    property string key: ""            // "" = columna sin orden
    property string current: ""        // clave activa de la cabecera
    property bool asc: true
    property int align: Text.AlignLeft
    readonly property bool active: key !== "" && current === key
    signal clicked()
    height: 28
    Text {
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width
        text: root.text + (root.active ? (root.asc ? " \u25b2" : " \u25bc") : "")
        color: root.active ? Theme.accent : ((root.key !== "" && mouse.containsMouse) ? Theme.text : Theme.textDim)
        font.pixelSize: 12
        font.weight: Font.DemiBold
        horizontalAlignment: root.align
        elide: Text.ElideRight
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: root.key !== "" && !DragState.inputBlocked
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
