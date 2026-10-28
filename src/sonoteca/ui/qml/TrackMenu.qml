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
    signal artistRequested(int artistId, string name)
    signal albumRequested(int albumId)
    // Datos de la canción (solo con una seleccionada) para los enlaces al artista y al álbum
    readonly property var info: ids.length === 1 ? library.trackInfo(ids[0]) : ({})
    signal playOneRequested(int id)   // una sola canción con lista en marcha: hay que preguntar

    function playNow() {
        if (ids.length === 1 && player.queueLength > 0) playOneRequested(ids[0])
        else player.playTrackIds(ids, 0)
    }
    function playLater() { player.playNext(ids) }
    function addToList() { player.addToQueue(ids) }
    function edit() { editRequested(ids) }
    property alias artistItem: artistItem   // para las pruebas
    property alias albumItem: albumItem

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
    AppMenuItem {
        id: artistItem
        text: "Ir al artista"
        enabled: !!root.info.hasArtist
        onTriggered: root.artistRequested(root.info.artistId, root.info.artist)
    }
    AppMenuItem {
        id: albumItem
        text: "Ir al \u00e1lbum"
        enabled: !!root.info.hasAlbum
        onTriggered: root.albumRequested(root.info.albumId)
    }
    AppMenuSeparator { }
    AppMenuItem { text: "Ver letra"; enabled: root.ids.length === 1; onTriggered: root.lyricsRequested(root.ids[0]) }
    AppMenuItem { text: "Editar tags\u2026"; onTriggered: root.edit() }
}
