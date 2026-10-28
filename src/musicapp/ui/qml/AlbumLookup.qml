import QtQuick
import QtQuick.Controls
import "."

// Buscar portada e información de un álbum: se elige un candidato y se confirma antes de aplicar
Popup {
    id: root
    property int albumId: 0
    property var trackIds: []
    property var candidates: []
    property int selected: -1
    property int step: 0              // 0 buscando, 1 resultados, 2 descargando la portada
    property string status: ""
    property string error: ""
    property var pendingChanges: ({})
    property alias useCoverItem: useCover  // para las pruebas
    property alias updateTagsItem: updateTags

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 640
    padding: 24
    closePolicy: step === 2 ? Popup.NoAutoClose : (Popup.CloseOnEscape | Popup.CloseOnPressOutside)
    background: Rectangle { color: "#1d1d1f"; radius: 12; border.color: "#2e2e32"; border.width: 1 }
    Overlay.modal: Rectangle { color: "#99000000" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function openFor(id, ids, unknownAlbum) {
        albumId = id
        trackIds = ids
        candidates = []
        selected = -1
        error = ""
        status = "Buscando\u2026"
        step = 0
        useCover.checked = true
        updateTags.checked = unknownAlbum   // en "Sin álbum" lo normal es querer poner el nombre del álbum
        open()
        online.requestAlbumCandidates(id, 0)
    }
    function apply() {
        var cand = candidates[selected]
        var changes = {}
        if (updateTags.checked) {
            changes.album = cand.title
            if (cand.year > 0) changes.year = String(cand.year)
        }
        pendingChanges = changes
        error = ""
        if (useCover.checked) {
            step = 2
            status = "Descargando la portada\u2026"
            online.requestCover(cand.id)
        } else if (Object.keys(changes).length > 0) {
            finish("")
        } else {
            error = "Marca al menos una opción."
        }
    }
    function finish(coverPath) {
        library.applyEdit(trackIds, pendingChanges, coverPath, backupCheck.checked)
        close()
    }

    Connections {
        target: online
        function onProgress(message) { if (root.visible && root.step !== 1) root.status = message }
        function onAlbumCandidatesReady(id, items) {
            if (!root.visible || id !== root.albumId) return
            root.candidates = items
            root.selected = items.length > 0 ? 0 : -1
            root.step = 1
            root.status = items.length > 0 ? "" : "No se encontraron coincidencias en MusicBrainz."
        }
        function onCoverReady(path) { if (root.visible && root.step === 2) root.finish(path) }
        function onOnlineError(message) {
            if (!root.visible) return
            root.error = message
            root.step = 1
        }
    }

    contentItem: Column {
        spacing: 14
        Column {
            width: parent.width
            spacing: 2
            Text { text: "Buscar portada e información"; color: Theme.text; font.pixelSize: 22; font.weight: Font.Bold }
            Text {
                text: "Elige el álbum correcto. Nada se cambia hasta que confirmes."
                color: Theme.textDim
                font.pixelSize: 13
            }
        }
        Text {
            width: parent.width
            visible: root.status !== ""
            text: root.status
            color: Theme.textDim
            font.pixelSize: 13
        }
        ListView {
            id: list
            width: parent.width
            height: Math.min(contentHeight, 330)
            visible: root.candidates.length > 0
            clip: true
            spacing: 6
            model: root.candidates
            delegate: Rectangle {
                width: list.width
                height: 76
                radius: 8
                color: index === root.selected ? "#2e2e32" : (rowMouse.containsMouse ? Theme.surfaceHover : "#232325")
                border.width: index === root.selected ? 1 : 0
                border.color: Theme.accent
                Behavior on color { ColorAnimation { duration: Theme.fast } }
                Rectangle {
                    id: thumb
                    x: 8
                    anchors.verticalCenter: parent.verticalCenter
                    width: 60; height: 60; radius: 4
                    color: "#161617"
                    Image {
                        anchors.fill: parent
                        source: modelData.previewPath ? online.fileUrl(modelData.previewPath) : ""
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                    }
                    Text { anchors.centerIn: parent; visible: !modelData.previewPath; text: "sin\nportada"; color: Theme.textDim; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter }
                }
                Column {
                    anchors { left: thumb.right; leftMargin: 12; right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
                    spacing: 3
                    Text { width: parent.width; text: modelData.title; color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideRight }
                    Text {
                        width: parent.width
                        color: Theme.textDim
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        text: modelData.artist + " \u00b7 " + (modelData.year > 0 ? modelData.year : "????") + (modelData.kind ? " \u00b7 " + modelData.kind : "")
                    }
                    Text {
                        visible: modelData.confident || modelData.lengthMatch
                        color: Theme.accent
                        font.pixelSize: 11
                        text: (modelData.confident ? "Coincidencia probable" : "") + (modelData.confident && modelData.lengthMatch ? " \u00b7 " : "") + (modelData.lengthMatch ? "Misma duración" : "")
                    }
                }
                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.selected = index
                }
            }
            ScrollBar.vertical: ScrollBar { }
        }
        Column {
            width: parent.width
            spacing: 8
            visible: root.candidates.length > 0
            AppCheck { id: useCover; width: parent.width; text: "Poner esta portada en los " + root.trackIds.length + " archivos" }
            AppCheck { id: updateTags; width: parent.width; text: "Actualizar el álbum y el año en los tags" }
            AppCheck { id: backupCheck; width: parent.width; checked: true; text: "Guardar copia de respaldo de los originales" }
        }
        Text { width: parent.width; visible: root.error !== ""; text: root.error; color: "#ff6b6b"; font.pixelSize: 13; wrapMode: Text.WordWrap }
        Text {
            width: parent.width
            visible: root.candidates.length > 0
            text: "Datos de MusicBrainz y portadas de Cover Art Archive."
            color: Theme.textDim
            font.pixelSize: 11
        }
        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { label: "Cancelar"; enabled: root.step !== 2; onClicked: root.close() }
            PillButton { label: "Aplicar"; primary: true; enabled: root.step === 1 && root.selected >= 0; onClicked: root.apply() }
        }
    }
}
