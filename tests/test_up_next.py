"""«Reproducir a continuación»: las canciones añadidas se distinguen con bandas de acento a ambos lados."""
import re
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"
UI = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui"


def test_row_draws_an_accent_band_on_each_side_for_up_next_tracks():
    row = (QML / "ListTrackRow.qml").read_text(encoding="utf-8")
    for prop in ("upNext", "upNextTop", "upNextBottom"):
        assert f"property bool {prop}: false" in row
    block = row[row.index("visible: row.upNext"):]
    assert "anchors.left: parent.left" in block[:900] and "anchors.right: parent.right" in block[:900]
    assert block[:900].count("color: Theme.accent") == 2          # una banda a cada lado


def test_queue_page_passes_group_edges_to_the_rows():
    page = (QML / "QueuePage.qml").read_text(encoding="utf-8")
    assert "upNext: modelData.upNext" in page
    assert re.search(r"upNextTop: modelData\.upNext && \(index === 0 \|\| !page\.items\[index - 1\]\.upNext\)", page)
    assert re.search(r"upNextBottom: modelData\.upNext && \(index === page\.items\.length - 1 \|\| !page\.items\[index \+ 1\]\.upNext\)", page)


def test_controller_exposes_the_up_next_flag_per_row():
    source = (UI / "player_controller.py").read_text(encoding="utf-8")
    assert "up_next_flags()" in source and '"upNext": up_next[position]' in source
