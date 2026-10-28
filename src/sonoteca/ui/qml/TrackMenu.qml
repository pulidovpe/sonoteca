import QtQuick
import QtQuick.Controls
import "."

// Menú de clic derecho sobre una o varias canciones
AppMenu {
    id: root
    property var ids: []
    signal editRequested(var ids)
    signal listPickerRequested(var ids)
    signal lyricsRequested(int id)
    signal playOneRequested(int id)   // una sola canción con lista en marcha: hay que preguntar

    function playNow() {
        if (ids.length === 1 && player.queueLength > 0) playOneRequested(ids[0])
        else player.playTrackIds(ids, 0)
    }
    function playLater() { player.playNext(ids) }
    function addToList() { player.addToQueue(ids) }
    function edit() { editRequested(ids) }

    AppMenuItem {
        text: root.ids.length > 1 ? "Reproducir ahora (" + root.ids.length + " pistas)" : "Reproducir ahora"
        onTriggered: root.playNow()
    }
    AppMenuItem {
        text: "Reproducir a continuaci\u00f3n"
        enabled: player.queueLength > 0
        onTriggered: root.playLater()
    }
    AppMenuItem {
        text: player.queueLength > 0 ? "Agregar a la lista actual" : "Agregar a una lista temporal nueva"
        onTriggered: root.addToList()
    }
    AppMenuItem { text: "Agregar a una lista\u2026"; onTriggered: root.listPickerRequested(root.ids) }
    AppMenuSeparator { }
    AppMenuItem { text: "Ver letra"; enabled: root.ids.length === 1; onTriggered: root.lyricsRequested(root.ids[0]) }
    AppMenuItem { text: "Editar tags\u2026"; onTriggered: root.edit() }
}
