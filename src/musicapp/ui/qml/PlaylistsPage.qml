import QtQuick
import QtQuick.Controls
import "."

Item {
    id: page
    property var lists: (playlists.revision, playlists.lists())
    signal openPlaylist(int playlistId)
    signal newRequested()

    Text {
        id: title
        text: "Listas de reproducci\u00f3n"
        color: Theme.text
        font.pixelSize: 30
        font.weight: Font.Bold
        anchors { left: parent.left; top: parent.top; leftMargin: 24; topMargin: 8 }
    }
    Text {
        id: sub
        text: Theme.plural(page.lists.length, "lista", "listas")
        color: Theme.textDim
        font.pixelSize: 13
        anchors { left: parent.left; top: title.bottom; leftMargin: 24; topMargin: 2 }
    }
    PillButton {
        id: newButton
        label: "Nueva lista"
        primary: true
        anchors { left: parent.left; top: sub.bottom; leftMargin: 24; topMargin: 12 }
        onClicked: page.newRequested()
    }
    Text {
        visible: page.lists.length === 0
        width: parent.width - 48
        anchors { left: parent.left; top: newButton.bottom; leftMargin: 24; topMargin: 24 }
        wrapMode: Text.WordWrap
        color: Theme.textDim
        font.pixelSize: 14
        text: "Todav\u00eda no tienes listas. Crea una, o guarda la lista actual desde \u00abReproduciendo\u00bb. Tambi\u00e9n puedes hacer clic derecho en una canci\u00f3n \u25b8 Agregar a una lista\u2026"
    }
    ListView {
        id: list
        clip: true
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; top: newButton.bottom; topMargin: 12 }
        model: page.lists
        delegate: Item {
            width: list.width
            height: 64
            Rectangle {
                anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                radius: 8
                color: mouse.containsMouse ? Theme.surfaceHover : "transparent"
                Behavior on color { ColorAnimation { duration: Theme.fast } }
            }
            Rectangle {
                id: icon
                x: 24
                anchors.verticalCenter: parent.verticalCenter
                width: 44; height: 44; radius: 6
                color: Qt.hsla(((modelData.id * 61) % 360) / 360, 0.45, 0.32, 1)
                Icon { anchors.centerIn: parent; svg: Theme.iconPlay; size: 16; color: Theme.text }
            }
            Column {
                anchors { left: icon.right; leftMargin: 16; right: parent.right; rightMargin: 24; verticalCenter: parent.verticalCenter }
                spacing: 2
                Text { width: parent.width; text: modelData.name; color: Theme.text; font.pixelSize: 15; elide: Text.ElideRight }
                Text {
                    text: Theme.plural(modelData.tracks, "canci\u00f3n", "canciones") + (modelData.tracks > 0 ? " \u00b7 " + Theme.fmtLong(modelData.duration) : "")
                    color: Theme.textDim
                    font.pixelSize: 12
                }
            }
            MouseArea {
                id: mouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: page.openPlaylist(modelData.id)
            }
        }
        ScrollBar.vertical: ScrollBar { }
    }
}
