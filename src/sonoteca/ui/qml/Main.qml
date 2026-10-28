import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import "."

ApplicationWindow {
    id: win
    width: 1280
    height: 800
    minimumWidth: 900
    minimumHeight: 560
    visible: true
    title: "Sonoteca"
    color: Theme.bg

    menuBar: AppMenuBar {
        AppMenu {
            title: "Archivo"
            AppMenuItem { action: actScan }
            AppMenuItem { action: actNewPlaylist }
            AppMenuItem { action: actEditCurrent }
            AppMenuItem { action: actInternet }
            AppMenuItem { action: actServers }
            AppMenuItem { action: actHarvest }
            AppMenuSeparator { }
            AppMenuItem { action: actExport }
            AppMenuItem { action: actImport }
            AppMenuItem { action: actReset }
            AppMenuSeparator { }
            AppMenuItem { action: actQuit }
        }
        AppMenu {
            title: "Ver"
            AppMenuItem { action: actHome }
            AppMenuItem { action: actAlbums }
            AppMenuItem { action: actArtists }
            AppMenuItem { action: actReview }
            AppMenuItem { action: actPlaylists }
            AppMenuItem { action: actQueue }
            AppMenuItem { action: actLyrics }
            AppMenuSeparator { }
            AppMenuItem { action: actBack }
            AppMenuItem { action: actForward }
            AppMenuItem { action: actSearch }
        }
        AppMenu {
            title: "Reproducción"
            AppMenuItem { action: actPlay }
            AppMenuItem { action: actPrev }
            AppMenuItem { action: actNext }
            AppMenuSeparator { }
            AppMenuItem { action: actNewList }
            AppMenuItem { action: actClearList }
            AppMenuSeparator { }
            AppMenuItem { action: actShuffle }
            AppMenuItem { action: actRepeat }
            AppMenuSeparator { }
            AppMenuItem { action: actVolUp }
            AppMenuItem { action: actVolDown }
        }
        AppMenu {
            title: "Ayuda"
            AppMenuItem { action: actAbout }
        }
    }

    Action { id: actEditCurrent; text: "Editar tags de la pista actual\u2026"; shortcut: "Ctrl+E"; enabled: player.hasTrack; onTriggered: win.editTags([player.currentId]) }
    Action { id: actServers; text: "Servidores de letras y portadas\u2026"; onTriggered: serversDialog.openDialog() }
    Action { id: actHarvest; text: "Descargar portadas e informaci\u00f3n\u2026"; onTriggered: harvestDialog.offer(true) }
    Action { id: actExport; text: "Exportar biblioteca\u2026"; onTriggered: transfer.exportLibrary() }
    Action { id: actImport; text: "Importar biblioteca\u2026"; onTriggered: transfer.importLibrary() }
    Action { id: actReset; text: "Empezar desde cero\u2026"; onTriggered: transfer.resetLibrary() }
    Action { id: actInternet; text: "Internet\u2026"; onTriggered: win.openInternetSettings() }
    Action { id: actQuit; text: "Salir"; shortcut: "Ctrl+Q"; onTriggered: Qt.quit() }
    Action { id: actScan; text: "Buscar m\u00fasica\u2026"; shortcut: "Ctrl+Shift+O"; onTriggered: scanDialog.openDialog(false) }
    Action { id: actHome; text: "Inicio"; shortcut: "Ctrl+0"; onTriggered: win.showSection("home") }
    Action { id: actBack; text: "Atr\u00e1s"; shortcut: "Alt+Left"; enabled: win.canBack; onTriggered: win.back() }
    Shortcut { sequence: "Ctrl+["; enabled: win.canBack; onActivated: win.back() }
    Action { id: actForward; text: "Adelante"; shortcut: "Alt+Right"; enabled: win.canForward; onTriggered: win.forward() }
    Shortcut { sequence: "Ctrl+]"; enabled: win.canForward; onActivated: win.forward() }
    Action { id: actAlbums; text: "Álbumes"; shortcut: "Ctrl+1"; onTriggered: win.showSection("albums") }
    Action { id: actArtists; text: "Artistas"; shortcut: "Ctrl+2"; onTriggered: win.showSection("artists") }
    Action { id: actReview; text: "Por revisar"; shortcut: "Ctrl+3"; onTriggered: win.showSection("review") }
    Action { id: actPlaylists; text: "Listas de reproducci\u00f3n"; shortcut: "Ctrl+5"; onTriggered: win.showSection("playlists") }
    Action { id: actNewPlaylist; text: "Nueva lista de reproducci\u00f3n\u2026"; shortcut: "Ctrl+N"; onTriggered: win.newPlaylist() }
    Action { id: actLyrics; text: "Letra"; shortcut: "Ctrl+6"; onTriggered: win.toggleLyrics() }
    Action { id: actQueue; text: "Reproduciendo"; shortcut: "Ctrl+4"; onTriggered: win.showSection("queue") }
    Action { id: actNewList; text: "Nueva lista temporal"; onTriggered: player.newTemporaryList() }
    Action { id: actClearList; text: "Vaciar la lista actual"; enabled: player.queueLength > (player.hasTrack ? 1 : 0); onTriggered: player.clearQueue() }
    Action { id: actSearch; text: "Buscar"; shortcut: "Ctrl+F"; onTriggered: { searchField.forceActiveFocus(); searchField.selectAll() } }
    Action { id: actPlay; text: player.playing ? "Pausar" : "Reproducir"; shortcut: "Space"; enabled: player.hasTrack; onTriggered: player.toggle() }
    Action { id: actPrev; text: "Anterior"; shortcut: "Ctrl+Left"; enabled: player.hasTrack; onTriggered: player.previous() }
    Action { id: actNext; text: "Siguiente"; shortcut: "Ctrl+Right"; enabled: player.hasTrack; onTriggered: player.next() }
    Action { id: actShuffle; text: "Aleatorio: " + (player.shuffle ? "sí" : "no"); onTriggered: player.toggleShuffle() }
    Action {
        id: actRepeat
        text: "Repetir: " + (player.repeatMode === "all" ? "todo" : player.repeatMode === "one" ? "una" : "no")
        onTriggered: player.cycleRepeat()
    }
    Action { id: actVolUp; text: "Subir volumen"; shortcut: "Ctrl+Up"; onTriggered: player.setVolume(player.volume + 0.1) }
    Action { id: actVolDown; text: "Bajar volumen"; shortcut: "Ctrl+Down"; onTriggered: player.setVolume(player.volume - 0.1) }
    Action { id: actAbout; text: "Acerca de Sonoteca"; onTriggered: { win.aboutInfo = library.about(); aboutDialog.open() } }

    property var aboutInfo: ({})
    Popup {
        id: aboutDialog
        modal: true
        focus: true
        anchors.centerIn: Overlay.overlay
        width: 460
        padding: 24
        background: Rectangle { color: "#1d1d1f"; radius: 12; border.color: "#2e2e32"; border.width: 1 }
        Overlay.modal: Rectangle { color: "#99000000" }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
        exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }
        contentItem: Column {
            spacing: 10
            Text { text: "Sonoteca"; color: Theme.accent; font.pixelSize: 26; font.weight: Font.Bold }
            Text { text: "Versión " + (win.aboutInfo.version || ""); color: Theme.text; font.pixelSize: 14 }
            Text {
                width: parent.width
                text: "Reproductor y organizador de música local. Funciona sin conexión."
                color: Theme.textDim
                font.pixelSize: 13
                wrapMode: Text.WordWrap
            }
            Text { width: parent.width; text: "Base de datos: " + (win.aboutInfo.dbPath || ""); color: Theme.textDim; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
            Text { width: parent.width; text: "Copias de respaldo de tags: " + (win.aboutInfo.backupsDir || ""); color: Theme.textDim; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
            Text { width: parent.width; text: "Portadas guardadas: " + (win.aboutInfo.coversDir || ""); color: Theme.textDim; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
            Text { width: parent.width; text: "Caché de portadas: " + (win.aboutInfo.cacheDir || ""); color: Theme.textDim; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
            Chip { label: "Cerrar"; active: true; onClicked: aboutDialog.close() }
        }
    }

    property string section: "home"
    property bool firstRunPrompt: true   // con la biblioteca vacía, ofrece buscar la música al abrir
    Component.onCompleted: if (firstRunPrompt && library.stats().tracks === 0) scanDialog.openDialog(true)
    property bool searching: false
    property bool videoOpen: false
    property var stats: (Theme.dataRevision, library.stats())

    function cleanup() {   // quita lo que quedó sin canciones o sin archivo
        var r = library.cleanup()
        if (r.removed > 0 || r.pruned > 0) Theme.dataRevision++
    }
    // ---- Navegación con historial (atrás / adelante, como en un navegador) ----
    property var navHistory: [{ t: "section", sec: "home" }]
    property int navIndex: 0
    readonly property bool canBack: navIndex > 0
    readonly property bool canForward: navIndex < navHistory.length - 1

    function go(loc) {
        if (JSON.stringify(navHistory[navIndex]) === JSON.stringify(loc)) { render(loc); return }
        var h = navHistory.slice(0, navIndex + 1)   // lo que había "adelante" se descarta
        h.push(loc)
        if (h.length > 60) h = h.slice(h.length - 60)
        navHistory = h
        navIndex = h.length - 1
        render(loc)
    }
    function replaceCurrent(loc) {
        var h = navHistory.slice()
        h[navIndex] = loc
        navHistory = h
        render(loc)
    }
    function valid(loc) {   // un álbum o lista que ya no existe se salta al navegar
        if (loc.t === "album") return !!library.album(loc.id).id
        if (loc.t === "playlist") return !!playlists.info(loc.id).id
        return true
    }
    function step(dir) {
        var i = navIndex + dir
        while (i >= 0 && i < navHistory.length && !valid(navHistory[i])) i += dir
        if (i < 0 || i >= navHistory.length) return
        navIndex = i
        render(navHistory[i])
    }
    function back() { step(-1) }
    function forward() { step(1) }
    function render(loc) {
        searching = (loc.t === "search")
        if (loc.t === "section") {
            if (loc.sec === "albums" || loc.sec === "artists" || loc.sec === "review") cleanup()
            section = loc.sec
            searchField.text = ""
            if (loc.sec === "home") stack.replace(null, homeComp)
            else if (loc.sec === "albums") stack.replace(null, albumsComp)
            else if (loc.sec === "artists") stack.replace(null, artistsComp)
            else if (loc.sec === "queue") stack.replace(null, queueComp)
            else if (loc.sec === "playlists") stack.replace(null, playlistsComp)
            else if (loc.sec === "lyrics") stack.replace(null, lyricsComp)
            else stack.replace(null, reviewComp)
            return
        }
        if (loc.t === "search") {
            stack.replace(null, searchComp, { query: loc.q })
            if (searchField.text.trim() !== loc.q) searchField.text = loc.q
            return
        }
        if (loc.from) section = loc.from
        if (loc.t === "album") stack.replace(null, albumComp, { albumId: loc.id })
        else if (loc.t === "artist") stack.replace(null, albumsComp, { artistId: loc.id, heading: loc.name })
        else if (loc.t === "playlist") stack.replace(null, playlistComp, { playlistId: loc.id })
        else if (loc.t === "lyrics") stack.replace(null, lyricsComp, { followPlayer: false, trackId: loc.trackId })
    }
    // «Letra»: con una canción sonando se abre en un panel a la derecha (el centro queda libre);
    // sin canción, página completa que explica qué hacer.
    property bool lyricsPanelOpen: false
    readonly property bool lyricsPanelShown: lyricsPanelOpen && player.hasTrack && section !== "lyrics"
    function toggleLyrics() {
        if (player.hasTrack) lyricsPanelOpen = !lyricsPanelShown
        else showSection("lyrics")
    }
    function showSection(sec) { go({ t: "section", sec: sec }) }
    function showLyrics(trackId) { go({ t: "lyrics", trackId: trackId, from: section }) }
    function openAlbum(id) { go({ t: "album", id: id, from: section }) }
    function openArtist(id, name) { go({ t: "artist", id: id, name: name, from: section }) }
    function runSearch(q) {
        if (q.length < 2) {
            if (searching) showSection(section)
            return
        }
        if (searching) {   // misma página de búsqueda: solo cambia el texto, sin llenar el historial
            var h = navHistory.slice()
            h[navIndex] = { t: "search", q: q }
            navHistory = h
            stack.currentItem.query = q
        } else {
            go({ t: "search", q: q })
        }
    }
    function openInternetSettings() { onlineSettings.openDialog() }
    function lookupAlbum(albumId, ids, unknownAlbum) {
        if (online.offline) {
            win.toast("Activa internet para buscar portadas e información.")
            onlineSettings.openDialog()
            return
        }
        albumLookup.openFor(albumId, ids, unknownAlbum)
    }
    function openPlaylist(id) { go({ t: "playlist", id: id, from: section }) }
    function newPlaylist() {
        namePrompt.ask("Nueva lista de reproducci\u00f3n", "", "Crear", function (name) {
            var r = playlists.create(name)
            return r.ok ? "" : r.error
        })
    }
    function renamePlaylist(id, current) {
        namePrompt.ask("Renombrar lista", current, "Guardar", function (name) {
            var r = playlists.rename(id, name)
            return r.ok ? "" : r.error
        })
    }
    function deletePlaylist(id, name) {
        confirmDialog.ask("Eliminar lista", "Se eliminar\u00e1 \u00ab" + name + "\u00bb. Las canciones no se borran de tu biblioteca.", "Eliminar", function () {
            playlists.remove(id)
            if (stack.currentItem && stack.currentItem.playlistId === id) win.back()
        })
    }
    function saveQueueAsPlaylist() {
        var queued = player.queueTrackIds()
        if (queued.length === 0) return
        namePrompt.ask("Guardar la lista actual como lista", "", "Guardar", function (name) {
            var r = playlists.createWithTracks(name, queued)
            return r.ok ? "" : r.error
        })
    }
    function showPlaylistPicker(ids) { playlistPicker.openFor(ids) }
    function pickerNewList(ids) {
        namePrompt.ask("Nueva lista de reproducci\u00f3n", "", "Crear y agregar", function (name) {
            var r = playlists.createWithTracks(name, ids)
            return r.ok ? "" : r.error
        })
    }
    function showTrackMenu(ids) {
        trackMenu.ids = ids
        trackMenu.popup()
    }
    function editTags(ids) {
        if (ids.length > 0) tagEditor.openFor(ids, 0, "")
    }
    function editArtistTags(artistId, name) {
        var ids = library.artistTrackIds(artistId)
        if (ids.length > 0) tagEditor.openFor(ids, artistId, name)
    }
    function clearSearch() {
        searchField.text = ""
        searchField.forceActiveFocus()
    }
    function rescanReview(page) {
        page.rescanning = true
        win.reviewTarget = page
        library.rescanReview()
    }
    property var reviewTarget: null
    function dismissReview(n) {
        confirmDialog.ask("Vaciar «Por revisar»", "Se quitar\u00e1n " + Theme.plural(n, "pista", "pistas") + " de esta lista. No se modifica ning\u00fan archivo ni tag y siguen en tu biblioteca; podr\u00e1s restaurarlas con \u00abRestaurar descartadas\u00bb.", "Vaciar lista", function () {
            var removed = library.dismissReview()
            Theme.dataRevision++
            toast("Lista vaciada (" + Theme.plural(removed, "pista", "pistas") + ")", 3500)
        })
    }
    function restoreReview() {
        var n = library.restoreDismissed()
        Theme.dataRevision++
        toast(n + " restauradas; las que sigan incompletas vuelven a la lista", 3500)
    }
    function toast(msg, ms) {
        toastText.text = msg
        toastBox.opacity = 1
        toastTimer.interval = ms || 2600
        toastTimer.restart()
    }
    // "3 archivos actualizados" / con fallos: indica el primero
    function editSummary(result) {
        var n = result.updated || 0
        var failed = result.failed || []
        var first = failed.length > 0 ? failed[0] : null
        var detail = ""
        if (first) {
            var name = first.path ? first.path.split(/[\\/]/).pop() + " \u2014 " : ""
            detail = name + first.message
        }
        if (n === 0 && first) return "No se pudo actualizar ning\u00fan archivo: " + detail
        var text = n === 1 ? "1 archivo actualizado" : n + " archivos actualizados"
        if (first) text += " \u00b7 " + (failed.length === 1 ? "1 fall\u00f3" : failed.length + " fallaron") + ": " + detail
        return text
    }

    Component { id: homeComp; HomePage { onAlbumClicked: (id) => win.openAlbum(id); onArtistClicked: (id, name) => win.openArtist(id, name); onPlaylistClicked: (id) => win.openPlaylist(id); onMenuRequested: (ids) => win.showTrackMenu(ids) } }
    Component { id: albumsComp; AlbumsPage { onMenuRequested: (ids) => win.showTrackMenu(ids); onAlbumClicked: (id) => win.openAlbum(id); onNeedInternet: win.openInternetSettings(); onEditArtistRequested: (id, name) => win.editArtistTags(id, name) } }
    Component { id: albumComp; AlbumDetail { onEditRequested: (ids) => win.editTags(ids); onMenuRequested: (ids) => win.showTrackMenu(ids); onListRequested: (ids) => win.showPlaylistPicker(ids); onLookupRequested: (id, ids, unknown) => win.lookupAlbum(id, ids, unknown); onPlayOneRequested: (id) => queueChoice.ask(id); onArtistRequested: (id, name) => win.openArtist(id, name) } }
    Component { id: artistsComp; ArtistsPage { onArtistClicked: (id, name) => win.openArtist(id, name) } }
    Component {
        id: reviewComp
        TrackListPage {
            heading: "Por revisar"
            hint: "sin artista o álbum en los tags, o deducidos del nombre del archivo"
            id: reviewPage
            property bool rescanning: false
            property int dismissed: (Theme.dataRevision, library.dismissedCount())
            items: (Theme.dataRevision, library.incomplete())
            onEditRequested: (ids) => win.editTags(ids)
            onMenuRequested: (ids) => win.showTrackMenu(ids)
            actions: [
                PillButton {
                    label: reviewPage.rescanning ? "Re-escaneando\u2026" : "Re-escanear tags"
                    enabled: !reviewPage.rescanning && reviewPage.items.length > 0
                    onClicked: win.rescanReview(reviewPage)
                },
                PillButton {
                    label: "Vaciar lista"
                    enabled: reviewPage.items.length > 0
                    onClicked: win.dismissReview(reviewPage.items.length)
                },
                PillButton {
                    visible: reviewPage.dismissed > 0
                    label: "Restaurar descartadas (" + reviewPage.dismissed + ")"
                    onClicked: win.restoreReview()
                }
            ]
        }
    }
    Component {
        id: searchComp
        SearchPage {
            onAlbumClicked: (id) => win.openAlbum(id)
            onArtistClicked: (id, name) => win.openArtist(id, name)
            onEditRequested: (ids) => win.editTags(ids)
            onMenuRequested: (ids) => win.showTrackMenu(ids)
        }
    }
    Component {
        id: queueComp
        QueuePage {
            onEditRequested: (ids) => win.editTags(ids)
            onMenuRequested: (ids) => win.showTrackMenu(ids)
            onSaveRequested: win.saveQueueAsPlaylist()
        }
    }
    Component { id: lyricsComp; LyricsPage { onSettingsRequested: lyricsSettings.openDialog(); onNeedInternet: win.openInternetSettings() } }
    Component { id: playlistsComp; PlaylistsPage { onOpenPlaylist: (id) => win.openPlaylist(id); onNewRequested: win.newPlaylist() } }
    Component {
        id: playlistComp
        PlaylistDetail {
            onMenuRequested: (ids) => win.showTrackMenu(ids)
            onEditRequested: (ids) => win.editTags(ids)
            onRenameRequested: (id, name) => win.renamePlaylist(id, name)
            onDeleteRequested: (id, name) => win.deletePlaylist(id, name)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

        Rectangle {
            Layout.preferredWidth: 230
            Layout.fillHeight: true
            color: Theme.sidebar

            Column {
                anchors { left: parent.left; right: parent.right; top: parent.top; topMargin: 24 }
                spacing: 4
                Text {
                    text: "Sonoteca"
                    x: 24
                    color: Theme.accent
                    font.pixelSize: 22
                    font.weight: Font.Bold
                }
                Item { width: 1; height: 20 }
                SideButton {
                    width: parent.width
                    label: "Inicio"
                    active: win.section === "home"
                    onClicked: win.showSection("home")
                }
                SideButton {
                    width: parent.width
                    label: "Álbumes"
                    active: win.section === "albums"
                    onClicked: win.showSection("albums")
                }
                SideButton {
                    width: parent.width
                    label: "Artistas"
                    active: win.section === "artists"
                    onClicked: win.showSection("artists")
                }
                Item {
                    id: listsGroup
                    width: parent.width
                    property bool expanded: false
                    readonly property bool open: expanded || DragState.active   // al arrastrar se despliega para poder soltar
                    height: listsHead.height + (open ? listsBox.height : 0)
                    SideButton {
                        id: listsHead
                        width: parent.width
                        label: "Listas"
                        hint: playlists.count > 0 ? playlists.count : ""
                        active: win.section === "playlists"
                        onClicked: win.showSection("playlists")
                    }
                    Text {
                        id: listsChevron
                        text: listsGroup.open ? "\u25be" : "\u25b8"
                        color: Theme.textDim
                        font.pixelSize: 14
                        anchors { right: parent.right; rightMargin: 46; verticalCenter: listsHead.verticalCenter }
                        MouseArea {
                            anchors { fill: parent; margins: -10 }
                            cursorShape: Qt.PointingHandCursor
                            onClicked: listsGroup.expanded = !listsGroup.expanded
                        }
                    }
                    Flickable {
                        id: listsBox
                        visible: listsGroup.open
                        y: listsHead.height
                        width: parent.width
                        height: Math.min(contentHeight, 168)
                        contentHeight: listsCol.height
                        clip: true
                        Column {
                            id: listsCol
                            width: listsBox.width
                            Text {
                                visible: playlists.count === 0
                                x: 36
                                height: 32
                                verticalAlignment: Text.AlignVCenter
                                text: "A\u00fan no hay listas"
                                color: Theme.textDim
                                font.pixelSize: 12
                            }
                            Repeater {
                                model: (playlists.revision, playlists.lists())
                                delegate: Item {
                                    id: listItem
                                    width: listsCol.width
                                    height: 32
                                    readonly property bool dropHover: DragState.active && over(DragState.sceneX, DragState.sceneY)
                                    function over(x, y) {
                                        var p = listItem.mapFromItem(null, x, y)
                                        return p.x >= 0 && p.y >= 0 && p.x <= listItem.width && p.y <= listItem.height
                                    }
                                    onDropHoverChanged: {
                                        if (dropHover) DragState.hoverListId = modelData.id
                                        else if (DragState.hoverListId === modelData.id) DragState.hoverListId = 0
                                    }
                                    Rectangle {
                                        anchors { fill: parent; leftMargin: 20; rightMargin: 8 }
                                        radius: 6
                                        color: listItem.dropHover ? Qt.alpha(Theme.accent, 0.3) : (listMouse.containsMouse ? Theme.surfaceHover : "transparent")
                                        border.width: listItem.dropHover ? 1 : 0
                                        border.color: Theme.accent
                                    }
                                    Text {
                                        x: 36
                                        width: parent.width - 36 - 52
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.name
                                        color: listItem.dropHover ? Theme.text : Theme.textDim
                                        font.pixelSize: 13
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        anchors { right: parent.right; rightMargin: 20; verticalCenter: parent.verticalCenter }
                                        text: modelData.tracks
                                        color: Theme.textDim
                                        font.pixelSize: 11
                                    }
                                    MouseArea {
                                        id: listMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: win.openPlaylist(modelData.id)
                                    }
                                }
                            }
                        }
                    }
                }
                SideButton {
                    width: parent.width
                    label: "Reproduciendo"
                    hint: player.queueLength > 0 ? player.queueLength : ""
                    active: win.section === "queue"
                    onClicked: win.showSection("queue")
                }
                SideButton {
                    width: parent.width
                    label: "Letra"
                    active: win.section === "lyrics" || win.lyricsPanelShown
                    onClicked: win.toggleLyrics()
                }
                SideButton {
                    width: parent.width
                    label: "Por revisar"
                    hint: win.stats.incomplete > 0 ? win.stats.incomplete : ""
                    active: win.section === "review"
                    onClicked: win.showSection("review")
                }
            }
            Text {
                id: onlineBadge
                anchors { left: parent.left; bottom: statsText.top; leftMargin: 24; bottomMargin: 10 }
                text: online.offline ? "\u25cb Sin conexi\u00f3n" : "\u25cf En l\u00ednea"
                color: online.offline ? Theme.textDim : Theme.accent
                font.pixelSize: 12
                MouseArea {
                    id: badgeMouse
                    anchors { fill: parent; margins: -6 }
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: online.setOffline(!online.offline)
                    ToolTip.visible: containsMouse
                    ToolTip.delay: 400
                    ToolTip.text: online.offline ? "Clic para volver a modo en l\u00ednea" : "Clic para pasar a modo sin conexi\u00f3n"
                }
            }
            Text {
                id: statsText
                anchors { left: parent.left; bottom: parent.bottom; leftMargin: 24; bottomMargin: 20 }
                color: Theme.textDim
                font.pixelSize: 12
                lineHeight: 1.4
                text: win.stats.tracks + " pistas · " + win.stats.artists + " artistas\n"
                      + Theme.fmtLong(win.stats.seconds)
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 68

                Row {
                    id: navButtons
                    x: 24
                    spacing: 8
                    anchors.verticalCenter: parent.verticalCenter
                    Rectangle {
                        id: backBtn
                        width: 40; height: 40; radius: 20
                        opacity: win.canBack ? 1 : 0.35
                        color: backMouse.containsMouse && win.canBack ? Theme.surfaceHover : Theme.surface
                        Behavior on color { ColorAnimation { duration: Theme.fast } }
                        Text { anchors.centerIn: parent; text: "\u2039"; color: Theme.text; font.pixelSize: 28 }
                        MouseArea {
                            id: backMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: win.canBack
                            cursorShape: Qt.PointingHandCursor
                            onClicked: win.back()
                        }
                    }
                    Rectangle {
                        id: forwardBtn
                        width: 40; height: 40; radius: 20
                        opacity: win.canForward ? 1 : 0.35
                        color: forwardMouse.containsMouse && win.canForward ? Theme.surfaceHover : Theme.surface
                        Behavior on color { ColorAnimation { duration: Theme.fast } }
                        Text { anchors.centerIn: parent; text: "\u203a"; color: Theme.text; font.pixelSize: 28 }
                        MouseArea {
                            id: forwardMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: win.canForward
                            cursorShape: Qt.PointingHandCursor
                            onClicked: win.forward()
                        }
                    }
                }
                TextField {
                    id: searchField
                    anchors.verticalCenter: parent.verticalCenter
                    x: navButtons.x + navButtons.width + 16
                    width: Math.min(420, parent.width - x - 24)
                    implicitHeight: 40
                    placeholderText: "Buscar canción, artista o álbum"
                    placeholderTextColor: Theme.textDim
                    color: Theme.text
                    font.pixelSize: 14
                    leftPadding: 18
                    rightPadding: 44
                    Keys.onEscapePressed: win.clearSearch()
                    background: Rectangle {
                        radius: 20
                        color: searchField.activeFocus ? "#2e2e32" : Theme.surface
                        border.width: searchField.activeFocus ? 1 : 0
                        border.color: Theme.accent
                        Behavior on color { ColorAnimation { duration: Theme.fast } }
                    }
                    onTextChanged: debounce.restart()

                    // Botón "x" dentro del campo para limpiar la búsqueda
                    Item {
                        id: clearBtn
                        visible: searchField.text.length > 0
                        width: 28
                        height: 28
                        anchors { right: parent.right; rightMargin: 8; verticalCenter: parent.verticalCenter }
                        Rectangle {
                            anchors.fill: parent
                            radius: 14
                            color: clearMouse.containsMouse ? "#3a3a3e" : "transparent"
                            Behavior on color { ColorAnimation { duration: Theme.fast } }
                        }
                        Icon {
                            anchors.centerIn: parent
                            svg: Theme.iconClose
                            size: 14
                            color: clearMouse.containsMouse ? Theme.text : Theme.textDim
                        }
                        MouseArea {
                            id: clearMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: win.clearSearch()
                        }
                    }
                }
                Timer { id: debounce; interval: 160; onTriggered: win.runSearch(searchField.text.trim()) }
            }

            StackView {
                id: stack
                Layout.fillWidth: true
                Layout.fillHeight: true
                initialItem: homeComp

                pushEnter: Transition {
                    ParallelAnimation {
                        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 240 }
                        NumberAnimation { property: "x"; from: 48; to: 0; duration: 280; easing.type: Easing.OutCubic }
                    }
                }
                pushExit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 160 } }
                popEnter: Transition {
                    ParallelAnimation {
                        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 240 }
                        NumberAnimation { property: "x"; from: -48; to: 0; duration: 280; easing.type: Easing.OutCubic }
                    }
                }
                popExit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 160 } }
                replaceEnter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 240 } }
                replaceExit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }
            }
        }

        Rectangle {
            id: lyricsPanel
            readonly property int fullWidth: Math.round(Math.min(400, Math.max(300, win.width * 0.3)))
            Layout.preferredWidth: win.lyricsPanelShown ? fullWidth : 0
            Layout.fillHeight: true
            color: Theme.sidebar
            clip: true
            visible: Layout.preferredWidth > 0
            Behavior on Layout.preferredWidth { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
            Loader {
                active: win.lyricsPanelShown
                width: lyricsPanel.fullWidth
                height: parent.height
                sourceComponent: LyricsPage {
                    panel: true
                    autoSearch: true   // con internet, busca sola la letra de la canción que suena
                    onCloseRequested: win.lyricsPanelOpen = false
                    onSettingsRequested: lyricsSettings.openDialog()
                    onNeedInternet: win.openInternetSettings()
                }
            }
        }
        }

        PlayerBar {
            id: playerBar
            Layout.fillWidth: true
            Layout.preferredHeight: player.hasTrack ? 88 : 0
            visible: Layout.preferredHeight > 0
            videoOpen: win.videoOpen
            onVideoToggled: win.videoOpen = !win.videoOpen
            onArtistRequested: (id, name) => win.openArtist(id, name)
            onAlbumRequested: (id) => win.openAlbum(id)
            Behavior on Layout.preferredHeight { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
        }
    }

    // Video: cubre el área de contenido (a la derecha de la barra lateral)
    Rectangle {
        id: videoPane
        visible: player.isVideo && win.videoOpen
        color: "#000000"
        z: 5
        anchors { left: parent.left; leftMargin: 230; right: parent.right; rightMargin: lyricsPanel.visible ? lyricsPanel.width : 0; top: parent.top; topMargin: 68; bottom: parent.bottom; bottomMargin: playerBar.height }
        VideoOutput { id: videoOut; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit }
        Component.onCompleted: player.setVideoSink(videoOut.videoSink)
    }

    TagEditor { id: tagEditor }
    TrackMenu { id: trackMenu; onPlayOneRequested: (id) => queueChoice.ask(id); onArtistRequested: (id, name) => win.openArtist(id, name); onAlbumRequested: (id) => win.openAlbum(id); onLyricsRequested: (id) => win.showLyrics(id); onEditRequested: (ids) => win.editTags(ids); onListPickerRequested: (ids) => win.showPlaylistPicker(ids) }
    NamePrompt { id: namePrompt }
    ConfirmDialog { id: confirmDialog }
    QueueChoiceDialog { id: queueChoice }
    PlaylistPicker { id: playlistPicker; onNewRequested: (ids) => win.pickerNewList(ids) }
    Connections {
        target: playlists
        function onMessage(message) { win.toast(message, 3000) }
    }
    OnlineSettings { id: onlineSettings }
    LyricsSettings { id: lyricsSettings }
    ScanDialog {
        id: scanDialog
        onFinished: (added) => {
            Theme.dataRevision++
            win.cleanup()
            win.toast(added > 0 ? added + " canciones a\u00f1adidas" : "No hay canciones nuevas")
            if (added > 0) {
                win.showSection("home")
                harvestDialog.offer(false)   // portadas y fotos de lo bien identificado, avisando cu\u00e1nto tardar\u00e1
            }
        }
    }
    ServersDialog {
        id: serversDialog
        onToastRequested: (text) => win.toast(text, 4000)
    }
    HarvestDialog {
        id: harvestDialog
        onToastRequested: (text) => win.toast(text, 6000)
        onInternetRequested: win.openInternetSettings()
    }
    LibraryTransfer {
        id: transfer
        onToastRequested: (text, ms) => win.toast(text, ms)
    }
    AlbumLookup { id: albumLookup }

    Connections {
        target: online
        function onOnlineError(message) { if (!albumLookup.visible) win.toast(message, 6000) }
    }

    Connections {
        target: library
        function onEditProgress(done, total) {
            tagEditor.done = done
            tagEditor.total = total
        }
        function onRescanFinished(result) {
            if (win.reviewTarget) win.reviewTarget.rescanning = false
            Theme.dataRevision++
            if (result.error) { win.toast("No se pudo re-escanear: " + result.error, 6000); return }
            var msg = result.resolved + " de " + Theme.plural(result.total, "pista", "pistas") + " ya no necesitan revisi\u00f3n"
            if (result.missing > 0) msg += " \u00b7 " + Theme.plural(result.missing, "archivo ausente", "archivos ausentes")
            if (result.errors > 0) msg += " \u00b7 " + Theme.plural(result.errors, "error de lectura", "errores de lectura")
            win.toast(msg, 6000)
        }
        function onEditFinished(result) {
            tagEditor.close()      // sin ventana de resultado: solo un aviso breve
            tagEditor.step = 0
            win.toast(win.editSummary(result), (result.failed && result.failed.length > 0) ? 8000 : 3000)
            Theme.dataRevision++   // todas las páginas se vuelven a consultar
            player.refreshCurrent()   // la barra de reproducción muestra los tags nuevos
            // Si el álbum abierto cambió de identidad (p. ej. se renombró), seguir al nuevo
            var page = stack.currentItem
            if (page && page.albumId !== undefined && !library.album(page.albumId).id) {
                if (result.albumId) win.replaceCurrent({ t: "album", id: result.albumId, from: win.section })
                else win.back()
            }
        }
    }

    Connections {
        target: player
        function onCurrentChanged() { win.videoOpen = player.isVideo }
        function onQueueMessage(message) { win.toast(message, 3500) }
        function onErrorMessage(message) { win.toast(message) }
    }

    Connections {
        target: DragState
        function onDropOnList(listId, ids) {
            var r = playlists.addTracks(listId, ids)
            if (!r.ok) win.toast(r.error)
            else if (r.added === 0) win.toast("Esa canci\u00f3n ya estaba en la lista")
        }
    }
    Rectangle {   // etiqueta que sigue al puntero mientras se arrastra una canción
        id: dragGhost
        parent: Overlay.overlay
        z: 2000
        visible: DragState.active
        enabled: false
        x: DragState.sceneX + 14
        y: DragState.sceneY + 8
        width: Math.min(ghostText.implicitWidth + 24, 280)
        height: 30
        radius: 15
        color: Theme.surface
        border.color: Theme.accent
        border.width: 1
        opacity: 0.95
        Text {
            id: ghostText
            anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
            verticalAlignment: Text.AlignVCenter
            text: "\u266a " + DragState.label
            color: Theme.text
            font.pixelSize: 13
            elide: Text.ElideRight
        }
    }
    Rectangle {
        id: toastBox
        opacity: 0
        visible: opacity > 0
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 28 }
        width: toastText.width + 40
        height: toastText.height + 26
        radius: 16
        color: "#2e2e32"
        border.color: Theme.accent
        border.width: 1
        Behavior on opacity { NumberAnimation { duration: 220 } }
        Text {
            id: toastText
            anchors.centerIn: parent
            width: Math.min(implicitWidth, win.width - 200)
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            horizontalAlignment: Text.AlignHCenter
            color: Theme.text
            font.pixelSize: 14
        }
        Timer { id: toastTimer; interval: 2200; onTriggered: toastBox.opacity = 0 }
    }
}
