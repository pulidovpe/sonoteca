import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "."

Popup {
    id: root
    property var ids: []
    property var info: ({})
    property int step: 0              // 0 formulario, 1 revisión, 2 guardando (al terminar se cierra solo)
    property var reviewData: ({ lines: [], count: 0, error: "" })
    property var result: ({})
    property var pending: ({})
    property string error: ""
    property string coverPath: ""
    property int artistId: 0           // > 0: se edita a un artista (la imagen actual es su foto)
    property string artistName: ""
    property var coverState: ({ state: "none", source: "" })   // portada que tienen hoy las pistas
    property int done: 0
    property int total: 0
    readonly property bool single: ids.length === 1
    // Para las pruebas de interfaz
    property alias coverNameItem: coverName
    property alias removeCoverItem: removeCover
    property alias currentThumbItem: currentImage
    property alias newThumbItem: newImage
    function fieldCursor(key) {
        for (var i = 0; i < fields.count; i++) {
            if (fields.itemAt(i).key === key) return fields.itemAt(i).cursor
        }
        return -1
    }
    readonly property var fieldDefs: [
        { key: "title", label: "Título", singleOnly: true },
        { key: "artist", label: "Artista" },
        { key: "album_artist", label: "Artista del álbum" },
        { key: "album", label: "Álbum" },
        { key: "year", label: "Año", number: true },
        { key: "track_no", label: "Nº de pista", number: true, singleOnly: true },
        { key: "disc_no", label: "Nº de disco", number: true },
        { key: "genre", label: "Género" }
    ]

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 580
    padding: 24
    closePolicy: step === 2 ? Popup.NoAutoClose : (Popup.CloseOnEscape | Popup.CloseOnPressOutside)
    background: Rectangle { color: Theme.panel; radius: 12; border.color: Theme.border; border.width: 1 }
    Overlay.modal: Rectangle { color: Theme.scrim }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function openFor(newIds, newArtistId, newArtistName) {
        ids = newIds
        artistId = newArtistId || 0
        artistName = newArtistName || ""
        info = library.tagValues(newIds)
        coverState = library.coverPreview(newIds, artistId)
        step = 0
        error = ""
        coverPath = ""
        pending = ({})
        done = 0
        total = 0
        for (var i = 0; i < fields.count; i++) {
            var f = fields.itemAt(i)
            var d = info[f.key]
            f.reset(d ? d.value : "", d ? d.mixed : false)
        }
        open()
    }
    function collect() {
        var c = {}
        for (var i = 0; i < fields.count; i++) {
            var f = fields.itemAt(i)
            if (f.visible && f.touched) c[f.key] = f.text
        }
        return c
    }
    function setField(key, text) {
        for (var i = 0; i < fields.count; i++) {
            var f = fields.itemAt(i)
            if (f.key === key) { f.text = text; f.touched = true }
        }
    }
    function goReview() {
        pending = collect()
        var p = library.previewEdit(ids, pending, coverPath)
        if (p.error) { error = p.error; return }
        error = ""
        reviewData = p
        step = 1
    }
    function apply() {
        done = 0
        total = ids.length
        step = 2
        library.applyEdit(ids, pending, coverPath, backupBox.checked)
    }

    FileDialog {
        id: coverDialog
        title: "Elegir portada"
        nameFilters: ["Imágenes (*.jpg *.jpeg *.png)"]
        onAccepted: root.coverPath = library.localPath(selectedFile.toString())
    }

    contentItem: Column {
        spacing: 14

        Column {
            width: parent.width
            spacing: 2
            Text { text: "Editar tags"; color: Theme.text; font.pixelSize: 22; font.weight: Font.Bold }
            Text {
                width: parent.width
                color: Theme.textDim
                font.pixelSize: 13
                elide: Text.ElideRight
                text: root.single ? (root.info.title ? root.info.title.value : "")
                                  : (root.artistId > 0 && root.artistName !== "" ? root.artistName + " \u00b7 " : "")
                                    + Theme.plural(root.ids.length, "pista", "pistas") + " seleccionadas"
            }
        }

        // ---- Paso 0: formulario ----
        Column {
            width: parent.width
            spacing: 14
            visible: root.step === 0
            Text {
                width: parent.width
                color: Theme.textDim
                font.pixelSize: 12
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                text: root.single ? "Solo se guardan los campos que modifiques (se marcan en verde)."
                                  : "Solo se cambian los campos que modifiques. Los que dicen \u201c(varios valores)\u201d se dejan como están salvo que los edites."
            }
            GridLayout {
                width: parent.width
                columns: 2
                columnSpacing: 12
                rowSpacing: 10
                Repeater {
                    id: fields
                    model: root.fieldDefs
                    delegate: EditorField {
                        key: modelData.key
                        label: modelData.label
                        number: modelData.number === true
                        visible: !modelData.singleOnly || root.single
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1   // reparto igual entre las dos columnas
                        Layout.columnSpan: modelData.key === "title" ? 2 : 1
                    }
                }
            }
            // Imagen que hay hoy y, si se elige otra, la nueva al lado
            Row {
                id: coverPreviewRow
                spacing: 16
                Column {
                    spacing: 6
                    Text {
                        text: root.artistId > 0 ? "Foto actual" : "Portada actual"
                        color: Theme.textDim
                        font.pixelSize: 12
                    }
                    Rectangle {
                        width: 96; height: 96; radius: 6
                        color: Theme.surfaceRaised
                        Image {
                            id: currentImage
                            anchors.fill: parent
                            visible: root.coverState.state === "single"
                            source: root.coverState.state === "single"
                                    ? root.coverState.source + "?v=" + Theme.dataRevision : ""
                            sourceSize.width: 192
                            sourceSize.height: 192
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                        }
                        Text {
                            anchors.centerIn: parent
                            width: parent.width - 12
                            visible: root.coverState.state !== "single"
                            text: root.coverState.state === "mixed" ? "(varias portadas)" : "Sin portada"
                            color: Theme.textDim
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                        }
                    }
                }
                Text {
                    visible: root.coverPath !== ""
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.verticalCenterOffset: 10
                    text: "\u2192"
                    color: Theme.textDim
                    font.pixelSize: 24
                }
                Column {
                    visible: root.coverPath !== ""
                    spacing: 6
                    Text { text: "Nueva"; color: Theme.accent; font.pixelSize: 12; font.weight: Font.DemiBold }
                    Rectangle {
                        width: 96; height: 96; radius: 6
                        color: Theme.surfaceRaised
                        border.width: 1
                        border.color: Theme.accent
                        Image {
                            id: newImage
                            anchors.fill: parent
                            anchors.margins: 1
                            source: root.coverPath !== "" ? online.fileUrl(root.coverPath) : ""
                            sourceSize.width: 192
                            sourceSize.height: 192
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                        }
                    }
                }
            }
            Text {
                width: parent.width
                visible: root.artistId > 0 && root.coverPath !== ""
                text: "La imagen nueva se guarda como portada en los archivos de este artista; su foto de Wikipedia no cambia."
                color: Theme.textDim
                font.pixelSize: 12
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }
            RowLayout {
                width: parent.width
                spacing: 10
                PillButton { label: "Cambiar portada\u2026"; onClicked: coverDialog.open() }
                Text {
                    id: coverName
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    visible: root.coverPath !== ""
                    text: root.coverPath.split("/").pop().split("\\").pop()
                    elide: Text.ElideMiddle   // conserva el inicio y la extensión (.jpg)
                    color: Theme.accent
                    font.pixelSize: 12
                }
                Item { Layout.fillWidth: true; visible: root.coverPath === "" }
                PillButton { id: removeCover; visible: root.coverPath !== ""; label: "Quitar"; onClicked: root.coverPath = "" }
            }
            Text {
                width: parent.width
                visible: root.error !== ""
                text: root.error
                color: Theme.danger
                font.pixelSize: 13
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }
            Row {
                spacing: 10
                anchors.right: parent.right
                PillButton { label: "Cancelar"; onClicked: root.close() }
                PillButton { label: "Revisar cambios"; primary: true; onClicked: root.goReview() }
            }
        }

        // ---- Paso 1: revisión ----
        Column {
            width: parent.width
            spacing: 12
            visible: root.step === 1
            Text {
                text: "Se modificarán " + Theme.plural(root.reviewData.count, "archivo", "archivos") + ":"
                color: Theme.text
                font.pixelSize: 14
            }
            Rectangle {
                width: parent.width
                height: reviewCol.height + 24
                radius: 8
                color: Theme.surfaceRaised
                Column {
                    id: reviewCol
                    x: 12
                    y: 12
                    width: parent.width - 24
                    spacing: 6
                    Repeater {
                        model: root.reviewData.lines
                        delegate: Text {
                            width: reviewCol.width
                            text: modelData
                            color: Theme.text
                            font.pixelSize: 13
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                    }
                }
            }
            CheckBox {
                id: backupBox
                checked: true
                text: "Guardar copia de respaldo de los originales"
                indicator: Rectangle {
                    implicitWidth: 18
                    implicitHeight: 18
                    x: backupBox.leftPadding
                    y: backupBox.height / 2 - height / 2
                    radius: 4
                    color: backupBox.checked ? Theme.accent : "transparent"
                    border.color: backupBox.checked ? Theme.accent : Theme.textDim
                    Text { anchors.centerIn: parent; text: "\u2713"; visible: backupBox.checked; color: Theme.onAccent; font.pixelSize: 12; font.weight: Font.Bold }
                }
                contentItem: Text {
                    text: backupBox.text
                    color: Theme.text
                    font.pixelSize: 13
                    leftPadding: backupBox.indicator.width + 10
                    verticalAlignment: Text.AlignVCenter
                }
            }
            Row {
                spacing: 10
                anchors.right: parent.right
                PillButton { label: "Atrás"; onClicked: root.step = 0 }
                PillButton { label: "Aplicar cambios"; primary: true; onClicked: root.apply() }
            }
        }

        // ---- Paso 2: guardando ----
        Column {
            width: parent.width
            spacing: 12
            visible: root.step === 2
            Text { text: "Guardando\u2026 " + root.done + " de " + root.total; color: Theme.text; font.pixelSize: 14 }
            ProgressBar {
                id: bar
                width: parent.width
                from: 0
                to: Math.max(1, root.total)
                value: root.done
                background: Rectangle { implicitHeight: 6; radius: 3; color: Theme.track }
                contentItem: Item {
                    Rectangle { width: bar.visualPosition * parent.width; height: parent.height; radius: 3; color: Theme.accent }
                }
            }
            Text { text: "No cierres la aplicación hasta que termine."; color: Theme.textDim; font.pixelSize: 12 }
        }
    }
}
