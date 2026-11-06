"""0.13.0: el álbum de las columnas es un enlace y se pueden elegir canciones concretas para agregarlas a una lista."""
from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "sonoteca" / "ui" / "qml"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_album_column_is_a_link_through_the_navigation_bus():
    assert "signal albumRequested(int albumId)" in _read("NavBus.qml") and "pragma Singleton" in _read("NavBus.qml")
    assert "singleton NavBus 1.0 NavBus.qml" in _read("qmldir")
    for name, ref in (("TrackRow.qml", "root"), ("ListTrackRow.qml", "row")):
        row = _read(name)
        assert "NavBus.albumRequested(info.albumId)" in row and f"onClicked: {ref}.openAlbum()" in row, name
        assert "font.underline: albumLink.containsMouse" in row, name
        assert "acceptedButtons: Qt.LeftButton" in row, name                  # el clic derecho sigue abriendo el menú de la fila
    main = _read("Main.qml")
    assert "target: NavBus; function onAlbumRequested(albumId) { win.openAlbum(albumId) }" in main


def test_selection_components_are_registered_and_complete():
    qmldir = _read("qmldir")
    assert "SelectionState 1.0 SelectionState.qml" in qmldir and "SelectionBar 1.0 SelectionBar.qml" in qmldir
    state = _read("SelectionState.qml")
    for fn in ("function toggle(id)", "function all(ids)", "function clear()", "function start()", "function stop()", "function ordered(ids)"):
        assert fn in state, fn
    bar = _read("SelectionBar.qml")
    for text in ('label: "Nueva lista"', 'label: "Guardar en lista\\u2026"', 'label: "Cancelar"', "Seleccionar todas"):
        assert text in bar, text


def test_track_row_has_a_selection_mode_that_replaces_play_and_drag():
    row = _read("TrackRow.qml")
    assert "property bool selectable: false" in row and "signal toggled()" in row
    assert "else if (root.selectable) root.toggled()" in row
    assert "m.button === Qt.LeftButton && !root.selectable" in row                       # doble clic no reproduce al seleccionar
    assert "ids: root.trackId > 0 && !root.selectable ? [root.trackId] : []" in row      # ni se arrastra


def test_album_and_search_pages_offer_to_select_songs():
    album, search = _read("AlbumDetail.qml"), _read("SearchPage.qml")
    for name, page in (("AlbumDetail", album), ("SearchPage", search)):
        assert "SelectionState { id: sel }" in page and "SelectionBar {" in page, name
        assert "selectable: sel.active" in page and "onToggled: sel.toggle(modelData.id)" in page, name
        assert 'label: sel.active ? "Terminar selecci\\u00f3n" : "Seleccionar canciones"' in page, name
        assert "page.listRequested(ids)" in page and "page.newListRequested(ids)" in page, name
        assert "sel.ordered(page.trackIds())" in page, name                                # solo las marcadas, en orden
    assert "signal newListRequested(var ids)" in album
    main = _read("Main.qml")
    block = main[main.index("id: albumComp"):main.index("id: albumComp") + 900]
    assert "onNewListRequested: (ids) => win.pickerNewList(ids)" in block
