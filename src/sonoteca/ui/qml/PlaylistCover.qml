import QtQuick
import "."

// Portada de una lista: un álbum = su portada; de 2 a 4 álbumes = collage (2 mitades, 1+2 o 2x2)
Item {
    id: root
    property var albumIds: []
    property color fallback: "#222224"
    readonly property int n: Math.min(albumIds.length, 4)
    // Cada baldosa en fracciones del tamaño total
    readonly property var tiles: {
        if (n === 1) return [{ x: 0, y: 0, w: 1, h: 1 }]
        if (n === 2) return [{ x: 0, y: 0, w: 0.5, h: 1 }, { x: 0.5, y: 0, w: 0.5, h: 1 }]
        if (n === 3) return [{ x: 0, y: 0, w: 0.5, h: 1 }, { x: 0.5, y: 0, w: 0.5, h: 0.5 }, { x: 0.5, y: 0.5, w: 0.5, h: 0.5 }]
        if (n === 4) return [{ x: 0, y: 0, w: 0.5, h: 0.5 }, { x: 0.5, y: 0, w: 0.5, h: 0.5 },
                             { x: 0, y: 0.5, w: 0.5, h: 0.5 }, { x: 0.5, y: 0.5, w: 0.5, h: 0.5 }]
        return []
    }
    property alias tileRepeater: tilesRepeater   // para las pruebas

    Rectangle { anchors.fill: parent; radius: 4; color: root.fallback }
    Icon { anchors.centerIn: parent; visible: root.n === 0; svg: Theme.iconPlay; size: Math.max(12, root.width * 0.35); color: Theme.text }
    Item {
        anchors.fill: parent
        clip: true
        Repeater {
            id: tilesRepeater
            model: root.tiles
            delegate: Image {
                x: modelData.x * root.width
                y: modelData.y * root.height
                width: modelData.w * root.width - (root.n > 1 ? 1 : 0)
                height: modelData.h * root.height - (root.n > 1 ? 1 : 0)
                source: "image://cover/" + root.albumIds[index] + "?v=" + Theme.dataRevision
                sourceSize.width: 2 * Math.ceil(width)
                sourceSize.height: 2 * Math.ceil(height)
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
            }
        }
    }
}
