import QtQuick
import QtQuick.Controls
import "."

// Duplicados: mismo artista, título, duración, nombre de archivo y tamaño. En cada grupo se conserva UNA copia (la mejor,
// por defecto) y las demás van a la papelera, por lotes. Antes de mover nada se verifica que el contenido sea idéntico.
Popup {
    id: root
    property var groups: []              // [{title, items: [...], keepId, include}]
    property string stage: "select"      // select | confirm | running | done
    property var result: ({})
    property int done: 0
    property int total: 0
    signal finished(var result)
    property alias deleteButton: deleteButton

    readonly property int removeCount: {
        var n = 0
        for (var i = 0; i < groups.length; i++) if (groups[i].include) n += groups[i].items.length - 1
        return n
    }
    readonly property real removeBytes: {
        var bytes = 0
        for (var i = 0; i < groups.length; i++) {
            var g = groups[i]
            if (!g.include) continue
            for (var k = 0; k < g.items.length; k++) if (g.items[k].id !== g.keepId) bytes += g.items[k].size
        }
        return bytes
    }

    modal: true
    focus: true
    closePolicy: stage === "running" ? Popup.NoAutoClose : Popup.CloseOnEscape
    anchors.centerIn: Overlay.overlay
    width: Math.min(760, Overlay.overlay ? Overlay.overlay.width - 48 : 760)
    height: Math.min(620, Overlay.overlay ? Overlay.overlay.height - 48 : 620)
    padding: 24
    background: Rectangle { color: Theme.panel; radius: 12; border.color: Theme.border; border.width: 1 }
    Overlay.modal: Rectangle { color: Theme.scrim }

    function mb(bytes) { return (bytes / 1048576).toFixed(1) + " MB" }
    function openDialog() {
        var raw = library.duplicateGroups()
        groups = raw.map(function (g) { return { title: g.title, items: g.items, keepId: g.items[0].id, include: true } })
        stage = "select"
        open()
    }
    function setKeep(index, id) { var copy = groups.slice(); copy[index].keepId = id; groups = copy }
    function toggleInclude(index) { var copy = groups.slice(); copy[index].include = !copy[index].include; groups = copy }
    function plan() {
        var out = []
        for (var i = 0; i < groups.length; i++) {
            var g = groups[i]
            if (!g.include) continue
            var remove = []
            for (var k = 0; k < g.items.length; k++) if (g.items[k].id !== g.keepId) remove.push(g.items[k].id)
            out.push({ keep: g.keepId, remove: remove })
        }
        return out
    }
    function start() {
        var p = plan(), ids = []
        for (var i = 0; i < p.length; i++) ids = ids.concat(p[i].remove)
        done = 0
        total = ids.length
        stage = "running"
        player.forgetTracks(ids)          // lo que suena o está en la lista deja de apuntar a archivos que se van a eliminar
        library.deleteDuplicates(p)
    }

    Connections {
        target: library
        function onDuplicatesProgress(d, t) { root.done = d; root.total = t }
        function onDuplicatesDeleted(r) { root.result = r; root.stage = "done"; root.finished(r) }
    }

    contentItem: Column {
        spacing: 12
        Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold
               text: root.stage === "done" ? "Duplicados eliminados" : "Duplicados" }

        // ---- elegir ----
        Column {
            width: parent.width
            spacing: 10
            visible: root.stage === "select"
            Text {
                width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 13
                text: root.groups.length === 0
                      ? "No hay duplicados: ninguna pareja de archivos coincide a la vez en artista, título, duraci\u00f3n, nombre de archivo y tama\u00f1o."
                      : "Archivos que coinciden en artista, t\u00edtulo, duraci\u00f3n, nombre de archivo y tama\u00f1o. Elige la copia que se conserva en cada grupo (por defecto, la de mejores tags, portada y bitrate); las dem\u00e1s ir\u00e1n a la papelera."
            }
            ScrollView {
                id: scroll
                width: parent.width
                height: root.height - 24 * 2 - 190
                clip: true
                contentWidth: availableWidth
                visible: root.groups.length > 0
                Column {
                    width: scroll.availableWidth - 12
                    spacing: 10
                    Repeater {
                        model: root.groups
                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            id: groupBox
                            readonly property int gi: index       // el Repeater interior tiene su propio «index»
                            width: parent.width
                            height: groupColumn.implicitHeight + 20
                            radius: 8
                            color: Theme.surface
                            border.color: modelData.include ? Theme.accent : Theme.border
                            Column {
                                id: groupColumn
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                                spacing: 6
                                Row {
                                    width: parent.width
                                    Text { width: parent.width - includeChip.width; text: modelData.title; color: Theme.text; font.pixelSize: 14; font.weight: Font.Medium; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                                    Chip { id: includeChip; height: 26; label: modelData.include ? "Incluido" : "Omitido"; active: modelData.include; onClicked: root.toggleInclude(groupBox.gi) }
                                }
                                Repeater {
                                    model: modelData.items
                                    delegate: Item {
                                        required property var modelData
                                        width: groupColumn.width
                                        height: 26
                                        readonly property bool kept: modelData.id === root.groups[groupBox.gi].keepId
                                        Rectangle {
                                            id: radio
                                            width: 14; height: 14; radius: 7
                                            anchors.verticalCenter: parent.verticalCenter
                                            color: "transparent"
                                            border.color: parent.kept ? Theme.accent : Theme.textFaint
                                            Rectangle { anchors.centerIn: parent; width: 8; height: 8; radius: 4; color: Theme.accent; visible: parent.parent.kept }
                                        }
                                        Text {
                                            anchors { left: radio.right; leftMargin: 8; right: tag.left; rightMargin: 8; verticalCenter: parent.verticalCenter }
                                            text: modelData.path
                                            color: parent.kept ? Theme.text : Theme.textDim
                                            font.pixelSize: 12
                                            elide: Text.ElideMiddle
                                        }
                                        Text {
                                            id: tag
                                            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                                            text: (parent.kept ? "Se conserva  \u00b7  " : "A la papelera  \u00b7  ") + root.mb(modelData.size) + (modelData.bitrate ? "  \u00b7  " + modelData.bitrate + " kbps" : "")
                                            color: parent.kept ? Theme.accent : Theme.textFaint
                                            font.pixelSize: 11
                                        }
                                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.setKeep(groupBox.gi, modelData.id) }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ---- confirmar ----
        Column {
            width: parent.width
            spacing: 10
            visible: root.stage === "confirm"
            Rectangle {
                width: parent.width; height: warn.implicitHeight + 20; radius: 8; color: Theme.warnBg; border.color: Theme.warnBorder
                Text {
                    id: warn
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 12 }
                    wrapMode: Text.WordWrap; color: Theme.warn; font.pixelSize: 13
                    text: "Se mover\u00e1n " + root.removeCount + " archivos (" + root.mb(root.removeBytes) + ") a la papelera del sistema y se quitar\u00e1n de la biblioteca. Antes se verifica que cada copia sea id\u00e9ntica a la que se conserva; las que no lo sean se dejan intactas. Podr\u00e1s recuperarlas desde la papelera."
                }
            }
        }

        // ---- en curso / resumen ----
        Column {
            width: parent.width
            spacing: 8
            visible: root.stage === "running"
            Rectangle { width: parent.width; height: 8; radius: 4; color: Theme.track
                Rectangle { height: parent.height; radius: 4; color: Theme.accent; width: root.total > 0 ? parent.width * Math.min(1, root.done / root.total) : 0 } }
            Text { width: parent.width; color: Theme.text; font.pixelSize: 14; text: root.done + " de " + root.total + " (se verifica el contenido de cada archivo)" }
        }
        Column {
            width: parent.width
            spacing: 6
            visible: root.stage === "done"
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.text; font.pixelSize: 14
                   text: root.result.error ? ("No se pudo completar: " + root.result.error)
                         : ((root.result.deleted ? root.result.deleted.length : 0) + " archivos movidos a la papelera (" + root.mb(root.result.bytes || 0) + " liberados).") }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.warn; font.pixelSize: 13
                   visible: !!root.result.skipped && root.result.skipped.length > 0
                   text: root.result.skipped ? (root.result.skipped.length + " no se eliminaron: " + root.result.skipped.slice(0, 4).map(function (s) { return s.reason }).join("; ") + (root.result.skipped.length > 4 ? "\u2026" : "")) : "" }
        }

        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { visible: root.stage === "select"; label: "Cerrar"; onClicked: root.close() }
            PillButton { id: deleteButton; visible: root.stage === "select" && root.groups.length > 0; enabled: root.removeCount > 0
                         label: "Eliminar " + root.removeCount + " duplicados\u2026"; primary: true; onClicked: root.stage = "confirm" }
            PillButton { visible: root.stage === "confirm"; label: "Volver"; onClicked: root.stage = "select" }
            PillButton { visible: root.stage === "confirm"; label: "Mover a la papelera"; primary: true; onClicked: root.start() }
            PillButton { visible: root.stage === "done"; label: "Cerrar"; primary: true; onClicked: root.close() }
        }
    }
}
