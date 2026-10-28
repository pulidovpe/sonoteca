import QtQuick
import QtQuick.Controls
import "."

Rectangle {
    id: bar
    property bool videoOpen: false
    property alias audioButton: audioButton   // para las pruebas
    signal videoToggled()
    signal artistRequested(int artistId, string name)   // enlaces de la canci\u00f3n que suena
    signal albumRequested(int albumId)
    property alias artistLink: artistLink
    property alias albumLink: albumLink
    color: "#141415"
    clip: true

    function fmtMs(ms) { return Theme.fmt(ms / 1000) }

    Rectangle { width: parent.width; height: 1; color: "#26262a" }

    // Izquierda: portada y datos de la pista
    Item {
        id: left
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom; leftMargin: 16 }
        width: Math.max(200, Math.min(300, bar.width * 0.24))
        Rectangle {
            id: artBg
            width: 56; height: 56; radius: 4
            color: "#222224"
            anchors.verticalCenter: parent.verticalCenter
            Image {
                anchors.fill: parent
                source: player.hasTrack ? "image://cover/" + player.currentTrack.albumId + "?v=" + Theme.dataRevision : ""
                sourceSize.width: 160
                sourceSize.height: 160
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
            }
        }
        Column {
            anchors { left: artBg.right; leftMargin: 12; right: parent.right; verticalCenter: parent.verticalCenter }
            spacing: 3
            Text {
                width: parent.width
                text: player.currentTrack.title || ""
                color: Theme.text
                font.pixelSize: 14
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }
            Text {
                id: artistLink
                readonly property bool linked: !!player.currentTrack.hasArtist
                width: Math.min(parent.width, implicitWidth)
                text: player.currentTrack.artist || ""
                color: linked && artistMouse.containsMouse ? Theme.text : Theme.textDim
                font.pixelSize: 12
                font.underline: linked && artistMouse.containsMouse
                elide: Text.ElideRight
                MouseArea {
                    id: artistMouse
                    anchors.fill: parent
                    enabled: artistLink.linked
                    hoverEnabled: true
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: bar.artistRequested(player.currentTrack.artistId, player.currentTrack.artist)
                }
            }
            Text {
                id: albumLink
                readonly property bool linked: !!player.currentTrack.hasAlbum
                visible: linked
                width: Math.min(parent.width, implicitWidth)
                text: player.currentTrack.album || ""
                color: albumMouse.containsMouse ? Theme.text : Theme.textDim
                font.pixelSize: 12
                font.underline: albumMouse.containsMouse
                elide: Text.ElideRight
                MouseArea {
                    id: albumMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: bar.albumRequested(player.currentTrack.albumId)
                }
            }
        }
    }

    // Centro: controles y progreso
    Column {
        anchors.centerIn: parent
        spacing: 6
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 10
            Chip {
                anchors.verticalCenter: parent.verticalCenter
                height: 28
                label: "Aleatorio"
                active: player.shuffle
                onClicked: player.toggleShuffle()
            }
            IconButton { anchors.verticalCenter: parent.verticalCenter; svg: Theme.iconPrev; onClicked: player.previous() }
            Rectangle {
                width: 44; height: 44; radius: 22
                color: "#ffffff"
                scale: playMouse.containsMouse ? 1.07 : 1.0
                Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
                Icon {
                    anchors.centerIn: parent
                    svg: player.playing ? Theme.iconPause : Theme.iconPlay
                    size: 22
                    color: "#000000"
                }
                MouseArea {
                    id: playMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: player.toggle()
                }
            }
            IconButton { anchors.verticalCenter: parent.verticalCenter; svg: Theme.iconNext; onClicked: player.next() }
            Chip {
                anchors.verticalCenter: parent.verticalCenter
                height: 28
                label: player.repeatMode === "all" ? "Repetir: todo"
                     : player.repeatMode === "one" ? "Repetir: una" : "Repetir"
                active: player.repeatMode !== "off"
                onClicked: player.cycleRepeat()
            }
        }
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 10
            Text {
                width: 44
                horizontalAlignment: Text.AlignRight
                anchors.verticalCenter: parent.verticalCenter
                text: bar.fmtMs(player.position)
                color: Theme.textDim
                font.pixelSize: 12
            }
            AppSlider {
                id: seekSlider
                width: Math.max(160, Math.min(460, bar.width - left.width * 2 - 280))
                from: 0
                to: Math.max(1, player.duration)
                onMoved: player.seek(value)
                Binding { target: seekSlider; property: "value"; value: player.position; when: !seekSlider.pressed }
            }
            Text {
                width: 44
                anchors.verticalCenter: parent.verticalCenter
                text: bar.fmtMs(player.duration)
                color: Theme.textDim
                font.pixelSize: 12
            }
        }
    }

    // Derecha: video, salida de audio (grupo propio) y, aparte, el volumen
    Row {
        anchors { right: parent.right; rightMargin: 24; verticalCenter: parent.verticalCenter }
        spacing: 14
        Chip {
            anchors.verticalCenter: parent.verticalCenter
            height: 28
            visible: player.isVideo
            label: bar.videoOpen ? "Ocultar video" : "Ver video"
            active: bar.videoOpen
            onClicked: bar.videoToggled()
        }
        IconButton {
            id: audioButton
            anchors.verticalCenter: parent.verticalCenter
            width: 30
            height: 30
            iconSize: 18
            // El icono indica el tipo de salida activa; el tooltip, cu\u00e1l es
            svg: player.audioDeviceKind === "headphones" ? Theme.iconHeadphones
                 : (player.audioDeviceKind === "display" ? Theme.iconDisplay : Theme.iconSpeakerBox)
            toolTip: "Salida de audio: " + (player.audioActiveName || "predeterminada del sistema")
            onClicked: audioPopup.openPopup()
        }
        Rectangle { anchors.verticalCenter: parent.verticalCenter; width: 1; height: 24; color: "#2e2e32" }
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            Icon { anchors.verticalCenter: parent.verticalCenter; svg: Theme.iconSpeaker; size: 18; color: Theme.textDim }
            AppSlider {
                id: volSlider
                anchors.verticalCenter: parent.verticalCenter
                width: 110
                from: 0
                to: 1
                onMoved: player.setVolume(value)
                Binding { target: volSlider; property: "value"; value: player.volume; when: !volSlider.pressed }
            }
        }
    }
    AudioOutputPopup { id: audioPopup; x: bar.width - width - 16; y: -height - 8 }
}
