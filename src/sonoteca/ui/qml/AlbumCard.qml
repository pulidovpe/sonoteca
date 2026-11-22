import QtQuick
import "."

Item {
    id: root
    property int albumId
    property string coverSource: "image://cover/" + albumId + "?v=" + Theme.dataRevision
    property string title
    property string subtitle
    // Solo los álbumes (albumId > 0) llevan menú ⋮ y clic derecho; las cajas de artistas no
    readonly property bool hasMenu: albumId > 0
    signal clicked()
    signal menuRequested()

    Rectangle {
        id: card
        anchors.fill: parent
        anchors.margins: 8
        radius: Theme.radius
        // HoverHandler (no el MouseArea): el botón ⋮ de encima no debe apagar el resaltado
        color: cardHover.hovered ? Theme.surfaceHover : Theme.surface
        scale: cardHover.hovered ? 1.03 : 1.0
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
        HoverHandler { id: cardHover }

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
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            cursorShape: Qt.PointingHandCursor
            onClicked: (m) => {
                if (m.button === Qt.RightButton) { if (root.hasMenu) root.menuRequested() }
                else root.clicked()
            }
        }
        // Botón de opciones (⋮) sobre la portada: aparece al pasar el ratón y abre el menú con todas las pistas del álbum
        Rectangle {
            id: moreBack
            visible: root.hasMenu
            width: 30
            height: 30
            radius: 15
            color: Theme.surface
            opacity: cardHover.hovered ? 0.9 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
            anchors { top: parent.top; right: parent.right; topMargin: 16; rightMargin: 16 }
        }
        IconButton {
            visible: root.hasMenu
            width: 30
            height: 30
            iconSize: 16
            svg: Theme.iconMore
            toolTip: "M\u00e1s opciones"
            enabled: cardHover.hovered
            opacity: cardHover.hovered ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
            anchors.centerIn: moreBack
            onClicked: root.menuRequested()
        }
    }
}
