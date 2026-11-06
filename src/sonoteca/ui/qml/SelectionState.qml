import QtQuick

// Estado de «seleccionar canciones» de una página: qué ids están marcados y si el modo está activo
QtObject {
    id: root
    property bool active: false
    property var picked: ({})
    readonly property int count: Object.keys(picked).length
    function has(id) { return !!picked[id] }
    function toggle(id) {
        var next = Object.assign({}, picked)
        if (next[id]) delete next[id]
        else next[id] = true
        picked = next
    }
    function all(ids) {
        var next = {}
        ids.forEach(function (id) { next[id] = true })
        picked = next
    }
    function clear() { picked = ({}) }
    function start() { clear(); active = true }
    function stop() { clear(); active = false }
    // los marcados, en el orden de `ids`
    function ordered(ids) { return ids.filter(function (id) { return !!picked[id] }) }
}
