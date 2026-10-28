import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "."

// Cuando la información descargada es de otro artista: elegir el artículo correcto de Wikipedia
// (como al buscar portadas) o escribir una descripción propia, con imagen opcional.
Popup {
    id: root
    property int artistId: 0
    property string artistName: ""
    property string mode: "search"        // search | manual
    property var candidates: []
    property int selected: -1
    property bool searching: false
    property string status: ""
    property string error: ""
    property string imagePath: ""
    signal applied()
    // Para las pruebas
    property alias queryItem: queryField
    property alias descriptionItem: descriptionField

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: 640
    padding: 24
    closePolicy: searching ? Popup.NoAutoClose : (Popup.CloseOnEscape | Popup.CloseOnPressOutside)
    background: Rectangle { color: "#1d1d1f"; radius: 12; border.color: "#2e2e32"; border.width: 1 }
    Overlay.modal: Rectangle { color: "#99000000" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function openFor(id, name, existingBio) {
        artistId = id
        artistName = name
        candidates = []
        selected = -1
        error = ""
        status = ""
        imagePath = ""
        searching = false
        queryField.text = name
        descriptionField.text = existingBio || ""
        mode = "search"
        open()
        search()
    }
    function search() {
        error = ""
        if (online.offline) { status = "Sin conexi\u00f3n: activa internet para buscar, o escribe tu propia descripci\u00f3n."; return }
        searching = true
        selected = -1
        candidates = []
        status = "Buscando\u2026"
        online.requestArtistCandidates(artistId, queryField.text)
    }
    function useSelected() {
        if (selected < 0) return
        searching = true
        status = "Aplicando\u2026"
        online.applyArtistCandidate(artistId, candidates[selected])
    }
    function saveManual() {
        var result = online.saveManualArtistInfo(artistId, descriptionField.text, imagePath)
        if (!result.ok) { error = result.error; return }
        applied()
        close()
    }

    Connections {
        target: online
        function onArtistCandidatesReady(id, list) {
            if (id !== root.artistId || !root.searching) return
            root.searching = false
            root.candidates = list
            root.status = list.length > 0 ? "" : "No se encontraron art\u00edculos. Prueba con otro nombre o escribe una descripci\u00f3n."
        }
        function onArtistInfoReady(id, data) {
            if (id !== root.artistId || !root.searching) return
            root.searching = false
            root.applied()
            root.close()
        }
        function onOnlineError(message) {
            if (root.searching) { root.searching = false; root.status = ""; root.error = message }
        }
        function onProgress(message) { if (root.searching) root.status = message }
    }
    FileDialog {
        id: imageDialog
        title: "Elegir imagen del artista"
        nameFilters: ["Im\u00e1genes (*.jpg *.jpeg *.png)"]
        onAccepted: root.imagePath = library.localPath(selectedFile.toString())
    }

    contentItem: Column {
        spacing: 14
        Column {
            width: parent.width
            spacing: 2
            Text { text: "Elegir el artista correcto"; color: Theme.text; font.pixelSize: 22; font.weight: Font.Bold }
            Text { width: parent.width; text: "Para \u00ab" + root.artistName + "\u00bb"; color: Theme.textDim; font.pixelSize: 13; elide: Text.ElideRight }
        }
        Row {
            spacing: 8
            Chip { label: "Buscar en Wikipedia"; active: root.mode === "search"; onClicked: root.mode = "search" }
            Chip { label: "Escribir descripci\u00f3n"; active: root.mode === "manual"; onClicked: root.mode = "manual" }
        }

        // ---- Buscar en Wikipedia ----
        Column {
            width: parent.width
            spacing: 10
            visible: root.mode === "search"
            Row {
                width: parent.width
                spacing: 8
                TextField {
                    id: queryField
                    width: parent.width - searchButton.width - 8
                    height: 36
                    color: Theme.text
                    placeholderText: "Nombre del artista"
                    placeholderTextColor: Theme.textDim
                    font.pixelSize: 14
                    leftPadding: 12
                    background: Rectangle { radius: 18; color: Theme.surface; border.color: queryField.activeFocus ? Theme.accent : "#2e2e32" }
                    onAccepted: root.search()
                }
                PillButton { id: searchButton; height: 36; enabled: !root.searching; label: "Buscar"; onClicked: root.search() }
            }
            ListView {
                id: candidateList
                width: parent.width
                height: 250
                clip: true
                spacing: 4
                model: root.candidates
                delegate: Rectangle {
                    width: candidateList.width
                    height: 76
                    radius: 8
                    color: index === root.selected ? "#2a3a30" : (rowMouse.containsMouse ? Theme.surfaceHover : Theme.surface)
                    border.width: index === root.selected ? 1 : 0
                    border.color: Theme.accent
                    Column {
                        anchors { fill: parent; margins: 10 }
                        spacing: 3
                        Row {
                            spacing: 8
                            Text { text: modelData.name; color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                            Text { text: modelData.language.toUpperCase() + (modelData.description ? " \u00b7 " + modelData.description : ""); color: Theme.accent; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                        }
                        Text {
                            width: parent.width
                            text: modelData.summary
                            color: Theme.textDim
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                        }
                    }
                    MouseArea { id: rowMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.selected = index }
                }
                ScrollBar.vertical: ScrollBar { }
            }
            Row {
                anchors.right: parent.right
                spacing: 10
                PillButton { primary: true; enabled: root.selected >= 0 && !root.searching; label: "Usar este artista"; onClicked: root.useSelected() }
            }
        }

        // ---- Escribir descripci\u00f3n ----
        Column {
            width: parent.width
            spacing: 10
            visible: root.mode === "manual"
            Rectangle {
                width: parent.width
                height: 190
                radius: 8
                color: Theme.surface
                border.color: descriptionField.activeFocus ? Theme.accent : "#2e2e32"
                ScrollView {
                    anchors { fill: parent; margins: 6 }
                    TextArea {
                        id: descriptionField
                        color: Theme.text
                        placeholderText: "Escribe aqu\u00ed la descripci\u00f3n del artista\u2026"
                        placeholderTextColor: Theme.textDim
                        font.pixelSize: 14
                        wrapMode: TextEdit.Wrap
                        background: null
                    }
                }
            }
            Row {
                spacing: 12
                PillButton { height: 34; label: root.imagePath ? "Cambiar imagen\u2026" : "Elegir imagen\u2026"; onClicked: imageDialog.open() }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 300
                    visible: root.imagePath !== ""
                    text: root.imagePath.split("/").pop().split("\\").pop()
                    color: Theme.textDim
                    font.pixelSize: 12
                    elide: Text.ElideMiddle
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.imagePath !== ""
                    text: "Quitar"
                    color: Theme.accent
                    font.pixelSize: 12
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.imagePath = "" }
                }
            }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 11; text: "La imagen es opcional (JPG o PNG, hasta 5 MB). Si no eliges ninguna, se conserva la foto actual." }
            Row {
                anchors.right: parent.right
                spacing: 10
                PillButton { primary: true; enabled: descriptionField.text.trim() !== ""; label: "Guardar descripci\u00f3n"; onClicked: root.saveManual() }
            }
        }

        Text { width: parent.width; visible: root.status !== ""; text: root.status; color: Theme.textDim; font.pixelSize: 13; wrapMode: Text.WordWrap }
        Text { width: parent.width; visible: root.error !== ""; text: root.error; color: "#ff6b6b"; font.pixelSize: 13; wrapMode: Text.WordWrap }
        Row {
            anchors.right: parent.right
            PillButton { label: "Cerrar"; enabled: !root.searching; onClicked: root.close() }
        }
    }
}
