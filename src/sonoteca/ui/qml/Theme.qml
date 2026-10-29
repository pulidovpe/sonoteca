pragma Singleton
import QtQuick

QtObject {
    // ===== Tema «Neón»: paleta tomada del logo (assets/icons/original.png) =====
    // Colores de marca
    readonly property color cyan: "#00d0fc"          // auriculares, copa izquierda
    readonly property color blue: "#0396fd"          // centro del arco
    readonly property color violet: "#9849fd"        // nota musical
    readonly property color magenta: "#ba38fc"       // copa derecha
    // Fondos (azul casi negro, como el icono)
    readonly property color bg: "#060e16"            // fondo de las páginas
    readonly property color sidebar: "#040a10"       // barra lateral
    readonly property color bar: "#050b11"           // barra de menú superior
    readonly property color playerBar: "#0a141d"     // barra de reproducción
    readonly property color surface: "#0c1822"       // tarjetas y fichas
    readonly property color surfaceHover: "#152536"  // al pasar el ratón
    readonly property color surfaceRaised: "#14212e" // botones y campos elevados
    readonly property color panel: "#0f1b27"         // diálogos y menús emergentes
    readonly property color field: "#08121a"         // campos de texto
    readonly property color placeholder: "#101d29"   // portada que aún no carga
    readonly property color heroTop: "#162a44"       // inicio del degradado de las cabeceras
    // Líneas
    readonly property color border: "#1e3043"
    readonly property color divider: "#172636"
    readonly property color track: "#2b3d50"         // ranuras de deslizadores
    // Texto
    readonly property color text: "#f4f9ff"
    readonly property color textSoft: "#c9d6e2"
    readonly property color textDim: "#8da2b6"
    readonly property color textFaint: "#5d7184"     // deshabilitado
    // Acento
    readonly property color accent: cyan
    readonly property color accentHover: "#4fe3ff"
    readonly property color accentSoft: "#0e2d3d"    // fila seleccionada
    readonly property color textOnAccent: "#031018"      // texto o icono sobre el acento
    // Estados
    readonly property color warn: "#f5c26b"
    readonly property color warnBorder: "#e0a23f"
    readonly property color warnBg: "#2f2511"
    readonly property color danger: "#ff6b81"
    readonly property color scrim: "#b0020a12"       // velo detrás de los diálogos
    // Color de una portada sin imagen: tono estable por id dentro de la gama cian → violeta del logo
    function coverColor(id) { return Qt.hsla((185 + ((id * 61) % 105)) / 360, 0.55, 0.28, 1) }

    // Iconos del menú lateral
    readonly property string iconHome: "M12 3 L2 12 H5 V20 H10 V15 H14 V20 H19 V12 H22 Z"
    readonly property string iconAlbum: "M12 3 A9 9 0 1 0 12 21 A9 9 0 1 0 12 3 Z M12 6.5 A5.5 5.5 0 1 1 12 17.5 A5.5 5.5 0 1 1 12 6.5 Z M12 10 A2 2 0 1 0 12 14 A2 2 0 1 0 12 10 Z"
    readonly property string iconArtist: "M12 4 A4 4 0 1 0 12 12 A4 4 0 1 0 12 4 Z M4 20 C4 15.5 8 14 12 14 C16 14 20 15.5 20 20 Z"
    readonly property string iconList: "M9 6 H21 V8 H9 Z M9 11 H21 V13 H9 Z M9 16 H21 V18 H9 Z M3 6 H6 V8 H3 Z M3 11 H6 V13 H3 Z M3 16 H6 V18 H3 Z"
    readonly property string iconQueue: "M4 12 H8 V20 H4 Z M10 4 H14 V20 H10 Z M16 9 H20 V20 H16 Z"
    readonly property string iconLyrics: "M4 5 H20 V7 H4 Z M4 10 H16 V12 H4 Z M4 15 H20 V17 H4 Z M4 20 H12 V22 H4 Z"
    readonly property string iconReview: "M12 3 A9 9 0 1 0 12 21 A9 9 0 1 0 12 3 Z M11 7 H13 V13 H11 Z M11 15 H13 V17 H11 Z"
    readonly property string iconGlobe: "M12 3 A9 9 0 1 0 12 21 A9 9 0 1 0 12 3 Z M12 4.8 A7.2 7.2 0 1 1 12 19.2 A7.2 7.2 0 1 1 12 4.8 Z M4.8 11 H19.2 V13 H4.8 Z M12 4.8 A3.5 7.2 0 1 0 12 19.2 A3.5 7.2 0 1 0 12 4.8 Z M12 6.3 A2 5.7 0 1 1 12 17.7 A2 5.7 0 1 1 12 6.3 Z"
    readonly property string iconPlay: "M8 4 L20 12 L8 20 Z"
    readonly property string iconPause: "M6 4 H10 V20 H6 Z M14 4 H18 V20 H14 Z"
    readonly property string iconNext: "M5 4 L16 12 L5 20 Z M17 4 H20 V20 H17 Z"
    readonly property string iconPrev: "M19 4 L8 12 L19 20 Z M4 4 H7 V20 H4 Z"
    readonly property string iconClose: "M7 5 L12 10 L17 5 L19 7 L14 12 L19 17 L17 19 L12 14 L7 19 L5 17 L10 12 L5 7 Z"
    // Sube cuando cambian los datos (p. ej. tras editar tags); las páginas lo leen para refrescarse
    property int dataRevision: 0
    readonly property string iconHeadphones: "M12 3 A9 9 0 0 0 3 12 V19 A2 2 0 0 0 5 21 H7 V13 H5 V12 A7 7 0 0 1 19 12 V13 H17 V21 H19 A2 2 0 0 0 21 19 V12 A9 9 0 0 0 12 3 Z"
    readonly property string iconDisplay: "M3 4 H21 V16 H3 Z M5 6 V14 H19 V6 Z M8 18 H16 V20 H8 Z"
    readonly property string iconSpeaker: "M3 9 H7 L12 4 V20 L7 15 H3 Z M14.5 8.5 A5 5 0 0 1 14.5 15.5 L16 17 A7 7 0 0 0 16 7 Z"
    // Caja acústica (salida de audio): distinta del altavoz con ondas, que es el volumen
    readonly property string iconMuted: "M3 9 H7 L12 4 V20 L7 15 H3 Z M14.5 9.9 L15.9 8.5 L18 10.6 L20.1 8.5 L21.5 9.9 L19.4 12 L21.5 14.1 L20.1 15.5 L18 13.4 L15.9 15.5 L14.5 14.1 L16.6 12 Z"
    readonly property string iconSpeakerBox: "M6 3 H18 A1 1 0 0 1 19 4 V20 A1 1 0 0 1 18 21 H6 A1 1 0 0 1 5 20 V4 A1 1 0 0 1 6 3 Z M7 5 V19 H17 V5 Z M12 6.5 A1.5 1.5 0 1 0 12 9.5 A1.5 1.5 0 1 0 12 6.5 Z M12 11 A3.5 3.5 0 1 0 12 18 A3.5 3.5 0 1 0 12 11 Z"
    readonly property string iconMore: "M12 4 A2 2 0 1 0 12 8 A2 2 0 1 0 12 4 Z M12 10 A2 2 0 1 0 12 14 A2 2 0 1 0 12 10 Z M12 16 A2 2 0 1 0 12 20 A2 2 0 1 0 12 16 Z"
    readonly property string iconUp: "M12 7 L19 17 L5 17 Z"
    readonly property string iconDown: "M12 17 L19 7 L5 7 Z"
    readonly property int radius: 10
    readonly property int fast: 160
    readonly property int slow: 320

    // plural(1, "pista", "pistas") -> "1 pista"
    function plural(n, one, many) { return n + " " + (n === 1 ? one : many) }

    // 4:20, 1:05:03
    function fmt(seconds) {
        var s = Math.round(seconds)
        var h = Math.floor(s / 3600)
        var m = Math.floor((s % 3600) / 60)
        var sec = s % 60
        var mm = (h > 0 && m < 10 ? "0" : "") + m
        return (h > 0 ? h + ":" + mm : mm) + ":" + (sec < 10 ? "0" : "") + sec
    }

    // 52 min, 1 h 05 min
    function fmtLong(seconds) {
        var mins = Math.round(seconds / 60)
        var h = Math.floor(mins / 60)
        var m = mins % 60
        return h > 0 ? h + " h " + (m < 10 ? "0" : "") + m + " min" : mins + " min"
    }
}
