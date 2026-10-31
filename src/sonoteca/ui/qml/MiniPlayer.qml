import QtQuick
import QtQuick.Controls
import "."

// Modo compacto de la ventana principal: solo la portada (del álbum o, si no tiene, la del artista) y los botones de
// reproducción. El icono de la esquina devuelve la ventana completa. El título y el artista salen como tooltip.
Rectangle {
    id: root
    color: Theme.bg
    signal restoreRequested()
    readonly property string kind: player.hasTrack ? library.coverKind(player.currentTrack.albumId, player.currentTrack.artistId) : ""
    readonly property string coverSource: !player.hasTrack ? ""
        : (kind === "artist" ? "image://cover/artist/" + player.currentTrack.artistId : "image://cover/" + player.currentTrack.albumId)
          + "?v=" + Theme.dataRevision
    property alias restoreButton: restoreButton
    property alias coverImage: cover

    Rectangle {
        id: coverBox
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: width
        color: Theme.placeholder
        Image {
            id: cover
            anchors.fill: parent
            source: root.coverSource
            sourceSize.width: 480
            sourceSize.height: 480
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            visible: root.coverSource !== ""
        }
        Icon {   // sin canción: nota musical del logo
            anchors.centerIn: parent
            visible: root.coverSource === ""
            svg: Theme.iconQueue
            size: 64
            color: Theme.textFaint
        }
        MouseArea { id: coverMouse; anchors.fill: parent; hoverEnabled: true }
        AppToolTip {
            visible: coverMouse.containsMouse && player.hasTrack
            text: player.currentTrack.title + "\n" + player.currentTrack.artist
        }
        Rectangle {   // volver a la ventana completa
            anchors { top: parent.top; right: parent.right; margins: 6 }
            width: 30
            height: 30
            radius: 15
            color: Theme.scrim
            IconButton {
                id: restoreButton
                anchors.fill: parent
                iconSize: 16
                svg: Theme.iconExpand
                toolTip: "Volver a la ventana completa"
                onClicked: root.restoreRequested()
            }
        }
    }
    Row {
        anchors { horizontalCenter: parent.horizontalCenter; top: coverBox.bottom; bottom: parent.bottom }
        spacing: 14
        IconButton { anchors.verticalCenter: parent.verticalCenter; svg: Theme.iconPrev; toolTip: "Anterior"; onClicked: player.previous() }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: 44; height: 44; radius: 22
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: Theme.cyan }
                GradientStop { position: 1.0; color: Theme.magenta }
            }
            scale: playMouse.containsMouse ? 1.07 : 1.0
            Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
            Icon { anchors.centerIn: parent; svg: player.playing ? Theme.iconPause : Theme.iconPlay; size: 22; color: Theme.textOnAccent }
            MouseArea { id: playMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: player.toggle() }
            AppToolTip { visible: playMouse.containsMouse; text: player.playing ? "Pausar" : "Reproducir" }
        }
        IconButton { anchors.verticalCenter: parent.verticalCenter; svg: Theme.iconNext; toolTip: "Siguiente"; onClicked: player.next() }
    }
}
