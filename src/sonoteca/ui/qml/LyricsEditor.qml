import QtQuick
import QtQuick.Controls
import "."

// Escribir o pegar la letra a mano. Si el texto trae marcas [mm:ss] queda sincronizada.
Popup {
    id: root
    property int trackId: 0
    property string trackLabel: ""
    property bool hadLyrics: false
    signal saved(var doc)
    property alias editor: area   // para las pruebas

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(620, Overlay.overlay ? Overlay.overlay.width - 48 : 620)
    height: Math.min(560, Overlay.overlay ? Overlay.overlay.height - 48 : 560)
    padding: 24
    background: Rectangle { color: Theme.panel; radius: 12; border.color: Theme.border; border.width: 1 }
    Overlay.modal: Rectangle { color: Theme.scrim }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function edit(id, label) {
        trackId = id
        trackLabel = label
        area.text = lyrics.rawText(id)
        hadLyrics = area.text !== ""
        open()
        area.forceActiveFocus()
    }
    function save() {
        var doc = lyrics.saveManual(trackId, area.text)
        close()
        saved(doc)
    }

    contentItem: Column {
        spacing: 12
        Text { text: root.hadLyrics ? "Editar letra" : "Agregar letra"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold; width: parent.width }
        Text { text: root.trackLabel; color: Theme.textDim; font.pixelSize: 13; width: parent.width; elide: Text.ElideRight; visible: text !== "" }
        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Theme.textDim
            font.pixelSize: 12
            text: "Escribe o pega la letra, una l\u00ednea por rengl\u00f3n. Si cada l\u00ednea empieza con [mm:ss] (formato LRC), se sincroniza con la canci\u00f3n. Dejarla vac\u00eda borra la letra guardada."
        }
        Rectangle {
            width: parent.width
            height: root.height - 24 * 2 - 150
            radius: 8
            color: Theme.field
            border.color: area.activeFocus ? Theme.accent : Theme.border
            ScrollView {
                anchors.fill: parent
                anchors.margins: 4
                TextArea {
                    id: area
                    color: Theme.text
                    font.pixelSize: 14
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    background: null
                    placeholderText: "Letra\u2026"
                    placeholderTextColor: Theme.textDim
                }
            }
        }
        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { label: "Cancelar"; onClicked: root.close() }
            PillButton { label: "Guardar letra"; primary: true; onClicked: root.save() }
        }
    }
}
