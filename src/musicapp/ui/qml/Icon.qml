import QtQuick
import QtQuick.Shapes

// Icono vectorial: `svg` es un path en un lienzo de 24x24
Item {
    id: root
    property string svg
    property color color: "#ffffff"
    property real size: 24
    width: size
    height: size

    Shape {
        width: 24
        height: 24
        scale: root.size / 24
        transformOrigin: Item.TopLeft
        antialiasing: true
        ShapePath {
            fillColor: root.color
            strokeColor: "transparent"
            PathSvg { path: root.svg }
        }
    }
}
