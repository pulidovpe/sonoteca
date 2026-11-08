import QtQuick
import "."

// Fila de canción. Columnas según el ancho (Theme.tier): pista · nombre con el artista debajo · álbum · año · reproducciones.
// Ancho amplio: todas; medio: hasta el álbum (+ año); estrecho: pista, nombre y año. La duración y el menú ⋮ se mantienen siempre.
Item {
    id: root
    property string number: ""
    property string title
    // artist: si la página no lo da (undefined) no hay artista; con ancho amplio tiene su propia columna y si no va debajo del
    // nombre (en ambos casos es un enlace a la página del artista)
    property var artist: undefined
    // album y year: si la página no los da (undefined) no hay columna; si los da, la columna existe en TODAS las filas
    // (aunque una canción no tenga el dato), para que las columnas queden alineadas entre canciones
    property var album: undefined
    property var year: undefined
    property string subtitle: ""    // texto libre cuando no hay artista (p. ej. «Por revisar»)
    property string badge: ""
    property string duration: ""
    property int plays: -1          // < 0: no se muestra
    property int trackId: 0         // > 0: se puede arrastrar a una lista de la barra lateral
    property bool current: false
    property bool inListColumn: true    // columna «En lista» (ancho medio o mayor)
    // Lista «Por revisar»: si la página los da, hay columnas «Tags» (¿ya tiene tags?) y «Tipo» (video o música)
    property var hasTags: undefined
    property var isVideo: undefined
    // modo «seleccionar canciones»: casilla a la izquierda; un clic marca/desmarca
    property bool selectable: false
    property bool selected: false
    signal toggled()
    function openAlbum() {
        var info = library.trackInfo(trackId)
        if (info && info.hasAlbum && info.albumId > 0) NavBus.albumRequested(info.albumId)
    }
    function openArtist() {
        var info = library.trackInfo(trackId)
        if (info && info.hasArtist && info.artistId > 0) NavBus.artistRequested(info.artistId, info.artist)
    }
    signal activated()
    signal contextRequested()
    readonly property int tier: Theme.tier(width)
    readonly property bool showAlbum: tier >= 2 && album !== undefined
    readonly property bool showYear: width >= Theme.yearMin && year !== undefined
    readonly property bool showPlays: width >= Theme.playsMin && plays >= 0
    readonly property bool showArtistColumn: artist !== undefined && width >= Theme.artistMin
    readonly property bool showInList: inListColumn && trackId >= 0 && width >= Theme.inListMin
    readonly property bool showReview: hasTags !== undefined
    readonly property bool inList: (playlists.revision, trackId > 0 && playlists.inLists(trackId))
    readonly property bool line2IsArtist: !showArtistColumn && artist !== undefined && artist !== ""
    readonly property string line2: line2IsArtist ? artist : subtitle
    height: 52
    opacity: dragHandler.active ? 0.45 : 1

    HoverHandler { id: rowHover; enabled: !DragState.inputBlocked }
    TrackDragHandler { id: dragHandler; ids: root.trackId > 0 && !root.selectable ? [root.trackId] : []; label: root.title }

    Rectangle {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        radius: 6
        color: root.selected ? Theme.accentSoft : (mouse.containsMouse ? Theme.surfaceHover : "transparent")
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    Text {
        id: num
        text: root.number
        x: 28
        width: (root.selectable || root.number !== "") ? 36 : 0
        visible: !root.selectable
        anchors.verticalCenter: parent.verticalCenter
        color: Theme.textDim
        font.pixelSize: 14
    }
    Rectangle {   // casilla del modo selección
        visible: root.selectable
        x: 28
        width: 20
        height: 20
        radius: 4
        anchors.verticalCenter: parent.verticalCenter
        color: root.selected ? Theme.accent : "transparent"
        border.color: root.selected ? Theme.accent : Theme.textDim
        border.width: 2
        Text { anchors.centerIn: parent; visible: root.selected; text: "\u2713"; color: Theme.textOnAccent; font.pixelSize: 14; font.weight: Font.Bold }
    }
    Column {
        anchors.left: num.right
        anchors.leftMargin: (root.selectable || root.number !== "") ? 8 : 0
        anchors.right: moreButton.left
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        Item {   // título; la etiqueta (p. ej. VIDEO) va al final de esta columna, sin desplazar las demás
            width: parent.width
            height: titleText.implicitHeight
            Text {
                id: titleText
                anchors { left: parent.left; right: badgeBox.visible ? badgeBox.left : parent.right; rightMargin: badgeBox.visible ? 8 : 0 }
                text: root.title
                color: root.current ? Theme.accent : Theme.text
                font.pixelSize: 15
                elide: Text.ElideRight
            }
            Rectangle {
                id: badgeBox
                visible: root.badge !== ""
                anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                width: badgeText.width + 14
                height: 20
                radius: 4
                color: "transparent"
                border.color: Theme.textDim
                border.width: 1
                Text {
                    id: badgeText
                    anchors.centerIn: parent
                    text: root.badge
                    color: Theme.textDim
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                }
            }
        }
        LinkText {   // segunda línea: el artista (enlace) o, si no hay, el texto libre
            width: parent.width
            visible: root.line2 !== ""
            text: root.line2
            font.pixelSize: 12
            linkEnabled: root.line2IsArtist && root.trackId > 0 && !root.selectable
            onClicked: root.openArtist()
        }
    }
    // Columnas de la derecha, en este orden: artista (solo ancho amplio), álbum, año, reproducciones, «En lista», [Tags y Tipo en Por
    // revisar] y duración (todas de ancho fijo)
    Row {
        id: cells
        z: 1                                  // por encima del MouseArea de toda la fila: si no, tapa el enlace del álbum
        anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
        spacing: 16
        LinkText {   // el artista, en su propia columna cuando la ventana es ancha (si no, va debajo del nombre)
            visible: root.showArtistColumn
            width: Theme.artistColumn(root.width)
            text: root.artist ? root.artist : ""
            font.pixelSize: 13
            linkEnabled: root.trackId > 0 && !root.selectable
            onClicked: root.openArtist()
        }
        LinkText {   // el álbum es un enlace a su página
            visible: root.showAlbum
            width: Theme.albumColumn(root.width)
            text: root.album ? root.album : ""
            font.pixelSize: 13
            linkEnabled: root.trackId > 0 && !root.selectable
            onClicked: root.openAlbum()
        }
        Text {
            visible: root.showYear
            width: Theme.yearColumn
            text: root.year ? root.year : ""
            color: Theme.textDim
            font.pixelSize: 13
        }
        Text {
            visible: root.showPlays
            width: Theme.playsColumn
            text: "\u25b6 " + root.plays
            color: Theme.textDim
            font.pixelSize: 12
        }
        Item {   // «En lista»: ✓ si la canción ya está en alguna lista guardada (el tooltip dice en cuáles)
            visible: root.showInList
            width: Theme.inListColumn
            height: 20
            Text { anchors.centerIn: parent; text: root.inList ? "\u2713" : ""; color: Theme.accent; font.pixelSize: 15; font.weight: Font.Bold }
            HoverHandler { id: inListHover }
            AppToolTip { visible: inListHover.hovered && root.inList; text: "Est\u00e1 en: " + playlists.listNames(root.trackId).join(", ") }
        }
        Text {   // Por revisar: ¿ya tiene tags?
            visible: root.showReview
            width: Theme.reviewColumn
            text: root.hasTags ? "Con tags" : "Sin tags"
            color: root.hasTags ? Theme.accent : Theme.warn
            font.pixelSize: 13
        }
        Text {   // Por revisar: video o música
            visible: root.showReview
            width: Theme.reviewColumn
            text: root.isVideo ? "Video" : "M\u00fasica"
            color: Theme.textDim
            font.pixelSize: 13
        }
        Text {
            id: dur
            text: root.duration
            width: Theme.durationColumn
            horizontalAlignment: Text.AlignRight
            color: Theme.textDim
            font.pixelSize: 14
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: !DragState.inputBlocked
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: (m) => {
            if (m.button === Qt.RightButton) root.contextRequested()
            else if (root.selectable) root.toggled()
        }
        onDoubleClicked: (m) => { if (m.button === Qt.LeftButton && !root.selectable) root.activated() }
    }
    // Botón de opciones (⋮): aparece al pasar el ratón y abre el menú con todas las acciones
    IconButton {
        id: moreButton
        width: 28
        height: 28
        iconSize: 16
        svg: Theme.iconMore
        enabled: rowHover.hovered
        opacity: rowHover.hovered ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        anchors.right: cells.left
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        onClicked: root.contextRequested()
    }
}
