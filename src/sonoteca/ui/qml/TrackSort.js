.pragma library

// Orden de las listas de canciones (cabeceras de columna). Sin estado: recibe la lista y devuelve una copia ordenada.
// Claves: name (título), artist, album, year, plays. `playsOf(t)` da las reproducciones de una pista.

function fold(value) {
    var s = (value === undefined || value === null) ? "" : String(value)
    s = s.toLowerCase()
    if (s.normalize) s = s.normalize("NFD").replace(/[\u0300-\u036f]/g, "")     // sin tildes: «Árbol» junto a «Arbol»
    return s
}
function cmpText(a, b) { var x = fold(a), y = fold(b); return x < y ? -1 : (x > y ? 1 : 0) }
function cmpNum(a, b) { return a < b ? -1 : (a > b ? 1 : 0) }
function num(v) { var n = parseInt(v, 10); return isNaN(n) ? 0 : n }

// Sin dato (año 0, sin álbum o artista): siempre al final, en cualquier sentido
function missing(key, t) {
    if (key === "year") return num(t.year) <= 0
    if (key === "album") return fold(t.album) === ""
    if (key === "artist") return fold(t.artist) === ""
    return false
}

function compare(key, a, b, playsOf) {
    if (key === "name") return cmpText(a.title, b.title)
    if (key === "artist")
        return cmpText(a.artist, b.artist) || cmpText(a.album, b.album) || cmpNum(num(a.number), num(b.number)) || cmpText(a.title, b.title)
    if (key === "album")
        return cmpText(a.album, b.album) || cmpNum(num(a.number), num(b.number)) || cmpText(a.title, b.title)
    if (key === "year") return cmpNum(num(a.year), num(b.year)) || cmpText(a.title, b.title)
    if (key === "plays") {
        var pa = playsOf ? num(playsOf(a)) : num(a.plays)
        var pb = playsOf ? num(playsOf(b)) : num(b.plays)
        return cmpNum(pa, pb) || cmpText(a.title, b.title)
    }
    return 0
}

function sortTracks(items, key, asc, playsOf) {
    if (!key || !items) return items
    var wrapped = items.map(function (t, i) { return { t: t, i: i } })
    wrapped.sort(function (x, y) {
        var mx = missing(key, x.t), my = missing(key, y.t)
        if (mx !== my) return mx ? 1 : -1
        var c = compare(key, x.t, y.t, playsOf)
        if (c === 0) return x.i - y.i                    // estable
        return asc ? c : -c
    })
    return wrapped.map(function (w) { return w.t })
}
