import QtQuick
import QtQuick.Controls
import "."

Item {
    id: page
    property string query: ""
    property var results: (Theme.dataRevision, library.searchAll(query))
    property var ids: results.tracks.map(function (x) { return x.id })
    readonly property bool empty: results.artists.length + results.albums.length + results.tracks.length === 0
    // Canciones sobre las que actúan los botones: las encontradas; si no hay canciones pero el resultado es un solo
    // álbum o un solo artista (lo normal al buscar su nombre), las de ese álbum o artista.
    readonly property var actionIds: {
        if (ids.length > 0) return ids
        if (results.albums.length === 1) return library.tracks(results.albums[0].id).map(function (x) { return x.id })
        if (results.albums.length === 0 && results.artists.length === 1) return library.artistTrackIds(results.artists[0].id)
        return []
    }
    // «Portada e info» necesita un álbum concreto: el único álbum de los resultados (o al que pertenecen las canciones)
    readonly property int lookupAlbumId: {
        var found = {}, count = 0, last = 0
        function add(id) { if (id > 0 && !found[id]) { found[id] = true; count++; last = id } }
        results.albums.forEach(function (a) { add(a.id) })
        results.tracks.forEach(function (t) { var info = library.trackInfo(t.id); if (info.hasAlbum) add(info.albumId) })
        return count === 1 ? last : 0
    }
    function lookupAlbum() {
        var info = library.album(lookupAlbumId)
        lookupRequested(lookupAlbumId, library.tracks(lookupAlbumId).map(function (x) { return x.id }),
                        info.title === "\u00c1lbum desconocido")
    }
    signal albumClicked(int albumId)
    signal playOneRequested(int trackId)
    signal artistClicked(int artistId, string name)
    signal editRequested(var ids)
    signal menuRequested(var ids)
    SelectionState { id: sel }          // «Seleccionar canciones» entre las canciones encontradas
    function trackIds() { return results.tracks.map(function (x) { return x.id }) }
    signal listRequested(var ids)            // «Guardar en lista…» (elegir una lista o crear una)
    signal newListRequested(var ids)         // «Nueva lista» con las canciones
    signal lookupRequested(int albumId, var ids, bool unknown)

    Flickable {
        id: flick
        anchors.fill: parent
        anchors.bottomMargin: selBar.visible ? selBar.height : 0
        contentWidth: width
        contentHeight: col.height + 32
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { }

        Column {
            id: col
            width: flick.width
            spacing: 6

            Text {
                x: 24
                width: parent.width - 48
                text: "Resultados para \u201c" + page.query + "\u201d"
                color: Theme.text
                font.pixelSize: 30
                font.weight: Font.Bold
                elide: Text.ElideRight
            }
            Flow {
                x: 24
                width: parent.width - 48
                spacing: 10
                visible: !page.empty
                PillButton { label: "Nueva lista"; enabled: page.actionIds.length > 0; onClicked: page.newListRequested(page.actionIds) }
                PillButton { label: "Guardar en lista\u2026"; enabled: page.actionIds.length > 0; onClicked: page.listRequested(page.actionIds) }
                PillButton { label: "Portada e info"; enabled: page.lookupAlbumId > 0; onClicked: page.lookupAlbum() }
                PillButton { label: "Editar tags"; enabled: page.actionIds.length > 0; onClicked: page.editRequested(page.actionIds) }
                PillButton { label: sel.active ? "Terminar selecci\u00f3n" : "Seleccionar canciones"; primary: sel.active; enabled: page.results.tracks.length > 0; onClicked: sel.active ? sel.stop() : sel.start() }
            }
            Text {
                x: 24
                visible: page.empty
                text: page.query.trim().length < 2 ? "Escribe al menos 2 letras." : "Sin resultados. Prueba con otras palabras (no importan acentos ni mayúsculas)."
                color: Theme.textDim
                font.pixelSize: 14
            }

            Text { x: 24; visible: page.results.artists.length > 0; topPadding: 14; text: "Artistas"; color: Theme.text; font.pixelSize: 20; font.weight: Font.DemiBold }
            ListView {
                visible: page.results.artists.length > 0
                width: parent.width
                height: visible ? 266 : 0
                orientation: ListView.Horizontal
                leftMargin: 16
                clip: true
                model: page.results.artists
                delegate: AlbumCard {
                    width: 190
                    height: 266
                    coverSource: "image://cover/artist/" + modelData.id + "?v=" + Theme.dataRevision
                    title: modelData.name
                    subtitle: modelData.subtitle
                    onClicked: page.artistClicked(modelData.id, modelData.name)
                }
            }

            Text { x: 24; visible: page.results.albums.length > 0; topPadding: 14; text: "Álbumes"; color: Theme.text; font.pixelSize: 20; font.weight: Font.DemiBold }
            ListView {
                visible: page.results.albums.length > 0
                width: parent.width
                height: visible ? 266 : 0
                orientation: ListView.Horizontal
                leftMargin: 16
                clip: true
                model: page.results.albums
                delegate: AlbumCard {
                    width: 190
                    height: 266
                    albumId: modelData.id
                    title: modelData.title
                    subtitle: modelData.subtitle
                    onClicked: page.albumClicked(modelData.id)
                }
            }

            Text { x: 24; visible: page.results.tracks.length > 0; topPadding: 14; text: "Canciones"; color: Theme.text; font.pixelSize: 20; font.weight: Font.DemiBold }
            Repeater {
                model: page.results.tracks
                delegate: TrackRow {
                    width: col.width
                    title: modelData.title
                    artist: modelData.artist
                    album: modelData.album
                    year: modelData.year
                    badge: modelData.badge
                    duration: modelData.duration > 0 ? Theme.fmt(modelData.duration) : ""
                    current: player.currentId === modelData.id
                    trackId: modelData.id
                    selectable: sel.active
                    selected: (sel.picked, sel.has(modelData.id))
                    onToggled: sel.toggle(modelData.id)
                    onActivated: page.playOneRequested(modelData.id)
                    onContextRequested: page.menuRequested([modelData.id])
                }
            }
        }
    }
    SelectionBar {
        id: selBar
        visible: sel.active
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        count: sel.count
        total: page.results.tracks.length
        onSelectAllRequested: sel.all(page.trackIds())
        onClearRequested: sel.clear()
        onCancelRequested: sel.stop()
        onSaveRequested: { var ids = sel.ordered(page.trackIds()); sel.stop(); page.listRequested(ids) }
        onNewRequested: { var ids = sel.ordered(page.trackIds()); sel.stop(); page.newListRequested(ids) }
    }
}
