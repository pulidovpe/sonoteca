import QtQuick
import QtQuick.Controls
import "."

// Servidores alternativos para letras y para portadas/informaci\u00f3n, que se usan EN LUGAR del predeterminado.
Popup {
    id: root
    property string tab: "lyrics"          // lyrics | meta
    property var st: ({ lyrics: [], lyricsActive: "default", meta: [], metaActive: "default" })
    property string message: ""
    property bool messageOk: true
    property bool testing: false
    property alias nameField: lyricsName   // para las pruebas
    signal toastRequested(string text)

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(680, Overlay.overlay ? Overlay.overlay.width - 48 : 680)
    height: Math.min(640, Overlay.overlay ? Overlay.overlay.height - 48 : 640)
    padding: 24
    background: Rectangle { color: "#1d1d1f"; radius: 12; border.color: "#2e2e32"; border.width: 1 }
    Overlay.modal: Rectangle { color: "#99000000" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function openDialog() { refresh(); message = ""; open() }
    function refresh() { st = serverConfig.state() }
    function show(ok, text) { messageOk = ok; message = text }
    function apply(result, okText) {
        if (result.ok) { st = result.state; show(true, okText || "") }
        else show(false, result.error)
    }
    function addLyrics() {
        var r = serverConfig.addLyrics(lyricsName.text, lyricsUrl.text)
        apply(r, "Servidor agregado. Elige \u00abUsar\u00bb para activarlo.")
        if (r.ok) { lyricsName.text = ""; lyricsUrl.text = "" }
    }
    function addMeta() {
        var r = serverConfig.addMeta(metaName.text, mbUrl.text, caUrl.text, wikiUrl.text)
        apply(r, "Servidor agregado. Elige \u00abUsar\u00bb para activarlo.")
        if (r.ok) { metaName.text = ""; mbUrl.text = ""; caUrl.text = ""; wikiUrl.text = "" }
    }
    function use(kind, id) {
        var r = serverConfig.setActive(kind, id)
        apply(r, id === "default" ? "Se usa el servicio predeterminado." : "Servidor activado. Se usar\u00e1 desde la pr\u00f3xima consulta.")
    }
    function removeServer(kind, id) { apply(serverConfig.remove(kind, id), "Servidor eliminado.") }

    Connections {
        target: serverConfig
        function onTestFinished(r) { root.testing = false; root.show(r.ok, r.message) }
    }

    component Field: Rectangle {
        id: field
        property alias text: input.text
        property string placeholder: ""
        height: 36
        radius: 8
        color: "#141416"
        border.color: input.activeFocus ? Theme.accent : "#2e2e32"
        TextField {
            id: input
            anchors.fill: parent
            leftPadding: 10
            color: Theme.text
            font.pixelSize: 13
            selectByMouse: true
            background: null
            placeholderText: field.placeholder
            placeholderTextColor: Theme.textDim
        }
    }
    component ServerList: Column {
        id: list
        property string kind: "lyrics"
        property var items: []
        property string active: "default"
        width: parent.width
        spacing: 6
        Repeater {
            model: list.items
            delegate: Rectangle {
                required property var modelData
                width: list.width
                height: info.implicitHeight + 20
                radius: 8
                color: modelData.id === list.active ? "#1f2a22" : "#232327"
                border.color: modelData.id === list.active ? Theme.accent : "#2e2e32"
                Column {
                    id: info
                    anchors { left: parent.left; right: buttons.left; verticalCenter: parent.verticalCenter; leftMargin: 12; rightMargin: 8 }
                    spacing: 2
                    Text { width: parent.width; text: modelData.name; color: Theme.text; font.pixelSize: 14; font.weight: Font.Medium; elide: Text.ElideRight }
                    Text { width: parent.width; text: modelData.url; color: Theme.textDim; font.pixelSize: 11; elide: Text.ElideMiddle }
                }
                Row {
                    id: buttons
                    anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
                    spacing: 8
                    Text { visible: modelData.id === list.active; anchors.verticalCenter: parent.verticalCenter; text: "En uso"; color: Theme.accent; font.pixelSize: 12 }
                    PillButton { visible: modelData.id !== list.active; height: 30; label: "Usar"; onClicked: root.use(list.kind, modelData.id) }
                    PillButton { visible: !modelData.builtin; height: 30; label: "Eliminar"; onClicked: root.removeServer(list.kind, modelData.id) }
                }
            }
        }
    }

    contentItem: Column {
        spacing: 12
        Text { text: "Servidores de letras y portadas"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold; width: parent.width }
        Row {
            spacing: 8
            Chip { height: 30; label: "Letras"; active: root.tab === "lyrics"; onClicked: { root.tab = "lyrics"; root.message = "" } }
            Chip { height: 30; label: "Portadas e informaci\u00f3n"; active: root.tab === "meta"; onClicked: { root.tab = "meta"; root.message = "" } }
        }
        ScrollView {
            id: scroll
            width: parent.width
            height: root.height - 24 * 2 - 150
            clip: true
            contentWidth: availableWidth
            Column {
                width: scroll.availableWidth - 12
                spacing: 12

                // ---------------- Letras ----------------
                Column {
                    width: parent.width
                    spacing: 10
                    visible: root.tab === "lyrics"
                    Text {
                        width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 13
                        text: "Un servidor de letras alternativo se usa en lugar de LRCLIB. Debe ser compatible con la API de LRCLIB (por ejemplo, una instancia propia): la direcci\u00f3n es la ra\u00edz de la API, como https://mi-servidor/api."
                    }
                    ServerList { kind: "lyrics"; items: root.st.lyrics; active: root.st.lyricsActive }
                    Text { text: "Agregar servidor"; color: Theme.text; font.pixelSize: 14; font.weight: Font.Bold }
                    Field { id: lyricsName; width: parent.width; placeholder: "Nombre (p. ej. Mi servidor)" }
                    Field { id: lyricsUrl; width: parent.width; placeholder: "https://mi-servidor/api" }
                    Row {
                        spacing: 10
                        PillButton { label: root.testing ? "Probando\u2026" : "Probar"; enabled: !root.testing && lyricsUrl.text !== ""; onClicked: { root.testing = true; root.message = ""; serverConfig.testLyrics(lyricsUrl.text, "") } }
                        PillButton { id: addLyricsButton; label: "Agregar"; primary: true; onClicked: root.addLyrics() }
                    }
                }

                // ---------------- Portadas e informaci\u00f3n ----------------
                Column {
                    width: parent.width
                    spacing: 10
                    visible: root.tab === "meta"
                    Text {
                        width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 13
                        text: "Sustituye a MusicBrainz, Cover Art Archive y Wikipedia. Indica solo los que tengas: los que dejes vac\u00edos siguen usando el servicio predeterminado. Deben ser compatibles con la misma API (por ejemplo, un espejo propio)."
                    }
                    ServerList { kind: "meta"; items: root.st.meta; active: root.st.metaActive }
                    Text { text: "Agregar servidor"; color: Theme.text; font.pixelSize: 14; font.weight: Font.Bold }
                    Field { id: metaName; width: parent.width; placeholder: "Nombre (p. ej. Mi espejo)" }
                    Field { id: mbUrl; width: parent.width; placeholder: "MusicBrainz: https://mi-espejo/ws/2  (opcional)" }
                    Field { id: caUrl; width: parent.width; placeholder: "Cover Art Archive: https://mi-espejo-caa  (opcional)" }
                    Field { id: wikiUrl; width: parent.width; placeholder: "Wikipedia: https://{lang}.mi-wiki.org  (opcional; {lang} = idioma)" }
                    Row {
                        spacing: 10
                        PillButton { label: root.testing ? "Probando\u2026" : "Probar"; enabled: !root.testing && (mbUrl.text !== "" || wikiUrl.text !== ""); onClicked: { root.testing = true; root.message = ""; serverConfig.testMeta(mbUrl.text, wikiUrl.text) } }
                        PillButton { id: addMetaButton; label: "Agregar"; primary: true; onClicked: root.addMeta() }
                    }
                }
            }
        }
        Text {
            visible: root.message !== ""
            width: parent.width
            wrapMode: Text.WordWrap
            color: root.messageOk ? Theme.accent : "#e5736b"
            font.pixelSize: 13
            text: root.message
        }
        Row {
            anchors.right: parent.right
            PillButton { label: "Cerrar"; primary: true; onClicked: root.close() }
        }
    }
}
