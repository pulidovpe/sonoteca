import QtQuick
import QtQuick.Controls
import "."

// Modo compacto de la ventana principal: la portada (del álbum o, si no tiene, la del artista), debajo el título de la canción
// que suena (en el color de acento; si es más largo que el ancho, se desplaza cada cierto tiempo para leerlo completo) y los
// botones de reproducción (aleatorio, anterior, reproducir/pausar, siguiente y silencio).
// El icono de la esquina devuelve la ventana completa; el artista sale como tooltip de la portada.
Rectangle {
    id: root
    color: Theme.bg
    signal restoreRequested()
    readonly property string kind: player.hasTrack ? library.coverKind(player.currentTrack.albumId, player.currentTrack.artistId) : ""
    readonly property string coverSource: !player.hasTrack ? ""
        : (kind === "artist" ? "image://cover/artist/" + player.currentTrack.artistId : "image://cover/" + player.currentTrack.albumId)
          + "?v=" + Theme.dataRevision
    property alias restoreButton: restoreButton
    property alias shuffleButton: shuffleButton
    property alias muteButton: muteButton
    property alias coverImage: cover
    property alias titleBox: titleBox

    Rectangle {
        id: coverBox
        anchors { horizontalCenter: parent.horizontalCenter; top: parent.top; topMargin: 8 }
        // cuadrada: cabe en el ancho (menos 48) y deja sitio al título (24 + 6) y a la fila de botones (52)
        width: Math.max(80, Math.min(parent.width - 48, parent.height - 8 - 6 - 24 - 52 - 6))
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
    Item {   // título: centrado si cabe; si no, va y viene con pausas
        id: titleBox
        anchors { left: parent.left; right: parent.right; top: coverBox.bottom; leftMargin: 14; rightMargin: 14; topMargin: 6 }
        height: 24
        clip: true
        property real offset: 0
        readonly property real overflow: Math.max(0, titleText.implicitWidth - width)
        Text {
            id: titleText
            y: (parent.height - height) / 2
            x: titleBox.overflow > 0 ? -titleBox.offset : (titleBox.width - implicitWidth) / 2
            text: player.hasTrack ? player.currentTrack.title : ""
            color: Theme.accent
            font.pixelSize: 17
            font.weight: Font.Bold
            wrapMode: Text.NoWrap
            onTextChanged: titleBox.offset = 0
        }
        SequentialAnimation {
            id: marquee
            running: titleBox.overflow > 0 && root.visible
            loops: Animation.Infinite
            onRunningChanged: if (!running) titleBox.offset = 0
            PauseAnimation { duration: 2500 }
            NumberAnimation { target: titleBox; property: "offset"; from: 0; to: titleBox.overflow
                              duration: Math.max(1200, titleBox.overflow * 30); easing.type: Easing.InOutSine }
            PauseAnimation { duration: 1500 }
            NumberAnimation { target: titleBox; property: "offset"; to: 0
                              duration: Math.max(700, titleBox.overflow * 14); easing.type: Easing.InOutSine }
        }
    }
    Row {
        anchors { horizontalCenter: parent.horizontalCenter; top: titleBox.bottom; bottom: parent.bottom }
        spacing: 10
        IconButton {
            id: shuffleButton
            anchors.verticalCenter: parent.verticalCenter
            width: 30; height: 30; iconSize: 18
            svg: Theme.iconShuffle
            active: player.shuffle
            toolTip: player.shuffle ? "Aleatorio: activado" : "Aleatorio"
            onClicked: player.toggleShuffle()
        }
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
        IconButton {
            id: muteButton
            anchors.verticalCenter: parent.verticalCenter
            width: 30; height: 30; iconSize: 18
            svg: player.muted ? Theme.iconMuted : Theme.iconSpeaker
            active: player.muted
            toolTip: player.muted ? "Quitar el silencio" : "Silenciar (silencio total)"
            onClicked: player.toggleMute()
        }
    }
}
