import QtQuick
import QtQuick.Controls
import "."

Item {
    id: root
    property string svg
    property real iconSize: 20
    property color color: Theme.text
    property string toolTip: ""
    signal clicked()
    width: 36
    height: 36

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: mouse.containsMouse ? Theme.surfaceHover : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    Icon {
        anchors.centerIn: parent
        svg: root.svg
        size: root.iconSize
        color: mouse.containsMouse ? Theme.text : Theme.textDim
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
    AppToolTip {
        visible: mouse.containsMouse && root.toolTip !== ""
        delay: 400
        text: root.toolTip
    }
}
