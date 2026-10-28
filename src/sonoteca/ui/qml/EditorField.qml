import QtQuick
import QtQuick.Controls
import "."

Column {
    id: root
    property string key
    property string label
    property bool mixed: false
    property bool number: false
    property bool touched: false
    property alias text: input.text
    property alias echoMode: input.echoMode   // TextInput.Password para claves
    signal accepted()
    readonly property int cursor: input.cursorPosition
    spacing: 4

    function forceFocus() { input.forceActiveFocus(); input.selectAll() }

    function reset(value, isMixed) {
        input.text = value
        input.cursorPosition = 0   // con valores largos se ve el principio, no el final
        mixed = isMixed
        touched = false
    }

    Text { text: root.label; color: Theme.textDim; font.pixelSize: 12 }
    TextField {
        id: input
        width: parent.width
        color: Theme.text
        font.pixelSize: 14
        leftPadding: 12
        placeholderText: root.mixed ? "(varios valores)" : ""
        placeholderTextColor: Theme.textDim
        validator: root.number ? numbers : null
        onTextEdited: root.touched = true
        onAccepted: root.accepted()
        onActiveFocusChanged: if (!activeFocus) cursorPosition = 0
        selectByMouse: true
        IntValidator { id: numbers; bottom: 0; top: 9999 }
        background: Rectangle {
            implicitHeight: 38
            radius: 6
            color: input.activeFocus ? Theme.border : Theme.surfaceRaised
            border.width: root.touched ? 1 : 0
            border.color: Theme.accent
        }
    }
}
