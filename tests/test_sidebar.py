"""Barra lateral de iconos: cada botón lleva icono y su texto va como tooltip."""
import re
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"


def _blocks(source, name):
    """Cuerpo de cada `name { ... }` (con llaves balanceadas)."""
    out = []
    for m in re.finditer(r"\b" + name + r"\s*\{", source):
        depth, i = 1, m.end()
        while depth and i < len(source):
            depth += {"{": 1, "}": -1}.get(source[i], 0)
            i += 1
        out.append(source[m.end():i - 1])
    return out


def test_every_sidebar_button_has_an_icon_and_a_tooltip_label():
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    buttons = _blocks(main, "SideButton")
    assert len(buttons) == 7        # Inicio, Álbumes, Artistas, Listas, Reproduciendo, Letra, Por revisar
    for body in buttons:
        assert re.search(r"label:\s*\S", body) and re.search(r"icon:\s*Theme\.icon\w+", body), body[:80]


def test_side_button_shows_no_text_only_a_tooltip():
    source = (QML / "SideButton.qml").read_text(encoding="utf-8")
    assert "AppToolTip" in source and "Accessible.name: root.label" in source
    texts = [b for b in _blocks(source, "Text") if "root.label" in b]
    assert texts == [], "El nombre del botón no debe dibujarse como texto: va solo en el tooltip"


def test_menu_icons_are_defined_in_the_theme():
    theme = (QML / "Theme.qml").read_text(encoding="utf-8")
    for icon in ("iconHome", "iconAlbum", "iconArtist", "iconList", "iconQueue", "iconLyrics", "iconReview", "iconGlobe"):
        assert re.search(r'property string ' + icon + r': "M', theme), icon


def test_sidebar_is_a_narrow_rail_and_the_video_pane_follows_it():
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    assert "readonly property int sidebarWidth: 72" in main
    assert "Layout.preferredWidth: win.sidebarWidth" in main and "leftMargin: win.sidebarWidth" in main
    assert "230" not in re.sub(r"\d{4,}", "", main)       # ya no quedan anchos fijos de la barra antigua


def test_right_panel_is_always_there_and_lyrics_replaces_the_queue():
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    queue = (QML / "QueuePage.qml").read_text(encoding="utf-8")
    assert 'id: rightPanel' in main and 'id: queueLoader' in main and 'id: lyricsLoader' in main
    assert 'property string rightMode: "queue"' in main                   # por defecto: Reproduciendo
    assert 'if (sec === "queue") { showQueue(); return }' in main         # ya no es una página del centro
    assert re.search(r"id: queueComp\s*QueuePage \{\s*panel: true", main)
    assert "property bool panel" in queue and "compact: page.panel" in queue
    assert "stack.replace(null, queueComp)" not in main
