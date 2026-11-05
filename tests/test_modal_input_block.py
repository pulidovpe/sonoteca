"""0.12.3: el editor de tags no debe dejar pasar clics/arrastres a las filas de canciones de detrás."""
from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "sonoteca" / "ui" / "qml"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_tag_editor_blocks_rows_behind_while_visible():
    assert "onVisibleChanged: DragState.inputBlocked = visible" in _read("TagEditor.qml")
    assert "property bool inputBlocked" in _read("DragState.qml")


def test_rows_and_drag_handler_respect_the_block():
    assert "enabled: ids.length > 0 && !DragState.inputBlocked" in _read("TrackDragHandler.qml")
    for name in ("TrackRow.qml", "ListTrackRow.qml"):
        text = _read(name)
        assert "HoverHandler {" in text and text.count("!DragState.inputBlocked") >= 2, name


def test_main_layout_is_disabled_while_the_editor_is_open():
    main = _read("Main.qml")
    i = main.index("id: playlistsComp")
    assert "ColumnLayout {\n        enabled: !DragState.inputBlocked" in main[i:]
    assert "if (inputBlocked) return" in _read("DragState.qml")


def test_duplicates_dialog_visible_is_always_boolean():
    # 0.12.4: «Unable to assign [undefined] to bool»
    assert "visible: !!root.result.skipped && root.result.skipped.length > 0" in _read("DuplicatesDialog.qml")


def test_hidden_track_menu_items_take_no_space():
    text = _read("TrackMenu.qml")
    assert text.count("height: root.allowDelete ? implicitHeight : 0") == 2
    assert "forceLayout" in _read("AppMenu.qml")
