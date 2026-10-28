pragma Singleton
import QtQuick

QtObject {
    readonly property color bg: "#0f0f10"
    readonly property color sidebar: "#000000"
    readonly property color surface: "#181819"
    readonly property color surfaceHover: "#262628"
    readonly property color text: "#ffffff"
    readonly property color textDim: "#a7a7ab"
    readonly property color accent: "#1ed760"
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
