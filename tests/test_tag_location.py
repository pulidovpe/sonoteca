"""0.14.4: el editor de tags muestra la ruta completa del archivo (o la carpeta si son varios)."""
import os
import tempfile
from pathlib import Path

from sonoteca.core import tag_edit
from sonoteca.core.db import connect

QML = Path(__file__).resolve().parents[1] / "src" / "sonoteca" / "ui" / "qml"


def test_describe_location_single_same_folder_and_several_folders():
    sep = os.sep
    a = sep.join(["", "musica", "Banda", "Disco", "01.mp3"])
    b = sep.join(["", "musica", "Banda", "Disco", "02.mp3"])
    c = sep.join(["", "musica", "Otro", "Disco", "03.mp3"])
    assert tag_edit.describe_location([a]) == a
    assert tag_edit.describe_location([a, a]) == a                                   # la misma pista dos veces
    assert tag_edit.describe_location([a, b]) == f"2 archivos en {os.path.dirname(a)}"
    many = tag_edit.describe_location([a, b, c])
    assert many == f"3 archivos en 2 carpetas; carpeta común: {sep}musica"
    root_only = tag_edit.describe_location([sep + "a" + sep + "x.mp3", sep + "b" + sep + "y.mp3"])
    assert root_only == "2 archivos en 2 carpetas"                                    # una raíz sola no informa
    assert tag_edit.describe_location([]) == ""


def test_common_values_include_the_location():
    with tempfile.TemporaryDirectory() as tmp:
        conn = connect(Path(tmp) / "t.db")
        conn.execute("INSERT INTO artists(id, name, sort_name) VALUES (1, 'Banda', 'banda')")
        conn.execute("INSERT INTO albums(id, title, album_artist_id, year) VALUES (1, 'Disco', 1, 2000)")
        cols = [r[1] for r in conn.execute("PRAGMA table_info(tracks)")][:13]
        for i in (1, 2):
            conn.execute("INSERT INTO files(id, path, size, mtime_ns, format, kind) VALUES (?, ?, 1, 1, 'mp3', 'audio')",
                         (i, os.path.join(tmp, "musica", f"{i}.mp3")))
            conn.execute(f"INSERT INTO tracks({','.join(cols)}) VALUES ({','.join('?' * 13)})",
                         (i, i, 1, 1, f"T{i}", i, 1, 2000, 200.0, "Rock", 192, 1, 0))
        conn.commit()
        one = tag_edit.common_values(conn, [1])
        assert one["location"] == os.path.join(tmp, "musica", "1.mp3")
        two = tag_edit.common_values(conn, [1, 2])
        assert two["location"] == f"2 archivos en {os.path.join(tmp, 'musica')}"
        conn.close()


def test_tag_editor_shows_the_location_in_every_step():
    editor = (QML / "TagEditor.qml").read_text(encoding="utf-8")
    header = editor[editor.index('Text { text: "Editar tags"'):editor.index("// ---- Paso 0")]
    assert "id: locationText" in header and "readOnly: true" in header and "selectByMouse: true" in header
    assert 'text: root.info.location ? root.info.location : ""' in header
    assert 'text: root.single ? "Ruta:" : "Ubicaci\\u00f3n:"' in header
