import QtQuick
import QtQuick.Controls
import "."

Item {
    id: page
    property string heading
    property string hint: ""
    property var items: []
    signal editRequested(var ids)
    signal menuRequested(var ids)
    property alias actions: actionRow.data   // botones opcionales junto al título
    property var ids: items.map(function (x) { return x.id })

    Text {
        id: title
        text: page.heading
        color: Theme.text
        font.pixelSize: 30
        font.weight: Font.Bold
        elide: Text.ElideRight
        anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: 24; rightMargin: 24; topMargin: 8 }
    }
    Text {
        id: sub
        text: Theme.plural(page.items.length, "pista", "pistas") + (page.hint !== "" ? " · " + page.hint : "")
        color: Theme.textDim
        font.pixelSize: 13
        elide: Text.ElideRight
        anchors { left: parent.left; right: parent.right; top: title.bottom; leftMargin: 24; rightMargin: 24; topMargin: 2 }
    }
    Flow {
        id: actionRow
        visible: children.length > 0
        spacing: 10
        anchors { left: parent.left; right: parent.right; top: sub.bottom; leftMargin: 24; rightMargin: 24; topMargin: 10 }
    }
    ListView {
        id: list
        clip: true
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; top: actionRow.visible ? actionRow.bottom : sub.bottom; topMargin: 12 }
        model: page.items
        delegate: TrackRow {
            width: list.width
            title: modelData.title
            subtitle: modelData.subtitle
            badge: modelData.badge
            duration: modelData.duration > 0 ? Theme.fmt(modelData.duration) : ""
            current: player.currentId === modelData.id
            trackId: modelData.id
            onActivated: player.playTrackIds(page.ids, index)
            onContextRequested: page.menuRequested([modelData.id])
        }
        ScrollBar.vertical: ScrollBar { }
    }
}
