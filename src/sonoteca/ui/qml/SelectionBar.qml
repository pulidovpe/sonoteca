import QtQuick
import "."

// Barra inferior del modo «seleccionar canciones»
Rectangle {
    id: root
    property int count: 0
    property int total: 0
    signal selectAllRequested()
    signal clearRequested()
    signal saveRequested()
    signal newRequested()
    signal cancelRequested()
    height: 60
    color: Theme.surfaceRaised
    border.color: Theme.border
    border.width: 1
    z: 5
    Text {
        id: summary
        anchors { left: parent.left; leftMargin: 24; verticalCenter: parent.verticalCenter }
        text: Theme.plural(root.count, "canci\u00f3n seleccionada", "canciones seleccionadas")
        color: Theme.text
        font.pixelSize: 14
        font.weight: Font.DemiBold
    }
    Row {
        anchors { right: parent.right; rightMargin: 24; verticalCenter: parent.verticalCenter }
        spacing: 10
        PillButton { label: root.count < root.total ? "Seleccionar todas" : "Quitar selecci\u00f3n"; onClicked: root.count < root.total ? root.selectAllRequested() : root.clearRequested() }
        PillButton { label: "Nueva lista"; enabled: root.count > 0; onClicked: root.newRequested() }
        PillButton { label: "Guardar en lista\u2026"; primary: true; enabled: root.count > 0; onClicked: root.saveRequested() }
        PillButton { label: "Cancelar"; onClicked: root.cancelRequested() }
    }
}
