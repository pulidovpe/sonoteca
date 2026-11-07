"""Orden de las cabeceras de columna (`TrackSort.js`). Se ejecuta con Node si está instalado."""
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parents[1] / "src" / "sonoteca" / "ui" / "qml" / "TrackSort.js"

SCRIPT = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[process.argv.length - 1], 'utf8').replace('.pragma library', '');
const m = {}; new Function('m', src + ';m.sortTracks = sortTracks;')(m);
const t = (id, title, artist, album, year, plays, number) => ({id, title, artist, album, year, plays, number});
const L = [t(1,'Beta','Zeta','Disco B','2001',5,'2'), t(2,'alfa','Ana','Disco B','',9,'1'), t(3,'Árbol','ana','Álbum A','1999',0,'1'),
           t(4,'Zulu','Mario','','1999',7,''), t(5,'Arbol','Zeta','Álbum A','2010',2,'2')];
const ids = (k, asc, f) => m.sortTracks(L, k, asc, f).map(x => x.id).join(',');
console.log(JSON.stringify({
  nameAsc: ids('name', true), nameDesc: ids('name', false), artistAsc: ids('artist', true),
  albumAsc: ids('album', true), albumDesc: ids('album', false), yearAsc: ids('year', true), yearDesc: ids('year', false),
  playsDesc: ids('plays', false), playsFn: ids('plays', true, t => t.id === 3 ? 100 : 0), none: m.sortTracks(L, '', true, null) === L,
}));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="necesita Node.js")
def test_sorting_rules():
    import json
    out = subprocess.run(["node", "-e", SCRIPT, str(JS)], capture_output=True, text=True, check=True).stdout
    got = json.loads(out)
    assert got == {
        "nameAsc": "2,3,5,1,4",        # sin tildes ni mayúsculas; el empate (Árbol/Arbol) conserva el orden original
        "nameDesc": "4,1,3,5,2",       # el empate sigue estable también al invertir
        "artistAsc": "3,2,4,5,1",      # Ana: primero el álbum A; con empate en artista, álbum y nº de pista
        "albumAsc": "3,5,2,1,4",       # sin álbum, siempre al final
        "albumDesc": "1,2,5,3,4",
        "yearAsc": "3,4,1,5,2",        # sin año, siempre al final
        "yearDesc": "5,1,4,3,2",
        "playsDesc": "2,4,1,5,3",      # más escuchadas primero
        "playsFn": "2,5,1,4,3",        # `playsOf` manda sobre el campo `plays`
        "none": True,                  # sin clave devuelve la lista tal cual
    }
