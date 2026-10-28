import QtQuick
import QtQuick.Controls
import "."

// Letra de una canción. Si está sincronizada se resalta la línea que suena (y un clic en una línea
// salta a ese momento); si no, se muestra como texto. Admite traducción (original / traducción / ambas).
Item {
    id: page
    property bool followPlayer: true   // true: la pista que suena; false: la pista `trackId`
    property int trackId: 0
    readonly property int shownId: followPlayer ? player.currentId : trackId
    readonly property bool playingThis: player.hasTrack && player.currentId === shownId
    property var doc: ({})
    property var info: ({})
    property var times: []
    property string viewMode: "both"   // preferencia del usuario: original | translation | both
    property string status: ""
    property bool panel: false   // true: panel lateral (más estrecho, con botón de cerrar)
    readonly property int pad: panel ? 16 : 24
    signal closeRequested()
    signal settingsRequested()
    signal needInternet()
    // Para las pruebas
    property alias listItem: list
    property alias searchButton: searchButton

    readonly property bool hasTranslation: doc.hasTranslation === true
    readonly property string mode: hasTranslation ? viewMode : "original"
    property int activeIndex: (doc.synced === true && playingThis) ? indexFor(player.position) : -1
    readonly property string emptyMessage: {
        if (shownId <= 0) return "Reproduce una canci\u00f3n para ver su letra."
        if (lyrics.busy) return ""
        if (!doc.stored) return online.offline
            ? "Todav\u00eda no se ha buscado la letra de esta canci\u00f3n. Activa internet para buscarla."
            : "Todav\u00eda no se ha buscado la letra de esta canci\u00f3n."
        if (doc.instrumental) return "Esta pista es instrumental."
        if (!doc.found) return "No se encontr\u00f3 la letra de esta canci\u00f3n en LRCLIB."
        return ""
    }

    function indexFor(ms) {       // búsqueda binaria: última línea cuyo tiempo ya pasó
        var lo = 0, hi = times.length - 1, ans = -1
        while (lo <= hi) {
            var mid = (lo + hi) >> 1
            if (times[mid] <= ms) { ans = mid; lo = mid + 1 } else { hi = mid - 1 }
        }
        return ans
    }
    function applyDoc(d) {
        var t = []
        var ls = d.lines || []
        for (var i = 0; i < ls.length; i++) t.push(ls[i].t)
        times = t
        doc = d
    }
    function reload() {
        status = ""
        info = shownId > 0 ? library.trackInfo(shownId) : ({})
        applyDoc(shownId > 0 ? lyrics.stored(shownId) : ({}))
    }
    function search(force) {
        if (online.offline) { needInternet(); return }
        status = ""
        lyrics.request(shownId, force)
    }
    function translate() {
        if (!lyrics.hasKey) { settingsRequested(); return }
        if (online.offline) { needInternet(); return }
        status = ""
        lyrics.translate(shownId, false)
    }

    onShownIdChanged: reload()
    onActiveIndexChanged: list.currentIndex = activeIndex
    Component.onCompleted: reload()

    Connections {
        target: lyrics
        function onLyricsReady(id, d) {
            if (id !== page.shownId) return
            page.status = ""
            page.applyDoc(d)
        }
        function onLyricsError(message) { page.status = message }
        function onProgress(message) { page.status = message }
        function onLangChanged() { page.reload() }   // otro idioma: la traducción guardada puede ser otra
    }
    Connections {
        target: Theme
        function onDataRevisionChanged() { page.reload() }   // p. ej. tras editar los tags
    }

    Text {
        id: title
        text: "Letra"
        color: Theme.text
        font.pixelSize: page.panel ? 22 : 30
        font.weight: Font.Bold
        anchors { left: parent.left; top: parent.top; leftMargin: page.pad; topMargin: 8 }
    }
    IconButton {
        id: closeButton
        visible: page.panel
        svg: Theme.iconClose
        iconSize: 14
        anchors { right: parent.right; rightMargin: 8; verticalCenter: title.verticalCenter }
        onClicked: page.closeRequested()
    }
    Text {
        id: sub
        visible: !!page.info.title
        text: (page.info.artist || "") + " \u2014 " + (page.info.title || "")
        color: Theme.textDim
        font.pixelSize: 13
        elide: Text.ElideRight
        anchors { left: parent.left; right: parent.right; top: title.bottom; leftMargin: page.pad; rightMargin: page.pad; topMargin: 2 }
    }
    Flow {
        id: actions
        spacing: 8
        visible: page.shownId > 0
        anchors { left: parent.left; right: parent.right; top: sub.visible ? sub.bottom : title.bottom; leftMargin: page.pad; rightMargin: page.pad; topMargin: 12 }
        PillButton {
            id: searchButton
            height: 34
            enabled: !lyrics.busy
            primary: !page.doc.stored
            label: !page.doc.stored ? "Buscar letra" : (page.doc.found ? "Actualizar letra" : "Buscar de nuevo")
            onClicked: page.search(page.doc.stored === true)
        }
        PillButton {
            id: translateButton
            height: 34
            visible: page.doc.found === true && page.doc.instrumental !== true && !page.hasTranslation
            enabled: !lyrics.busy
            label: "Traducir a " + lyrics.translateLang
            onClicked: page.translate()
        }
        Chip { visible: page.hasTranslation; label: "Original"; active: page.mode === "original"; onClicked: page.viewMode = "original" }
        Chip { visible: page.hasTranslation; label: "Traducci\u00f3n"; active: page.mode === "translation"; onClicked: page.viewMode = "translation" }
        Chip { visible: page.hasTranslation; label: "Ambas"; active: page.mode === "both"; onClicked: page.viewMode = "both" }
        PillButton {
            height: 34
            visible: page.doc.found === true
            label: "Ajustes de traducci\u00f3n"
            onClicked: page.settingsRequested()
        }
    }
    Text {
        id: statusText
        visible: page.status !== ""
        width: parent.width - 2 * page.pad
        x: page.pad
        anchors.top: actions.visible ? actions.bottom : sub.bottom
        anchors.topMargin: 8
        text: page.status
        color: Theme.textDim
        font.pixelSize: 12
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
    }
    Text {
        id: note
        visible: page.doc.found === true && page.doc.instrumental !== true
        width: parent.width - 2 * page.pad
        x: page.pad
        anchors.top: statusText.visible ? statusText.bottom : (actions.visible ? actions.bottom : sub.bottom)
        anchors.topMargin: 8
        text: "Fuente: " + (page.doc.source || "LRCLIB") + (page.doc.synced ? " \u00b7 sincronizada" : " \u00b7 sin sincronizar")
              + (page.doc.language ? " \u00b7 idioma original: " + page.doc.language : "")
              + " \u00b7 las letras tienen copyright: uso personal"
        color: Theme.textDim
        font.pixelSize: 11
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
    }

    ListView {
        id: list
        clip: true
        model: page.doc.lines || []
        anchors {
            left: parent.left; right: parent.right; bottom: parent.bottom
            top: note.visible ? note.bottom : (statusText.visible ? statusText.bottom : (actions.visible ? actions.bottom : sub.bottom))
            leftMargin: page.pad; rightMargin: page.pad; topMargin: 12
        }
        // La línea que suena se mantiene en la zona alta-media; el usuario puede desplazarse libremente
        highlightRangeMode: ListView.ApplyRange
        preferredHighlightBegin: height * 0.25
        preferredHighlightEnd: height * 0.5
        highlightMoveDuration: 350
        highlight: Item { }
        Connections {
            target: list
            function onCountChanged() { list.currentIndex = page.activeIndex }
        }
        delegate: Item {
            id: row
            width: list.width
            height: body.height + (modelData.text === "" ? 10 : 14)
            readonly property bool active: index === page.activeIndex
            readonly property bool synced: page.doc.synced === true
            readonly property string original: modelData.text
            readonly property string translated: modelData.tr
            Column {
                id: body
                width: parent.width
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    width: parent.width
                    visible: text !== ""
                    text: page.mode === "translation" && row.translated !== "" ? row.translated : row.original
                    color: !row.synced || row.active ? Theme.text : "#6f6f74"
                    font.pixelSize: page.panel ? (row.active ? 20 : 16) : (row.active ? 24 : 20)
                    font.weight: row.active ? Font.Bold : Font.DemiBold
                    wrapMode: Text.WordWrap
                    Behavior on font.pixelSize { NumberAnimation { duration: Theme.fast } }
                }
                Text {
                    width: parent.width
                    visible: page.mode === "both" && row.translated !== ""
                    text: row.translated
                    color: row.active ? Theme.accent : Theme.textDim
                    font.pixelSize: 15
                    wrapMode: Text.WordWrap
                }
            }
            MouseArea {
                anchors.fill: parent
                enabled: row.synced && page.playingThis && modelData.t >= 0
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: player.seek(modelData.t)
            }
        }
    }
    Text {
        anchors.centerIn: list
        width: Math.min(list.width, 460)
        visible: page.emptyMessage !== "" && list.count === 0
        text: page.emptyMessage
        color: Theme.textDim
        font.pixelSize: 15
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
    }
}
