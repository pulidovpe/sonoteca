import QtQuick
import "."

// Texto que es un enlace: al pasar el ratón se subraya y toma el color de acento; el clic izquierdo emite `clicked()`.
// (El clic derecho sigue llegando a la fila que lo contiene.)
Text {
    id: root
    property bool linkEnabled: true
    property color baseColor: Theme.textDim
    signal clicked()
    color: (area.containsMouse && root.linkEnabled) ? Theme.accent : baseColor
    font.underline: area.containsMouse && root.linkEnabled
    elide: Text.ElideRight
    MouseArea {
        id: area
        enabled: root.linkEnabled && root.text !== "" && !DragState.inputBlocked
        width: Math.min(parent.width, parent.implicitWidth)
        height: parent.height
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
