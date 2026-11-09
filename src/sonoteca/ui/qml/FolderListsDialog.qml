import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Crear listas de reproducción a partir de carpetas de la biblioteca (las que registró «Buscar música»).
// Paso 1: elegir carpetas (y si cada una incluye sus subcarpetas). Paso 2 (solo si hay nombres repetidos): decidir qué hacer.
Popup {
    id: root
    property var candidates: []
    property var picked: ({})            // ruta -> true
    property var withSub: ({})           // ruta -> true (incluir subcarpetas)
    property string stage: "pick"        // pick | conflicts
    property var plan: []
    property var choices: ({})           // ruta -> create | rename | append | skip
    property string message: ""
    property alias list: folderRepeater  // para las pruebas
    property alias createButton: createButton
    signal toastRequested(string text)

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(720, Overlay.overlay ? Overlay.overlay.width - 48 : 720)
    height: Math.min(640, Overlay.overlay ? Overlay.overlay.height - 48 : 640)
    padding: 24
    background: Rectangle { color: Theme.panel; radius: 12; border.color: Theme.border; border.width: 1 }
    Overlay.modal: Rectangle { color: Theme.scrim }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    readonly property int pickedCount: Object.keys(picked).length
    // Una carpeta sin música propia (solo subcarpetas) siempre incluye sus subcarpetas
    function subOf(item) { return item.tracks === 0 ? true : !!withSub[item.path] }
    function countOf(item) { return subOf(item) ? item.total : item.tracks }
    function setPicked(path, on) {
        var next = Object.assign({}, picked)
        if (on) next[path] = true
        else delete next[path]
        picked = next
    }
    function setSub(path, on) {
        var next = Object.assign({}, withSub)
        if (on) next[path] = true
        else delete next[path]
        withSub = next
    }
    function setChoice(path, mode) {
        var next = Object.assign({}, choices)
        next[path] = mode
        choices = next
    }
    function openDialog() {
        candidates = playlists.folderCandidates()
        picked = ({})
        withSub = ({})
        choices = ({})
        plan = []
        stage = "pick"
        message = ""
        open()
    }
    function start() {
        message = ""
        var items = []
        candidates.forEach(function (c) { if (picked[c.path]) items.push({ path: c.path, sub: subOf(c) }) })
        if (items.length === 0) return
        plan = playlists.planFolderLists(items)
        if (plan.length === 0) { message = "Las carpetas elegidas no tienen canciones."; return }
        var conflicts = plan.filter(function (p) { return p.conflict !== "" })
        if (conflicts.length === 0) { finish(); return }
        var next = {}
        conflicts.forEach(function (p) { next[p.path] = "rename" })
        choices = next
        stage = "conflicts"
    }
    function finish() {
        var decisions = plan.map(function (p) {
            return { path: p.path, sub: p.sub, name: p.name, mode: p.conflict === "" ? "create" : (choices[p.path] || "rename") }
        })
        var r = playlists.createFromFolders(decisions)
        close()
        toastRequested(r.message)
    }

    contentItem: ColumnLayout {
        spacing: 12
        Text {
            Layout.fillWidth: true
            text: root.stage === "pick" ? "Crear listas desde carpetas" : "Nombres repetidos"
            color: Theme.text
            font.pixelSize: 22
            font.weight: Font.Bold
        }
        Text {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.textDim
            font.pixelSize: 13
            text: root.stage === "pick"
                  ? "Marca las carpetas de tu biblioteca; cada una dar\u00e1 una lista con su nombre. Con \u00abcon subcarpetas\u00bb la lista incluye tambi\u00e9n la m\u00fasica de todas las subcarpetas. Tus archivos no se tocan."
                  : "Ya existe una lista con el mismo nombre (o dos carpetas elegidas se llaman igual). Elige qu\u00e9 hacer en cada caso."
        }

        // ---- Paso 1: elegir carpetas ----
        Flickable {
            id: scroller
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.stage === "pick"
            contentHeight: body.height
            clip: true
            ScrollBar.vertical: ScrollBar { }
            Column {
                id: body
                width: scroller.width - 12
                spacing: 2
                Repeater {
                    id: folderRepeater
                    model: root.candidates
                    delegate: Rectangle {
                        width: body.width
                        height: 40
                        radius: 8
                        color: rowMouse.containsMouse ? Theme.surfaceHover : "transparent"
                        MouseArea { id: rowMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                        AppCheck {
                            id: pickCheck
                            x: 8 + modelData.depth * 18
                            anchors.verticalCenter: parent.verticalCenter
                            checked: !!root.picked[modelData.path]
                            onToggled: root.setPicked(modelData.path, checked)
                        }
                        Text {
                            anchors { left: pickCheck.right; leftMargin: -4; right: subCheck.visible ? subCheck.left : countText.left; rightMargin: 10; verticalCenter: parent.verticalCenter }
                            text: modelData.name
                            color: Theme.text
                            font.pixelSize: 13
                            elide: Text.ElideMiddle
                            MouseArea { anchors.fill: parent; onClicked: pickCheck.toggle() }
                        }
                        AppCheck {
                            id: subCheck
                            visible: modelData.hasChildren
                            enabled: modelData.tracks > 0     // sin música propia: siempre con subcarpetas
                            anchors { right: countText.left; rightMargin: 12; verticalCenter: parent.verticalCenter }
                            text: "con subcarpetas"
                            checked: root.subOf(modelData)
                            onToggled: root.setSub(modelData.path, checked)
                        }
                        Text {
                            id: countText
                            width: 96
                            anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
                            horizontalAlignment: Text.AlignRight
                            text: Theme.plural(root.countOf(modelData), "canci\u00f3n", "canciones")
                            color: Theme.textDim
                            font.pixelSize: 12
                        }
                    }
                }
                Text {
                    visible: root.candidates.length === 0
                    width: parent.width
                    wrapMode: Text.WordWrap
                    color: Theme.textDim
                    font.pixelSize: 13
                    text: "Todav\u00eda no hay carpetas con m\u00fasica. Usa \u00abBuscar m\u00fasica\u2026\u00bb en el men\u00fa Archivo."
                }
            }
        }

        // ---- Paso 2: nombres repetidos ----
        Flickable {
            id: conflictScroller
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.stage === "conflicts"
            contentHeight: conflictColumn.height
            clip: true
            ScrollBar.vertical: ScrollBar { }
            Column {
                id: conflictColumn
                width: conflictScroller.width - 12
                spacing: 14
                Repeater {
                    id: conflictRepeater
                    model: root.plan.filter(function (p) { return p.conflict !== "" })
                    delegate: Column {
                        width: conflictColumn.width
                        spacing: 6
                        Text {
                            width: parent.width
                            wrapMode: Text.WordWrap
                            color: Theme.text
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                            text: "\u00ab" + modelData.name + "\u00bb \u00b7 " + Theme.plural(modelData.count, "canci\u00f3n", "canciones")
                        }
                        Text {
                            width: parent.width
                            wrapMode: Text.WordWrap
                            color: Theme.textDim
                            font.pixelSize: 12
                            text: (modelData.conflict === "existing" ? "Ya existe una lista con ese nombre. " : "Otra carpeta elegida se llama igual. ") + modelData.path
                        }
                        Flow {
                            width: parent.width
                            spacing: 8
                            Chip { label: "Crear con otro nombre"; active: root.choices[modelData.path] === "rename"; onClicked: root.setChoice(modelData.path, "rename") }
                            Chip { label: "Agregar a esa lista"; active: root.choices[modelData.path] === "append"; onClicked: root.setChoice(modelData.path, "append") }
                            Chip { label: "Omitir"; active: root.choices[modelData.path] === "skip"; onClicked: root.setChoice(modelData.path, "skip") }
                        }
                    }
                }
            }
        }

        Text { Layout.fillWidth: true; visible: root.message !== ""; text: root.message; color: Theme.danger; font.pixelSize: 13; wrapMode: Text.WordWrap }
        Row {
            Layout.alignment: Qt.AlignRight
            spacing: 10
            PillButton { visible: root.stage === "conflicts"; label: "Volver"; onClicked: root.stage = "pick" }
            PillButton { label: "Cancelar"; onClicked: root.close() }
            PillButton {
                id: createButton
                primary: true
                label: root.stage === "pick" ? "Crear listas (" + root.pickedCount + ")" : "Continuar"
                enabled: root.stage === "conflicts" || root.pickedCount > 0
                onClicked: root.stage === "pick" ? root.start() : root.finish()
            }
        }
    }
}
