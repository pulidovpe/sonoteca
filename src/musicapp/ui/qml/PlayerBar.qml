import QtQuick
import QtQuick.Controls
import "."

Rectangle {
    id: bar
    property bool videoOpen: false
    signal videoToggled()
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
                width: parent.width
                text: player.currentTrack.artist || ""
                color: Theme.textDim
                font.pixelSize: 12
                elide: Text.ElideRight
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

    // Derecha: video y volumen
    Row {
        anchors { right: parent.right; rightMargin: 24; verticalCenter: parent.verticalCenter }
        spacing: 12
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
            svg: Theme.iconSpeaker
            onClicked: audioPopup.openPopup()
        }
        Text { anchors.verticalCenter: parent.verticalCenter; text: "Vol"; color: Theme.textDim; font.pixelSize: 12 }
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
    AudioOutputPopup { id: audioPopup; x: bar.width - width - 16; y: -height - 8 }
}
