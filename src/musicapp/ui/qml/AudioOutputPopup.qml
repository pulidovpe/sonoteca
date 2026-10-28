import QtQuick
import QtQuick.Controls
import "."

// Salida de audio: elegir entre parlantes, audífonos (cableados o Bluetooth) u otra salida
Popup {
    id: root
    property var devices: []
    property alias listItem: deviceList

    padding: 8
    width: 360
    focus: true
    background: Rectangle { color: "#1d1d1f"; radius: 10; border.color: "#2e2e32"; border.width: 1 }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 120 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 } }

    function openPopup() { devices = player.audioDevices(); open() }
    Connections {
        target: player
        function onAudioChanged() { if (root.visible) root.devices = player.audioDevices() }
    }

    contentItem: Column {
        spacing: 2
        Text { leftPadding: 8; topPadding: 4; bottomPadding: 6; text: "Salida de audio"; color: Theme.textDim; font.pixelSize: 12; font.weight: Font.DemiBold }
        ListView {
            id: deviceList
            width: parent.width
            height: Math.min(contentHeight, 280)
            clip: true
            model: root.devices
            delegate: Rectangle {
                width: deviceList.width
                height: 40
                radius: 6
                color: rowMouse.containsMouse ? Theme.surfaceHover : "transparent"
                Text {
                    anchors { left: parent.left; leftMargin: 12; right: check.left; rightMargin: 8; verticalCenter: parent.verticalCenter }
                    text: modelData.name
                    color: modelData.current ? Theme.accent : Theme.text
                    font.pixelSize: 13
                    font.weight: modelData.current ? Font.DemiBold : Font.Normal
                    elide: Text.ElideRight
                }
                Text {
                    id: check
                    anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
                    text: "\u2713"
                    visible: modelData.current
                    color: Theme.accent
                    font.pixelSize: 15
                }
                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: { player.setAudioDevice(modelData.id); root.close() }
                }
            }
        }
        Text {
            leftPadding: 8; bottomPadding: 4
            width: parent.width
            visible: root.devices.length <= 1
            wrapMode: Text.WordWrap
            text: "No se detectaron otras salidas. Conecta los audífonos o activa el Bluetooth y vuelve a abrir este menú."
            color: Theme.textDim
            font.pixelSize: 11
        }
    }
}
