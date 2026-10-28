import QtQuick
import QtQuick.Controls
import "."

// Ficha del artista: resumen de Wikipedia y foto (se guardan para verlos sin conexión)
Item {
    id: root
    property int artistId: 0
    property string artistName: ""
    property var info: ({})
    property string status: ""
    property bool searching: false
    property bool expanded: false
    signal needInternet()
    implicitHeight: Math.max(photo.height, body.height) + 8

    function reload() { info = online.storedArtistInfo(artistId) }
    function search() {
        if (online.offline) { needInternet(); return }
        searching = true
        status = "Consultando\u2026"
        online.requestArtistInfo(artistId, !!info.bio)
    }
    onArtistIdChanged: { expanded = false; status = ""; reload() }
    Component.onCompleted: reload()

    Connections {
        target: Theme
        function onDataRevisionChanged() { root.reload() }
    }
    Connections {
        target: online
        function onProgress(message) { if (root.searching) root.status = message }
        function onArtistInfoReady(id, data) {
            if (id !== root.artistId) return
            root.searching = false
            // la foto nueva se usa en las tarjetas de la sección Artistas: obliga a recargarlas
            // (primero, porque cada revisión vuelve a leer la ficha guardada)
            if (data.imagePath) Theme.dataRevision++
            root.info = data
            root.status = data.bio ? "" : "No se encontró información fiable de este artista."
        }
        function onOnlineError(message) {
            if (root.searching) { root.searching = false; root.status = message }
        }
    }

    Rectangle {
        id: photo
        visible: !!root.info.imagePath
        width: visible ? 120 : 0
        height: visible ? 120 : 0
        radius: 8
        color: "#222224"
        Image {
            anchors.fill: parent
            source: root.info.imagePath ? online.fileUrl(root.info.imagePath) : ""
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
        }
    }
    Column {
        id: body
        anchors { left: photo.right; leftMargin: photo.visible ? 20 : 0; right: parent.right }
        spacing: 8
        Text {
            width: parent.width
            visible: !!root.info.bio
            text: root.info.bio || ""
            color: "#d0d0d4"
            font.pixelSize: 13
            lineHeight: 1.25
            wrapMode: Text.WordWrap
            maximumLineCount: root.expanded ? 1000 : 4
            elide: Text.ElideRight
        }
        Row {
            spacing: 16
            visible: !!root.info.bio
            Text {
                visible: (root.info.bio || "").length > 280
                text: root.expanded ? "Ver menos" : "Ver más"
                color: Theme.text
                font.pixelSize: 12
                font.weight: Font.DemiBold
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.expanded = !root.expanded }
            }
            Text {
                visible: root.info.source !== "Manual"
                text: "Fuente: " + (root.info.source || "Wikipedia") + (root.info.lang ? " (" + root.info.lang + ")" : "") + " \u00b7 licencia CC BY-SA"
                color: Theme.accent
                font.pixelSize: 12
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: if (root.info.url) Qt.openUrlExternally(root.info.url)
                }
            }
        }
        Text { width: parent.width; visible: root.status !== ""; text: root.status; color: Theme.textDim; font.pixelSize: 12; wrapMode: Text.WordWrap }
        Row {
            spacing: 10
            PillButton {
                height: 32
                enabled: !root.searching
                label: root.searching ? "Buscando\u2026" : (root.info.bio ? "Actualizar información" : "Buscar información en internet")
                onClicked: root.search()
            }
            PillButton {
                id: lookupButton
                height: 32
                enabled: !root.searching
                label: "¿Artista equivocado?"
                onClicked: lookup.openFor(root.artistId, root.artistName, root.info.source === "Manual" ? root.info.bio : "")
            }
        }
    }
    ArtistLookup {
        id: lookup
        onApplied: { Theme.dataRevision++; root.reload() }
    }
}
