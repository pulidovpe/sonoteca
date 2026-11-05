import QtQuick
import QtQuick.Controls
import "."

Menu {
    id: root
    padding: 6
    // El ListView interno calcula su alto con retraso: si se muestran/ocultan opciones justo antes de abrir (p. ej.
    // «Eliminar archivo»), el menú quedaba con un hueco al final. Se fuerza el cálculo antes de mostrarlo.
    onAboutToShow: if (contentItem && typeof contentItem.forceLayout === "function") contentItem.forceLayout()
    background: Rectangle {
        implicitWidth: 280
        color: Theme.panel
        radius: 8
        border.color: Theme.border
        border.width: 1
    }
}
