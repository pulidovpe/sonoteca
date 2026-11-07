"""0.14.1: el diálogo de duplicados tiene la pestaña «Misma canción, otro bitrate o formato»."""
from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "sonoteca" / "ui" / "qml"


def test_dialog_switches_between_identical_and_similar_groups():
    dialog = (QML / "DuplicatesDialog.qml").read_text(encoding="utf-8")
    assert 'property string mode: "exact"' in dialog and 'readonly property bool similar: mode === "similar"' in dialog
    assert "similar ? library.similarGroups() : library.duplicateGroups()" in dialog
    assert "if (similar) library.deleteSimilar(p)" in dialog and "else library.deleteDuplicates(p)" in dialog
    assert 'label: "Archivos id\\u00e9nticos"' in dialog and 'label: "Misma canci\\u00f3n, otro bitrate o formato"' in dialog
    assert "NO son id\\u00e9nticas" in dialog                                       # la confirmación avisa de que no son idénticas
