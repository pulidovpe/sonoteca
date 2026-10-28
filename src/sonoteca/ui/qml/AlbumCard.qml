import QtQuick
import "."

Item {
    id: root
    property int albumId
    property string coverSource: "image://cover/" + albumId + "?v=" + Theme.dataRevision
    property string title
    property string subtitle
    signal clicked()

    Rectangle {
        id: card
        anchors.fill: parent
        anchors.margins: 8
        radius: Theme.radius
        color: mouse.containsMouse ? Theme.surfaceHover : Theme.surface
        scale: mouse.containsMouse ? 1.03 : 1.0
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }

        Column {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            Item {
                width: parent.width
                height: width
                Rectangle { anchors.fill: parent; radius: 6; color: Theme.placeholder }
                Image {
                    anchors.fill: parent
                    source: root.coverSource
                    sourceSize.width: 320
                    sourceSize.height: 320
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    opacity: status === Image.Ready ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.slow } }
                }
            }
            Text {
                width: parent.width
                text: root.title
                color: Theme.text
                font.pixelSize: 14
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                text: root.subtitle
                color: Theme.textDim
                font.pixelSize: 12
                elide: Text.ElideRight
            }
        }
        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.clicked()
        }
    }
}
