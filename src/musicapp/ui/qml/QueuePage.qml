import QtQuick
import QtQuick.Controls
import "."

// La lista que suena: es temporal (se pierde al cerrar la aplicación) salvo que se guarde como lista
Item {
    id: page
    property var items: []
    signal editRequested(var ids)
    signal menuRequested(var ids)
    signal saveRequested()

    function refresh() { items = player.queueItems() }
    function removeAt(i) { player.removeFromQueue(i) }
    function moveUp(i) { if (i > 0) player.moveInQueue(i, i - 1) }
    function moveDown(i) { if (i < items.length - 1) player.moveInQueue(i, i + 1) }
    Component.onCompleted: refresh()
    Connections {
        target: player
        function onQueueChanged() { page.refresh() }
    }
    Connections {
        target: Theme
        function onDataRevisionChanged() { page.refresh() }   // p. ej. tras editar tags
    }

    Text {
        id: title
        text: "Lista actual"
        color: Theme.text
        font.pixelSize: 30
        font.weight: Font.Bold
        anchors { left: parent.left; top: parent.top; leftMargin: 24; topMargin: 8 }
    }
    Text {
        id: sub
        color: Theme.textDim
        font.pixelSize: 13
        text: page.items.length === 0 ? "Vac\u00eda" : Theme.plural(page.items.length, "canci\u00f3n", "canciones") + " \u00b7 temporal: se pierde al cerrar la aplicaci\u00f3n"
        anchors { left: parent.left; top: title.bottom; leftMargin: 24; topMargin: 2 }
    }
    Flow {
        id: buttons
        spacing: 10
        anchors { left: parent.left; right: parent.right; top: sub.bottom; leftMargin: 24; rightMargin: 24; topMargin: 12 }
        PillButton { label: "Reproducir"; primary: true; visible: page.items.length > 0 && !player.hasTrack; onClicked: player.playQueueAt(0) }
        PillButton { label: "Guardar como lista\u2026"; enabled: page.items.length > 0; onClicked: page.saveRequested() }
        PillButton { label: "Nueva lista temporal"; onClicked: player.newTemporaryList() }
        PillButton { label: "Vaciar"; enabled: page.items.length > 0; onClicked: player.clearQueue() }
    }
    Text {
        visible: page.items.length === 0
        width: parent.width - 48
        anchors { left: parent.left; top: buttons.bottom; leftMargin: 24; topMargin: 24 }
        wrapMode: Text.WordWrap
        color: Theme.textDim
        font.pixelSize: 14
        text: "No hay canciones en la lista. Haz clic derecho en una canci\u00f3n (o usa \u00abAgregar a la lista\u00bb en un \u00e1lbum) para agregarla, y se reproducir\u00e1n en orden."
    }
    ListView {
        id: list
        clip: true
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; top: buttons.bottom; topMargin: 12 }
        model: page.items
        delegate: ListTrackRow {
            width: list.width
            position: modelData.position
            title: modelData.title
            subtitle: modelData.artist + " \u00b7 " + modelData.album
            duration: modelData.duration
            current: modelData.current
            playing: player.playing
            onActivated: player.playQueueAt(modelData.position)
            onMenuRequested: page.menuRequested([modelData.id])
            onEditRequested: page.editRequested([modelData.id])
            onMoveUp: page.moveUp(index)
            onMoveDown: page.moveDown(index)
            onRemoveRequested: page.removeAt(index)
        }
        ScrollBar.vertical: ScrollBar { }
    }
}
