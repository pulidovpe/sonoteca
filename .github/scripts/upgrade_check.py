#!/usr/bin/env python3
"""Prueba de ACTUALIZACIÓN de la base de datos: una biblioteca creada por una versión ANTIGUA de Sonoteca (p. ej. la v1.0.0)
debe abrirse con el código actual, migrarse sin perder datos y dejar una copia de seguridad; y la app antigua debe negarse a abrir
la base ya migrada (en vez de corromperla).

Se ejecuta en tres pasos, cada uno con el código que corresponde (lo decide PYTHONPATH):
  create  <db> <expected.json> --code old   # con el código ANTIGUO (checkout del tag): crea la base y datos de ejemplo
  verify  <db> <expected.json> --code new --keep <migrada.db>   # con el código ACTUAL: migra una copia y comprueba todo
  refuse  <db migrada> --code old           # con el código ANTIGUO: debe negarse a abrir la base migrada
Sale con código distinto de 0 si algo falla. Escribe un resumen en $GITHUB_STEP_SUMMARY si existe.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

DATA_TABLES = ("artists", "albums", "files", "tracks", "playlists", "playlist_tracks", "play_stats", "lyrics",
               "library_folders", "excluded_paths")


def log(lines: list[str], text: str = "") -> None:
    print(text)
    lines.append(text)


def import_sonoteca(code: str):
    """Importa el paquete y comprueba que es el código esperado: «old» = una carpeta llamada old/, «new» = cualquier otra."""
    import sonoteca
    from sonoteca.core import db
    where = Path(sonoteca.__file__).resolve()
    is_old = "old" in where.parts
    if (code == "old") != is_old:
        sys.exit(f"✗ Se esperaba el código {code.upper()} pero se importó {where}. Revisa PYTHONPATH.")
    return sonoteca, db, where


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    out = {}
    for table in DATA_TABLES:
        try:
            out[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.DatabaseError:
            out[table] = -1                      # la tabla no existe en esa versión
    return out


def spot(conn: sqlite3.Connection) -> dict:
    """Valores concretos que deben sobrevivir tal cual."""
    return {
        "titles": [r[0] for r in conn.execute("SELECT title FROM tracks ORDER BY id")],
        "lists": {r[0]: [t[0] for t in conn.execute(
            "SELECT track_id FROM playlist_tracks WHERE playlist_id = ? ORDER BY position", (r[1],))]
            for r in conn.execute("SELECT name, id FROM playlists ORDER BY id")},
        "plays": {str(r[0]): [r[1], r[2]] for r in conn.execute("SELECT track_id, plays, last_played FROM play_stats ORDER BY track_id")},
        "lyrics": {str(r[0]): [r[1], r[2]] for r in conn.execute("SELECT track_id, original_text, synced_lrc FROM lyrics ORDER BY track_id")},
        "paths": [r[0] for r in conn.execute("SELECT path FROM files ORDER BY id")],
    }


def create(args) -> int:
    sonoteca, db, where = import_sonoteca("old")
    path = Path(args.db)
    if path.exists():
        sys.exit(f"✗ {path} ya existe")
    conn = db.connect(path)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    with conn:
        conn.executemany("INSERT INTO artists (id, name, sort_name) VALUES (?, ?, ?)",
                         [(1, "Artista Uno", "Artista Uno"), (2, "Ñandú y Compañía", "Nandu y Compania")])
        conn.executemany("INSERT INTO albums (id, title, album_artist_id, year) VALUES (?, ?, ?, ?)",
                         [(1, "Primer disco", 1, 1999), (2, "Segundo disco", 1, 2004), (3, "Canción ñ & «comillas»", 2, 2010)])
        tracks = [(1, 1, 1), (2, 1, 1), (3, 2, 1), (4, 2, 1), (5, 3, 2), (6, 3, 2)]       # (id, álbum, artista)
        for tid, album, artist in tracks:
            conn.execute("INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES (?, ?, ?, ?, 'mp3', 'audio')",
                         (tid, f"/musica/disco{album}/pista{tid}.mp3", 1000 + tid, 1_700_000_000_000_000_000 + tid))
            conn.execute("INSERT INTO tracks (id, file_id, album_id, artist_id, title, track_no, duration) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (tid, tid, album, artist, f"Pista {tid} · ñ", tid, 180.5))
        conn.execute("INSERT INTO playlists (id, name) VALUES (1, 'Mis favoritas')")
        conn.execute("INSERT INTO playlists (id, name) VALUES (2, 'Lista vacía')")
        conn.executemany("INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (1, ?, ?)",
                         [(5, 0), (1, 1), (3, 2)])
        conn.executemany("INSERT INTO play_stats (track_id, plays, last_played) VALUES (?, ?, ?)",
                         [(1, 12, "2026-01-02T03:04:05"), (3, 1, "2026-02-03T04:05:06"), (5, 7, None)])
        conn.executemany("INSERT INTO lyrics (track_id, language, original_text, synced_lrc, source) VALUES (?, 'es', ?, ?, 'manual')",
                         [(1, "Letra de prueba\nsegunda línea", "[00:01.00]Letra de prueba"), (2, "Otra letra", None)])
        conn.executemany("INSERT INTO library_folders (path) VALUES (?)", [("/musica",), ("/musica/disco1",)])
        conn.execute("INSERT INTO excluded_paths (path, kind) VALUES ('/musica/disco9/x.mp3', 'file')")
    expected = {"version": version, "schema_old": db.SCHEMA_VERSION, "counts": counts(conn), "spot": spot(conn)}
    conn.close()
    Path(args.expected).write_text(json.dumps(expected, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ Base de ejemplo creada con el código ANTIGUO ({where.parent.parent}): esquema v{version}, {sum(expected['counts'].values())} filas")
    return 0


def verify(args) -> int:
    sonoteca, db, where = import_sonoteca("new")
    expected = json.loads(Path(args.expected).read_text(encoding="utf-8"))
    old_version = expected["version"]
    out: list[str] = []
    problems: list[str] = []

    def check(ok: bool, text: str) -> None:
        log(out, ("✅ " if ok else "❌ ") + text)
        if not ok:
            problems.append(text)

    log(out, f"## Actualización de la base: v{old_version} → v{db.SCHEMA_VERSION} (Sonoteca {sonoteca.__version__})")
    log(out)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "library.db"
        shutil.copy2(args.db, work)
        conn = db.connect(work)                                  # migra
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        check(version == db.SCHEMA_VERSION, f"la versión del esquema pasa de {old_version} a {version} (esperado {db.SCHEMA_VERSION})")

        bak = db.backup_path(work, old_version)
        check(bak.exists(), f"se dejó la copia de seguridad previa ({bak.name})")
        if bak.exists():
            old = sqlite3.connect(bak)
            check(old.execute("PRAGMA user_version").fetchone()[0] == old_version, "la copia conserva la versión anterior del esquema")
            check(counts(old) == expected["counts"], "la copia tiene exactamente los datos originales")
            check(old.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "la copia no está corrupta")
            old.close()

        now = counts(conn)
        for table, n in expected["counts"].items():
            if n >= 0:
                check(now.get(table) == n, f"«{table}»: {n} filas antes, {now.get(table)} después")
        got = spot(conn)
        for key, value in expected["spot"].items():
            check(got[key] == value, f"se conservan tal cual: {key}")

        check(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "PRAGMA integrity_check = ok")
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        check(not fk, f"sin violaciones de claves foráneas ({len(fk)})")

        for table in ("tracks", "playlists"):
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
            if "uuid" in cols:
                total, filled, distinct = conn.execute(
                    f"SELECT COUNT(*), COUNT(uuid), COUNT(DISTINCT uuid) FROM {table}").fetchone()
                check(total == filled == distinct, f"«{table}»: {total} filas, todas con uuid único")

        # Abrir de nuevo no debe cambiar nada ni crear otra copia
        conn.close()
        before = sorted(p.name for p in Path(tmp).iterdir())
        again = db.connect(work)
        check(again.execute("PRAGMA user_version").fetchone()[0] == version and counts(again) == now,
              "abrir otra vez no cambia nada")
        again.close()
        check(sorted(p.name for p in Path(tmp).iterdir()) == before, "abrir otra vez no crea más copias")
        if args.keep:
            shutil.copy2(work, args.keep)
    log(out)
    log(out, "**Resultado: " + ("TODO CORRECTO" if not problems else f"{len(problems)} PROBLEMA(S)") + "**")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "\n")
    return 1 if problems else 0


def refuse(args) -> int:
    sonoteca, db, where = import_sonoteca("old")
    try:
        db.connect(args.db)
    except RuntimeError as exc:
        print(f"✓ La app ANTIGUA se niega a abrir la base migrada, como debe: {exc}")
        return 0
    print("❌ La app antigua abrió una base más nueva que ella: podría corromperla.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create"); c.add_argument("db"); c.add_argument("expected"); c.add_argument("--code", default="old")
    v = sub.add_parser("verify"); v.add_argument("db"); v.add_argument("expected"); v.add_argument("--code", default="new")
    v.add_argument("--keep")
    r = sub.add_parser("refuse"); r.add_argument("db"); r.add_argument("--code", default="old")
    args = parser.parse_args()
    return {"create": create, "verify": verify, "refuse": refuse}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
