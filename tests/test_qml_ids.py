"""Un `id` repetido dentro de un mismo archivo QML impide cargar el componente («id is not unique»)."""
import collections
import re
from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "sonoteca" / "ui" / "qml"
ID = re.compile(r"(?m)(?:^|[{;]\s*)id:\s*([A-Za-z_]\w*)")


def test_no_qml_file_repeats_an_id():
    repeated = {}
    for path in sorted(QML.glob("*.qml")):
        counts = collections.Counter(ID.findall(path.read_text(encoding="utf-8")))
        dup = sorted(name for name, n in counts.items() if n > 1)
        if dup:
            repeated[path.name] = dup
    assert repeated == {}, repeated


def test_qml_braces_are_balanced():
    for path in sorted(QML.glob("*.qml")):
        text = path.read_text(encoding="utf-8")
        assert text.count("{") == text.count("}"), path.name
