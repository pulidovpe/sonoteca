pragma Singleton
import QtQuick

// Estado compartido del arrastre de canciones (a una lista de la barra lateral o para reordenar)
QtObject {
    property bool active: false
    property var ids: []
    property string label: ""
    property real sceneX: 0       // posición del puntero en coordenadas de la ventana
    property real sceneY: 0
    property real startY: 0
    property int hoverListId: 0   // lista de la barra lateral bajo el puntero (0: ninguna)
    signal dropOnList(int listId, var ids)

    function begin(trackIds, text, x, y) {
        if (!trackIds || trackIds.length === 0) return
        ids = trackIds
        label = text
        sceneX = x; sceneY = y; startY = y
        hoverListId = 0
        active = true
    }
    function move(x, y) { sceneX = x; sceneY = y }
    function end() { active = false; hoverListId = 0 }
}
