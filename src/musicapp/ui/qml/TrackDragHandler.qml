import QtQuick
import "."

// Arrastrar una canción: soltarla sobre una lista de la barra lateral la agrega; soltarla más arriba o
// más abajo dentro de su propia lista (si `position` >= 0) cambia su posición.
DragHandler {
    id: handler
    property var ids: []
    property string label: ""
    property int position: -1      // posición de la fila si la lista se puede reordenar
    property int count: 0
    property real rowHeight: 56
    signal reorderRequested(int dst)

    enabled: ids.length > 0
    target: null
    acceptedButtons: Qt.LeftButton
    grabPermissions: PointerHandler.CanTakeOverFromAnything

    onActiveChanged: {
        if (active) {
            DragState.begin(ids, label, centroid.scenePosition.x, centroid.scenePosition.y)
        } else if (DragState.active) {
            var listId = DragState.hoverListId
            var dy = DragState.sceneY - DragState.startY
            var dragged = DragState.ids
            DragState.end()
            if (listId > 0) {
                DragState.dropOnList(listId, dragged)
            } else if (position >= 0 && count > 1) {
                var dst = Math.max(0, Math.min(count - 1, position + Math.round(dy / rowHeight)))
                if (dst !== position) reorderRequested(dst)
            }
        }
    }
    onCentroidChanged: if (active) DragState.move(centroid.scenePosition.x, centroid.scenePosition.y)
}
