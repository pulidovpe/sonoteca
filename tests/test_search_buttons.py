"""0.12.7: la página de resultados de búsqueda ofrece Nueva lista, Guardar en lista, Portada e info y Editar tags."""
from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "sonoteca" / "ui" / "qml"


def test_search_page_has_the_four_buttons_and_main_wires_them():
    page = (QML / "SearchPage.qml").read_text(encoding="utf-8")
    for label in ('label: "Nueva lista"', 'label: "Guardar en lista\\u2026"', 'label: "Portada e info"', 'label: "Editar tags"'):
        assert label in page, label
    assert "page.newListRequested(page.actionIds)" in page and "page.editRequested(page.actionIds)" in page
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    i = main.index("id: searchComp")
    block = main[i:main.index("id: queueComp")]
    for wired in ("win.showPlaylistPicker(ids)", "win.pickerNewList(ids)", "win.lookupAlbum(id, ids, unknown)", "win.editTags(ids)"):
        assert wired in block, wired


def test_lookup_needs_exactly_one_album():
    page = (QML / "SearchPage.qml").read_text(encoding="utf-8")
    assert "return count === 1 ? last : 0" in page and "enabled: page.lookupAlbumId > 0" in page
