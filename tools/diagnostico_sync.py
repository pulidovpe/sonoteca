"""Diagnóstico de SOLO LECTURA: por qué una lista tiene menos pistas en el móvil que en el escritorio.

Uso:  python3 tools/diagnostico_sync.py [ruta/a/library.db]      (por defecto ~/sonoteca-dev/library.db)

Para cada lista cuenta cuántas pistas son audio, cuántas son vídeo (no se sincronizan), cuántas tienen el archivo ausente del disco
(no se pueden descargar: el servidor responde 410) y cuántas aún no tienen huella calculada. No modifica nada.
"""
import os
import sqlite3
import sys

PENDIENTE = "(f.content_hash IS NULL OR f.hash_size IS NOT f.size OR f.hash_mtime_ns IS NOT f.mtime_ns)"


def main() -> None:
    db = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/sonoteca-dev/library.db")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)   # solo lectura
    con.row_factory = sqlite3.Row
    print("Base:", db, "\n")
    pendientes = con.execute(f"SELECT path FROM files f WHERE f.kind = 'audio' AND {PENDIENTE}").fetchall()
    ausentes = [r["path"] for r in pendientes if not os.path.exists(r["path"])]
    print(f"Archivos de audio sin huella vigente: {len(pendientes)}  (de ellos, NO existen en el disco: {len(ausentes)})")
    for ruta in ausentes[:15]:
        print("   FALTA EN DISCO:", ruta)
    todos = con.execute("SELECT path FROM files WHERE kind = 'audio'").fetchall()
    sin_disco = [r["path"] for r in todos if not os.path.exists(r["path"])]
    print(f"Archivos de audio de la biblioteca que NO existen en el disco: {len(sin_disco)} de {len(todos)}\n")
    print("Listas (en el escritorio / audio / vídeo / archivo ausente / sin huella):")
    for lista in con.execute("SELECT id, name FROM playlists ORDER BY name"):
        filas = con.execute(
            f"""SELECT t.title, f.kind, f.path, {PENDIENTE} AS pendiente
                FROM playlist_tracks pt JOIN tracks t ON t.id = pt.track_id JOIN files f ON f.id = t.file_id
                WHERE pt.playlist_id = ? ORDER BY pt.position""",
            (lista["id"],),
        ).fetchall()
        video = [r for r in filas if r["kind"] != "audio"]
        audio = [r for r in filas if r["kind"] == "audio"]
        falta = [r for r in audio if not os.path.exists(r["path"])]
        sin_huella = [r for r in audio if r["pendiente"] and os.path.exists(r["path"])]
        marca = "  <-- difiere" if (video or falta or sin_huella) else ""
        print(f"  {lista['name']}: {len(filas)} / {len(audio)} / {len(video)} / {len(falta)} / {len(sin_huella)}{marca}")
        for r in video[:5]:
            print("       vídeo (no se sincroniza):", r["title"])
        for r in falta[:5]:
            print("       archivo ausente:", r["title"], "->", r["path"])
        for r in sin_huella[:5]:
            print("       sin huella (aún por calcular):", r["title"])


if __name__ == "__main__":
    main()
