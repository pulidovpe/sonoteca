import QtQuick
import QtQuick.Controls
import "."

Item {
    id: page
    property int albumId
    property var info: (Theme.dataRevision, library.album(albumId))
    property var tracks: (Theme.dataRevision, library.tracks(albumId))
    signal editRequested(var ids)
    signal menuRequested(var ids)
    signal listRequested(var ids)
    signal newListRequested(var ids)
    signal removeRequested(var ids, string label, bool whole)   // quitar de la biblioteca (no toca los archivos)
    signal playOneRequested(int trackId)   // con una lista ya en marcha, Main pregunta qué hacer
    function addAllToQueue() { player.addToQueue(page.tracks.map(function (x) { return x.id })) }
    signal lookupRequested(int albumId, var ids, bool unknownAlbum)
    signal artistRequested(int artistId, string name)   // ir a la ficha del artista (con su descripción)
    // ¿Lo que suena ahora pertenece a este álbum?
    readonly property bool isCurrentAlbum: player.hasTrack && player.currentTrack.albumId === albumId
    // «Detener» mientras suena esta lista (la que se empezó desde esta página)
    readonly property string sourceKey: "album:" + albumId
    readonly property bool listPlaying: player.playing && player.sourceKey === sourceKey
    function trackIds() { return page.tracks.map(function (x) { return x.id }) }
    // Con Aleatorio activo, Reproducir empieza por una canción al azar. El botón Aleatorio solo reordena la lista de la derecha.
    function playOrStop() {
        if (listPlaying) player.stopPlayback()
        else if (player.shuffle) player.playShuffled(sourceKey, trackIds())
        else player.playFrom(sourceKey, trackIds(), 0)
    }
    function shuffleList() { player.toggleShuffle() }
    // «Quitar de la biblioteca»: con selección activa, solo las marcadas; si no, todo el álbum
    function requestRemove() {
        var ids = sel.active ? sel.ordered(trackIds()) : trackIds()
        if (ids.length === 0) return
        var whole = ids.length === page.tracks.length
        if (sel.active) sel.stop()
        removeRequested(ids, whole ? "El \u00e1lbum \u00ab" + (page.info.title || "") + "\u00bb (" + ids.length + " canciones)" : "", whole)
    }
    SelectionState { id: sel }          // «Seleccionar canciones»: elegir algunas para agregarlas a una lista

    Rectangle {
        id: hero
        height: 270
        anchors { left: parent.left; right: parent.right; top: parent.top }
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.heroTop }
            GradientStop { position: 1.0; color: Theme.bg }
        }
        Rectangle { id: artBg; x: 24; y: 40; width: 190; height: 190; radius: 6; color: Theme.placeholder }
        Image {
            anchors.fill: artBg
            source: "image://cover/" + page.albumId + "?v=" + Theme.dataRevision
            sourceSize.width: 640
            sourceSize.height: 640
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            opacity: status === Image.Ready ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.slow } }
        }
        Column {
            anchors.left: artBg.right
            anchors.leftMargin: 24
            anchors.right: parent.right
            anchors.rightMargin: 24
            anchors.verticalCenter: artBg.verticalCenter
            spacing: 8
            Text { text: "ÁLBUM"; color: Theme.textDim; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1.5 }
            Text {
                width: parent.width
                text: page.info.displayTitle || ""
                color: Theme.text
                font.pixelSize: 38
                font.weight: Font.Bold
                elide: Text.ElideRight
            }
            Text {
                id: infoLine
                width: parent.width
                color: Theme.textDim
                font.pixelSize: 14
                elide: Text.ElideRight
                text: (page.info.artist || "")
                      + (page.info.year > 0 ? " · " + page.info.year : "")
                      + " · " + Theme.plural(page.info.tracks || 0, "pista", "pistas") + ", " + Theme.fmtLong(page.info.duration || 0)
            }
            Flow {
                width: parent.width
                spacing: 12
            Rectangle {
                width: 150; height: 44; radius: 22
                color: playMouse.containsMouse ? Theme.accentHover : Theme.accent
                scale: playMouse.containsMouse ? 1.04 : 1.0
                Behavior on color { ColorAnimation { duration: Theme.fast } }
                Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
                Row {
                    anchors.centerIn: parent
                    spacing: 8
                    Icon { anchors.verticalCenter: parent.verticalCenter; svg: page.listPlaying ? Theme.iconStop : Theme.iconPlay; size: 18; color: Theme.textOnAccent }
                    Text { anchors.verticalCenter: parent.verticalCenter; text: page.listPlaying ? "Detener" : "Reproducir"; color: Theme.textOnAccent; font.pixelSize: 14; font.weight: Font.DemiBold }
                }
                MouseArea {
                    id: playMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: page.playOrStop()
                }
            }
            PillButton { height: 44; label: "Aleatorio"; primary: player.shuffle; onClicked: page.shuffleList() }
            PillButton { height: 44; label: "Ir al artista"; enabled: (page.info.artist_id || 0) > 0; onClicked: page.artistRequested(page.info.artist_id, page.info.artist || "") }
            PillButton { height: 44; label: "Agregar a la lista"; onClicked: page.addAllToQueue() }
            PillButton { height: 44; label: "Guardar en lista\u2026"; onClicked: page.listRequested(page.tracks.map(function (x) { return x.id })) }
            PillButton { height: 44; label: sel.active ? "Terminar selecci\u00f3n" : "Seleccionar canciones"; primary: sel.active; onClicked: sel.active ? sel.stop() : sel.start() }
            PillButton {
                id: removeButton
                height: 44
                label: sel.active ? "Quitar seleccionadas (" + sel.count + ") de la biblioteca\u2026" : "Quitar \u00e1lbum de la biblioteca\u2026"
                enabled: sel.active ? sel.count > 0 : page.tracks.length > 0
                onClicked: page.requestRemove()
            }
            PillButton {
                height: 44
                label: "Portada e info"
                onClicked: page.lookupRequested(page.albumId, page.tracks.map(function (x) { return x.id }), page.info.title === "\u00c1lbum desconocido")
            }
            PillButton { height: 44; label: "Editar tags"; onClicked: page.editRequested(page.tracks.map(function (x) { return x.id })) }
            }
        }
    }
    ColumnHeader {
        id: hdr
        hasNumber: true
        anchors { left: parent.left; right: parent.right; top: hero.bottom; topMargin: 8 }
    }
    readonly property var shown: (hdr.sortKey, hdr.sortAsc, player.statsRevision, hdr.sorted(page.tracks))
    ListView {
        id: list
        clip: true
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; top: hdr.bottom; bottomMargin: selBar.visible ? selBar.height : 0 }
        model: page.shown
        delegate: TrackRow {
            width: list.width
            number: modelData.number
            title: modelData.title
            artist: modelData.artist
            album: modelData.album
            year: modelData.year
            badge: modelData.badge
            duration: Theme.fmt(modelData.duration)
            plays: (player.statsRevision, player.playsOf(modelData.id))
            trackId: modelData.id
            current: player.currentId === modelData.id
            selectable: sel.active
            selected: (sel.picked, sel.has(modelData.id))
            onToggled: sel.toggle(modelData.id)
            onActivated: {
                page.playOneRequested(modelData.id)      // doble clic: solo esa canción entra en la lista de reproducción
            }
            onContextRequested: page.menuRequested([modelData.id])
        }
        add: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 240 } }
        ScrollBar.vertical: ScrollBar { }
    }
    SelectionBar {
        id: selBar
        visible: sel.active
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        count: sel.count
        total: page.tracks.length
        onSelectAllRequested: sel.all(page.trackIds())
        onClearRequested: sel.clear()
        onCancelRequested: sel.stop()
        onSaveRequested: { var ids = sel.ordered(page.trackIds()); sel.stop(); page.listRequested(ids) }
        onNewRequested: { var ids = sel.ordered(page.trackIds()); sel.stop(); page.newListRequested(ids) }
    }
}
