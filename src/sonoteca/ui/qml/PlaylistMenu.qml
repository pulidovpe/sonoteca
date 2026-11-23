import QtQuick
import QtQuick.Controls
import "."

// Menú de clic derecho (o ⋮) sobre una lista guardada: sus opciones aplicadas a la lista entera
AppMenu {
    id: root
    property int playlistId: 0
    property string listName: ""
    property var ids: []
    signal renameRequested(int playlistId, string name)
    signal deleteRequested(int playlistId, string name)
    property alias playItem: playItem            // para las pruebas
    property alias deleteItem: deleteItem

    function openFor(id, name) {
        playlistId = id
        listName = name
        ids = playlists.trackIds(id)
        popup()
    }
    // «Reproducir»: la lista de reproducción pasa a ser esta lista (con Aleatorio, en orden al azar)
    function play() {
        var source = "playlist:" + playlistId
        if (player.shuffle) player.playShuffled(source, ids)
        else player.playFrom(source, ids, 0)
    }

    AppMenuItem {
        id: playItem
        text: root.ids.length > 0 ? "Reproducir (" + Theme.plural(root.ids.length, "canci\u00f3n", "canciones") + ")" : "Reproducir"
        enabled: root.ids.length > 0
        onTriggered: root.play()
    }
    AppMenuItem {
        text: "Reproducir en orden aleatorio"
        enabled: root.ids.length > 0
        onTriggered: player.playShuffled("playlist:" + root.playlistId, root.ids)
    }
    AppMenuItem {
        text: "Reproducir a continuaci\u00f3n"
        enabled: root.ids.length > 0 && player.queueLength > 0
        onTriggered: player.playNext(root.ids)
    }
    AppMenuItem {
        text: player.queueLength > 0 ? "Agregar al final de la lista de reproducci\u00f3n" : "Agregar a una lista temporal nueva"
        enabled: root.ids.length > 0
        onTriggered: player.addToQueue(root.ids)
    }
    AppMenuSeparator { }
    AppMenuItem { text: "Renombrar\u2026"; onTriggered: root.renameRequested(root.playlistId, root.listName) }
    AppMenuSeparator { }
    AppMenuItem {
        id: deleteItem
        text: "Eliminar lista\u2026"
        onTriggered: root.deleteRequested(root.playlistId, root.listName)
    }
}
