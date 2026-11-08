import QtQuick
import "."
import "TrackSort.js" as TrackSort

// Primera fila de una lista de canciones: títulos de columna que ordenan. Se alinea con las filas (`TrackRow` / `ListTrackRow`)
// usando los mismos anchos y umbrales. Un clic ordena; otro invierte; el tercero vuelve al orden original (en «Reproducciones» el
// primer clic pone las más escuchadas primero).
//   · Normal: Nombre · [Artista, si la ventana es ancha] · Álbum · Año · Más escuchadas · En lista · Duración. Si el artista no
//     tiene columna propia (ventana estrecha) va debajo del nombre y el título de la columna es «Nombre · Artista».
//   · `review` (Por revisar): Nombre · Tags · Tipo · Duración, sin recortar el nombre.
Item {
    id: root
    property bool hasNumber: false          // filas con columna de número (o casilla de selección)
    property int nameLeft: 28 + (hasNumber ? 44 : 0)      // dónde empieza la columna del nombre (112 en `ListTrackRow`)
    property bool hasArtist: true
    property bool hasAlbum: true
    property bool hasYear: true
    property bool hasPlays: true
    property bool hasInList: true           // false en listas guardadas (todas las canciones están en la lista)
    property bool review: false
    property string sortKey: ""
    property bool sortAsc: true
    readonly property int tier: Theme.tier(width)
    readonly property bool showArtistColumn: !review && hasArtist && width >= Theme.artistMin
    readonly property bool showAlbum: !review && hasAlbum && tier >= 2
    readonly property bool showYear: !review && hasYear && width >= Theme.yearMin
    readonly property bool showPlays: !review && hasPlays && width >= Theme.playsMin
    readonly property bool showInList: !review && hasInList && width >= Theme.inListMin

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
    Row {   // columna del nombre
        x: root.nameLeft
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6
        SortLabel { width: root.showArtistColumn || root.review || !root.hasArtist ? 80 : 58; text: "Nombre"; key: "name"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("name") }
        Text { visible: !root.showArtistColumn && !root.review && root.hasArtist; anchors.verticalCenter: parent.verticalCenter; text: "\u00b7"; color: Theme.textDim; font.pixelSize: 12 }
        SortLabel { visible: !root.showArtistColumn && !root.review && root.hasArtist; width: 58; text: "Artista"; key: "artist"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("artist") }
    }
    Row {   // mismas columnas y anchos que las filas
        anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
        spacing: 16
        SortLabel { visible: root.showArtistColumn; width: Theme.artistColumn(root.width); text: "Artista"; key: "artist"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("artist") }
        SortLabel { visible: root.showAlbum; width: Theme.albumColumn(root.width); text: "\u00c1lbum"; key: "album"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("album") }
        SortLabel { visible: root.showYear; width: Theme.yearColumn; text: "A\u00f1o"; key: "year"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("year") }
        SortLabel { visible: root.showPlays; width: Theme.playsColumn; text: "M\u00e1s escuchadas"; key: "plays"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("plays") }
        SortLabel { visible: root.showInList; width: Theme.inListColumn; text: "En lista"; align: Text.AlignHCenter }
        SortLabel { visible: root.review; width: Theme.reviewColumn; text: "Tags"; key: "tags"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("tags") }
        SortLabel { visible: root.review; width: Theme.reviewColumn; text: "Tipo"; key: "kind"; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("kind") }
        SortLabel { width: Theme.durationColumn; text: "Duraci\u00f3n"; align: Text.AlignRight; key: root.review ? "duration" : ""; current: root.sortKey; asc: root.sortAsc; onClicked: root.toggle("duration") }
    }
    Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom; leftMargin: 12; rightMargin: 12 } height: 1; color: Theme.border }
}
