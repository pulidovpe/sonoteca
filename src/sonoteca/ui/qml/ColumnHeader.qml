import QtQuick
import "."
import "TrackSort.js" as TrackSort

// Primera fila de una lista de canciones: títulos de columna que ordenan (nombre, artista, álbum, año, más escuchadas).
// Se alinea con las filas (`TrackRow` / `ListTrackRow`) usando los mismos anchos fijos. Un clic ordena; otro invierte; el
// tercero vuelve al orden original. «Más escuchadas» empieza por las que más suenan.
Item {
    id: root
    property bool hasNumber: false          // filas con columna de número (o casilla de selección)
    property int nameLeft: 28 + (hasNumber ? 44 : 0)      // dónde empieza la columna del nombre (112 en `ListTrackRow`)
    property bool hasAlbum: true
    property bool hasYear: true
    property bool hasPlays: true
    property string sortKey: ""
    property bool sortAsc: true
    readonly property int tier: Theme.tier(width)
    readonly property bool showAlbum: hasAlbum && tier >= 2
    readonly property bool showYear: hasYear && width >= Theme.yearMin
    readonly property bool showPlays: hasPlays && tier >= 3

    function toggle(key) {
        var first = key !== "plays"          // sentido del primer clic: ascendente (en reproducciones, descendente)
        if (sortKey !== key) { sortKey = key; sortAsc = first }
        else if (sortAsc === first) sortAsc = !first
        else sortKey = ""
    }
    function sorted(items) {
        return TrackSort.sortTracks(items, sortKey, sortAsc, function (t) {
            return (t.plays !== undefined && t.plays !== null) ? t.plays : player.playsOf(t.id)
        })
    }

    implicitHeight: 32
    height: implicitHeight
    Row {   // columna del nombre: «Nombre» y «Artista» (la fila los muestra en dos líneas)
        x: root.nameLeft
        anchors.verticalCenter: parent.verticalCenter
        spacing: 14
        SortLabel { width: 72; text: "Nombre"; key: "name"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("name") }
        SortLabel { width: 72; text: "Artista"; key: "artist"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("artist") }
    }
    Row {   // mismas columnas y anchos que las filas
        anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
        spacing: 16
        SortLabel { visible: root.showAlbum; width: Theme.albumColumn(root.width); text: "\u00c1lbum"; key: "album"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("album") }
        SortLabel { visible: root.showYear; width: Theme.yearColumn; text: "A\u00f1o"; key: "year"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("year") }
        SortLabel { visible: root.showPlays; width: Theme.playsColumn; text: "M\u00e1s escuchadas"; key: "plays"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("plays") }
        SortLabel { width: Theme.durationColumn; text: "Duraci\u00f3n"; align: Text.AlignRight }
    }
    Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom; leftMargin: 12; rightMargin: 12 } height: 1; color: Theme.border }
}
