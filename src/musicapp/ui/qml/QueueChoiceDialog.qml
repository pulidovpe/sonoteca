import QtQuick
import QtQuick.Controls
import "."

// Se pregunta al reproducir una canción suelta cuando ya hay una lista en reproducción
Popup {
    id: root
    property int trackId: 0
    property string trackTitle: ""
    property int queueCount: 0

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 540
    padding: 24
    background: Rectangle { color: "#1d1d1f"; radius: 12; border.color: "#2e2e32"; border.width: 1 }
    Overlay.modal: Rectangle { color: "#99000000" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function ask(id) {
        trackId = id
        trackTitle = library.trackInfo(id).title || ""
        queueCount = player.queueLength
        open()
    }
    function replaceList() {   // vaciar la lista y reproducir solo esta canción
        close()
        player.playOnly(trackId)
    }
    function keepList() {      // suena ya, y la lista sigue después
        close()
        player.playKeepingQueue(trackId)
    }

    contentItem: Column {
        spacing: 14
        Text { text: "Ya hay una lista en reproducci\u00f3n"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold; width: parent.width; wrapMode: Text.WordWrap }
        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Theme.textDim
            font.pixelSize: 14
            text: "La lista actual tiene " + Theme.plural(root.queueCount, "canci\u00f3n", "canciones") + ". \u00bfQuieres vaciarla y reproducir solo \u00ab"
                  + root.trackTitle + "\u00bb? Si la conservas, esa canci\u00f3n suena ahora y la lista contin\u00faa despu\u00e9s."
        }
        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { label: "Cancelar"; onClicked: root.close() }
            PillButton { label: "Conservar la lista"; onClicked: root.keepList() }
            PillButton { label: "Vaciar y reproducir"; primary: true; onClicked: root.replaceList() }
        }
    }
}
