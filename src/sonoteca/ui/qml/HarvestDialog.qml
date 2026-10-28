import QtQuick
import QtQuick.Controls
import "."

// Descarga automática de portadas y fotos tras escanear (o desde Archivo). Siempre avisa cuánto puede tardar.
Popup {
    id: root
    property string stage: "intro"        // intro | running | done
    property var plan: ({ albums: 0, artists: 0, total: 0, seconds: 0, duration: "", long: false, offline: false })
    property var summary: ({})
    property int done: 0
    property int total: 0
    property string label: ""
    property real etaSeconds: 0
    property bool manual: false
    signal toastRequested(string text)
    signal internetRequested()
    property alias startButton: startButton   // para las pruebas

    modal: stage !== "running"
    focus: true
    closePolicy: stage === "running" ? Popup.NoAutoClose : Popup.CloseOnEscape
    anchors.centerIn: Overlay.overlay
    width: Math.min(560, Overlay.overlay ? Overlay.overlay.width - 48 : 560)
    padding: 24
    background: Rectangle { color: "#1d1d1f"; radius: 12; border.color: "#2e2e32"; border.width: 1 }
    Overlay.modal: Rectangle { color: "#99000000" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    function fmt(seconds) {
        var m = Math.ceil(seconds / 60)
        if (seconds < 60) return "menos de un minuto"
        if (m < 60) return "unos " + m + " minutos"
        return "unas " + Math.floor(m / 60) + " h " + (m % 60) + " min"
    }
    // Se llama tras escanear (silencioso si no hay nada) o desde el men\u00fa (manual = avisa que no hay nada)
    function offer(isManual) {
        if (harvest.busy) { stage = "running"; open(); return }
        manual = !!isManual
        plan = harvest.plan()
        if (plan.total === 0) {
            if (manual) toastRequested("No hay portadas ni fotos por descargar")
            return
        }
        stage = "intro"
        open()
    }
    function start() {
        done = 0; total = plan.total; label = ""; etaSeconds = plan.seconds
        stage = "running"
        harvest.start()
    }

    Connections {
        target: harvest
        function onProgress(d, t, text, eta) { root.done = d; root.total = t; root.label = text; root.etaSeconds = eta }
        function onFinished(result) {
            root.summary = result
            Theme.dataRevision++
            if (root.visible) root.stage = "done"
            else root.toastRequested(root.summaryText(result))
        }
    }
    function summaryText(r) {
        if (r.error) return "No se pudo completar la descarga: " + r.error
        var t = r.covers + " portadas y " + r.artists + " artistas descargados"
        if (r.cancelled) t += " (cancelado)"
        return t
    }

    contentItem: Column {
        spacing: 14
        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Theme.text
            font.pixelSize: 20
            font.weight: Font.Bold
            text: root.stage === "done" ? "Descarga terminada" : "Descargar portadas e informaci\u00f3n"
        }

        // ---- introducci\u00f3n: qu\u00e9 se va a hacer y cu\u00e1nto tarda ----
        Column {
            width: parent.width
            spacing: 10
            visible: root.stage === "intro"
            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                color: Theme.textDim
                font.pixelSize: 14
                text: "Hay " + Theme.plural(root.plan.albums, "\u00e1lbum", "\u00e1lbumes") + " sin portada y "
                      + Theme.plural(root.plan.artists, "artista", "artistas")
                      + " sin foto ni ficha, con tags bien identificados. Se buscar\u00e1n en MusicBrainz, Cover Art Archive y Wikipedia. "
                      + "No se modifica ning\u00fan archivo de m\u00fasica; las portadas se guardan en la carpeta de datos de Sonoteca."
            }
            Rectangle {
                width: parent.width
                height: timeText.implicitHeight + 20
                radius: 8
                color: root.plan.long ? "#3a2a12" : "#232327"
                border.color: root.plan.long ? "#d9993d" : "#2e2e32"
                Text {
                    id: timeText
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 12 }
                    wrapMode: Text.WordWrap
                    color: root.plan.long ? "#f0c27a" : Theme.text
                    font.pixelSize: 14
                    text: (root.plan.long ? "Es bastante m\u00fasica: " : "") + "tiempo estimado " + root.plan.duration
                          + ". " + (root.plan.long ? "Puedes ocultar esta ventana y seguir usando Sonoteca, o cancelar cuando quieras; lo ya descargado se conserva. " : "")
                          + "Es una estimaci\u00f3n: depende de tu conexi\u00f3n."
                }
            }
            Text {
                visible: root.plan.offline
                width: parent.width
                wrapMode: Text.WordWrap
                color: "#f0c27a"
                font.pixelSize: 13
                text: "El modo sin conexi\u00f3n est\u00e1 activo: activa internet para poder descargar."
            }
        }

        // ---- en curso ----
        Column {
            width: parent.width
            spacing: 10
            visible: root.stage === "running"
            Rectangle {
                width: parent.width; height: 8; radius: 4; color: "#2e2e32"
                Rectangle {
                    height: parent.height; radius: 4; color: Theme.accent
                    width: root.total > 0 ? parent.width * Math.min(1, root.done / root.total) : 0
                }
            }
            Text {
                width: parent.width
                color: Theme.text
                font.pixelSize: 14
                elide: Text.ElideRight
                text: root.done + " de " + root.total + (root.label ? "  \u00b7  " + root.label : "")
            }
            Text {
                width: parent.width
                color: Theme.textDim
                font.pixelSize: 13
                text: "Faltan " + root.fmt(root.etaSeconds) + ". Puedes ocultar esta ventana; avisaremos al terminar."
            }
        }

        // ---- resumen ----
        Column {
            width: parent.width
            spacing: 6
            visible: root.stage === "done"
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.text; font.pixelSize: 14
                   text: root.summary.error ? ("No se pudo completar: " + root.summary.error) : (root.summary.covers + " portadas y " + root.summary.artists + " artistas descargados.") }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 13; visible: (root.summary.unsure || 0) > 0
                   text: root.summary.unsure + " con coincidencia dudosa: no se aplicaron. Elige su portada a mano con \u00abBuscar portada\u00bb en el \u00e1lbum." }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 13; visible: (root.summary.notfound || 0) > 0
                   text: root.summary.notfound + " sin resultado (se volver\u00e1 a intentar dentro de 30 d\u00edas)." }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: "#f0c27a"; font.pixelSize: 13; visible: !!root.summary.offline
                   text: "Se detuvo porque el modo sin conexi\u00f3n est\u00e1 activo." }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: "#f0c27a"; font.pixelSize: 13; visible: !!root.summary.aborted || (root.summary.errors || 0) > 0
                   text: (root.summary.errors || 0) + " errores de red" + (root.summary.aborted ? "; se detuvo tras varios fallos seguidos. Revisa tu conexi\u00f3n y vuelve a intentarlo." : ".") }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 13; visible: !!root.summary.cancelled
                   text: "Cancelado: lo ya descargado se conserva." }
        }

        Row {
            anchors.right: parent.right
            spacing: 10
            PillButton { visible: root.stage === "intro"; label: "Ahora no"; onClicked: root.close() }
            PillButton { visible: root.stage === "intro" && root.plan.offline; label: "Activar internet\u2026"; onClicked: { root.close(); root.internetRequested() } }
            PillButton { id: startButton; visible: root.stage === "intro" && !root.plan.offline; label: "Descargar"; primary: true; onClicked: root.start() }
            PillButton { visible: root.stage === "running"; label: "Cancelar"; onClicked: harvest.cancel() }
            PillButton { visible: root.stage === "running"; label: "Ocultar"; primary: true; onClicked: root.close() }
            PillButton { visible: root.stage === "done"; label: "Cerrar"; primary: true; onClicked: root.close() }
        }
    }
}
