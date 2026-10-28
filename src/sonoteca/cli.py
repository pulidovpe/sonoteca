"""CLI de la Fase 1: indexar y consultar la biblioteca sin interfaz gráfica."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .core import library, paths
from .core.db import connect, default_db_path
from .core.scanner import scan


def _fmt_duration(seconds: float) -> str:
    s = round(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def _version_text() -> str:
    import sonoteca

    return f"sonoteca {sonoteca.__version__}  (código en: {Path(sonoteca.__file__).parent})"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sonoteca", description="Biblioteca musical local")
    p.add_argument("--version", action="version", version=_version_text())
    p.add_argument("--db", type=Path, help=f"ruta de la base (por defecto {default_db_path()})")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="indexar una carpeta (incremental)")
    s.add_argument("path", type=Path)
    s.add_argument("--force", action="store_true", help="releer todos los archivos")

    sub.add_parser("stats", help="resumen de la biblioteca")
    r = sub.add_parser("restore", help="restaurar los originales de una carpeta de respaldo")
    r.add_argument("backup_dir", type=Path)
    o = sub.add_parser("online", help="ver o cambiar el modo sin conexión")
    o.add_argument("action", choices=["status", "on", "off"])
    o.add_argument("--contact", help="correo o URL con el que identificarse ante MusicBrainz y Wikipedia")
    fa = sub.add_parser("find-album", help="buscar en MusicBrainz un álbum de la biblioteca")
    fa.add_argument("album_id", type=int)
    fa.add_argument("--all", action="store_true", help="mostrar todos los candidatos (por defecto, 10)")
    fa.add_argument("--track", type=int, help="id de la pista a usar en un grupo \"Sin álbum\" (ver `sonoteca tracks --album ID`)")
    ft = sub.add_parser("find-track", help="buscar en MusicBrainz los álbumes de una pista concreta")
    ft.add_argument("track_id", type=int, help="id de pista (ver `sonoteca search texto`)")
    ft.add_argument("--all", action="store_true", help="mostrar todos los candidatos (por defecto, 10)")
    ai = sub.add_parser("artist-info", help="traer de Wikipedia la información de un artista")
    ai.add_argument("artist_id", type=int)
    ai.add_argument("--force", action="store_true", help="consultar de nuevo aunque ya esté guardada")
    ex = sub.add_parser("export", help="exportar la biblioteca a un archivo .sonoteca")
    ex.add_argument("archivo", help="destino (se añade .sonoteca si falta)")
    ex.add_argument("--sin-imagenes", action="store_true", help="no incluir portadas ni fotos de artistas")
    im = sub.add_parser("import", help="importar un archivo .sonoteca (reemplaza la biblioteca; guarda una copia)")
    im.add_argument("archivo")
    im.add_argument("--carpeta-musica", help="carpeta donde está la música en este equipo (si cambió la ruta)")
    rs = sub.add_parser("reset", help="vaciar la biblioteca y empezar desde cero (guarda una copia salvo --sin-copia)")
    rs.add_argument("--yes", action="store_true", help="confirmar (sin esto no se hace nada)")
    rs.add_argument("--sin-copia", action="store_true", help="no guardar copia de seguridad (irreversible)")
    sub.add_parser("harvest", help="descargar portadas y fotos que falten (solo música bien identificada)")
    sub.add_parser("gui", help="abrir la interfaz gráfica")
    sub.add_parser("paths", help="mostrar dónde se guardan la base de datos y la caché")
    sub.add_parser("artists", help="listar artistas")
    sub.add_parser("incomplete", help="pistas con tags faltantes o deducidos del nombre")

    a = sub.add_parser("albums", help="listar álbumes")
    a.add_argument("--artist", type=int, help="id de artista")
    a.add_argument("--year", type=int)
    a.add_argument("--decade", type=int, help="ej. 1990")

    t = sub.add_parser("tracks", help="listar pistas")
    t.add_argument("--album", type=int, help="id de álbum")
    t.add_argument("--artist", type=int, help="id de artista")

    q = sub.add_parser("search", help="buscar por título, artista o álbum")
    q.add_argument("text")
    return p


def _cmd_online(args, out) -> int:
    from .online import settings as online_settings

    stored = online_settings.load(apply_env=False)  # lo guardado, sin variables de entorno
    if args.action in {"on", "off"}:
        stored.offline = args.action == "off"
        if args.contact:
            stored.contact = args.contact.strip()
        online_settings.save(stored)
    effective = online_settings.load()
    print(f"Modo sin conexión: {'SÍ' if effective.offline else 'no'}", file=out)
    print(f"Identificación (User-Agent): {online_settings.user_agent(effective.contact)}", file=out)
    if not effective.offline and not effective.contact:
        print("Aviso: MusicBrainz y Wikipedia piden identificar la aplicación. Indica un correo o URL:"
              "\n  sonoteca online on --contact tu@correo.com", file=out)
    print(f"Ajustes guardados en: {online_settings.settings_path()}", file=out)
    return 0


def _cmd_online_lookup(args, conn, out) -> int:
    from .online import enrich
    from .online.http import HttpClient, OfflineError, OnlineError

    client = HttpClient()
    try:
        if args.cmd in {"find-album", "find-track"}:
            from .core.models import UNKNOWN_ALBUM

            if args.cmd == "find-track":
                track = conn.execute(
                    "SELECT t.id, t.title, t.duration, COALESCE(t.year, al.year) AS year, ar.name AS artist"
                    " FROM tracks t JOIN albums al ON al.id = t.album_id"
                    " JOIN artists ar ON ar.id = t.artist_id WHERE t.id = ?", (args.track_id,)).fetchone()
                if track is None:
                    print(f"No existe la pista {args.track_id}.", file=out)
                    return 0
            else:
                title_row = conn.execute("SELECT title FROM albums WHERE id = ?",
                                         (args.album_id,)).fetchone()
                track = (enrich.pick_track(conn, args.album_id, args.track)
                         if title_row and title_row["title"] == UNKNOWN_ALBUM else None)
            if track:
                minutes, seconds = divmod(round(track["duration"] or 0), 60)
                print(f"Buscando por la canción «{track['title']}» de {track['artist']} "
                      f"({minutes}:{seconds:02d}, año {track['year'] or '????'}) "
                      f"[pista {track['id']}]", file=out)
            if args.cmd == "find-track":
                candidates = enrich.track_candidates(client, conn, args.track_id)
            else:
                candidates = enrich.album_candidates(client, conn, args.album_id, track_id=args.track)
            if not candidates:
                print("Sin resultados (¿artista desconocido o álbum inexistente?).", file=out)
                return 0
            if candidates[0].via == "track":
                print("Pista sin álbum: álbumes donde aparece la canción. Los primeros coinciden mejor "
                      "en duración y año (si se conocen).", file=out)
            shown = candidates if args.all else candidates[:10]
            for i, c in enumerate(shown, start=1):
                year = c.year or "????"
                if c.via == "track":
                    flag = "  <- misma duración" if c.length_match else ""
                    print(f"{i}. {c.title} - {c.artist} ({year}, {c.kind or '?'})  "
                          f"[{c.release_group_id}]{flag}", file=out)
                else:
                    flag = "  <- coincidencia probable" if c.confident else ""
                    print(f"{i}. {c.title} - {c.artist} ({year}, {c.kind or '?'})  "
                          f"puntaje {c.mb_score}, parecido {c.similarity:.2f}  [{c.release_group_id}]{flag}",
                          file=out)
            if len(candidates) > len(shown):
                print(f"... y {len(candidates) - len(shown)} más (usa --all para verlos)", file=out)
        else:
            info = enrich.fetch_artist_info(client, conn, args.artist_id, force=args.force)
            if info is None:
                print("No se encontró información fiable de ese artista.", file=out)
                return 0
            print(f"{info['name']} ({info['bio_lang']}.wikipedia.org)\n\n{info['bio']}\n\n"
                  f"Fuente: {info['bio_url']}  (texto de Wikipedia, licencia CC BY-SA)", file=out)
        if client.settings.offline and client.cache_hits and not client.network_requests:
            print("\nNota: el modo sin conexión está activo; este resultado estaba guardado de una "
                  "consulta anterior.", file=out)
    except OfflineError:
        print("Modo sin conexión activo. Para usar internet: sonoteca online on", file=sys.stderr)
        return 3
    except OnlineError as exc:
        print(f"Error en la consulta: {exc}", file=sys.stderr)
        return 3
    finally:
        client.close()
    return 0


def _run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = sys.stdout
    if getattr(args, "db", None) is None and args.cmd != "gui":   # (la interfaz lo hace en run())
        from .core import legacy

        legacy.ensure_migrated()
    if args.cmd == "export":
        from .core import portable

        dest = Path(args.archivo)
        if dest.suffix != portable.EXTENSION:
            dest = dest.with_name(dest.name + portable.EXTENSION)
        manifest = portable.export_library(args.db or default_db_path(), dest, include_images=not args.sin_imagenes)
        print(f"Exportado: {dest}  ({manifest['tracks']} canciones, {manifest['albums']} álbumes, "
              f"{manifest['artists']} artistas, {manifest['playlists']} listas)", file=out)
        return 0
    if args.cmd == "import":
        from .core import portable

        if args.db:
            print("`import` trabaja sobre la biblioteca estándar; no se combina con --db.", file=sys.stderr)
            return 2
        try:
            manifest = portable.stage_import(args.archivo, args.carpeta_musica)
        except portable.PortableError as exc:
            print(f"No se importó: {exc}", file=sys.stderr)
            return 1
        report = portable.apply_pending_import()
        print(f"Importado: {manifest['tracks']} canciones, {manifest['albums']} álbumes. "
              f"Copia de la biblioteca anterior en {report['backup']}", file=out)
        if report["missing"]:
            print(f"AVISO: {report['missing']} archivos no están en las rutas guardadas; usa --carpeta-musica "
                  "si la música cambió de carpeta.", file=out)
        return 0
    if args.cmd == "reset":
        from .core import portable

        if not args.yes:
            print("Esto vacía la biblioteca (base de datos, portadas y fotos descargadas). "
                  "Repite con --yes para confirmar.", file=sys.stderr)
            return 2
        portable.stage_reset(keep_backup=not args.sin_copia)
        report = portable.apply_pending_reset()
        print("Biblioteca vaciada." + (f" Copia en {report['backup']}" if report["backup"] else " Sin copia de seguridad."),
              file=out)
        return 0
    if args.cmd == "harvest":
        from .online import harvest
        from .online.http import HttpClient, OfflineError

        conn = connect(args.db)
        work = harvest.plan(conn)
        print(f"Por descargar: {len(work.albums)} portadas y {len(work.artists)} artistas "
              f"({harvest.format_duration(work.seconds)}).", file=out)
        client = HttpClient()
        try:
            summary = harvest.run(conn, client, work, progress=lambda d, t, label: label and print(
                f"[{d + 1}/{t}] {label}", file=out))
        except OfflineError:
            summary = {"offline": True}
        finally:
            client.close()
        if summary.get("offline"):
            print("Modo sin conexión activo. Para usar internet: sonoteca online on", file=sys.stderr)
            return 3
        print(f"Listo: {summary['covers']} portadas, {summary['artists']} artistas, {summary['unsure']} dudosos "
              f"(se dejan para elegir a mano), {summary['notfound']} sin resultado, {summary['errors']} errores.",
              file=out)
        return 0
    if args.cmd == "gui":
        try:
            from .ui.app import run
        except ImportError:
            print("Falta PySide6. Instálalo con: pip install -e \".[ui]\"  (o: uv sync --extra ui)",
                  file=sys.stderr)
            return 2
        return run(args.db)
    out = sys.stdout
    if args.cmd == "online":
        return _cmd_online(args, out)
    if args.cmd == "restore":
        from .core.tag_writer import restore_backups

        try:
            restored, failed = restore_backups(args.backup_dir)
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 2
        print(f"Restaurados: {restored}  Fallidos: {len(failed)}", file=out)
        for msg in failed:
            print(f"  ERROR {msg}", file=sys.stderr)
        print("Ejecuta `sonoteca scan --force <carpeta>` para actualizar la biblioteca.", file=out)
        return 1 if failed else 0
    if args.cmd == "paths":
        db = args.db or default_db_path()
        cache = paths.cache_dir() / "covers"
        import sonoteca

        print(f"Versión       : {sonoteca.__version__}  (código en {Path(sonoteca.__file__).parent})", file=out)
        print(f"Base de datos : {db}", file=out)
        print(f"Caché de portadas: {cache}  (miniaturas; se puede borrar)", file=out)
        print(f"Portadas guardadas: {paths.covers_dir()}  (elegidas y reemplazadas)", file=out)
        for var in ("SONOTECA_DATA_DIR", "SONOTECA_CACHE_DIR", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
            if os.environ.get(var):
                print(f"  variable {var}={os.environ[var]}", file=out)
        for label, path in (("base de datos", db), ("caché", cache), ("carpeta de portadas", paths.covers_dir())):
            if paths.inside_virtualenv(path):
                print(f"AVISO: la {label} está dentro del entorno virtual ({sys.prefix}).", file=out)
        return 0
    conn = connect(args.db)
    if args.cmd in {"find-album", "find-track", "artist-info"}:
        return _cmd_online_lookup(args, conn, out)

    if args.cmd == "scan":
        def progress(n: int, path: Path) -> None:
            if n % 100 == 0:
                print(f"  {n} archivos revisados...", file=sys.stderr)

        try:
            r = scan(conn, args.path, progress, force=args.force)
        except NotADirectoryError as exc:
            print(f"No es una carpeta: {exc}", file=sys.stderr)
            return 2
        print(f"Nuevos: {r.added}  Actualizados: {r.updated}  Sin cambios: {r.unchanged}"
              f"  Eliminados: {r.removed}  Errores: {len(r.errors)}", file=out)
        for path, msg in r.errors:
            print(f"  ERROR {path}: {msg}", file=sys.stderr)
        return 1 if r.errors else 0

    if args.cmd == "stats":
        s = library.stats(conn)
        print(f"Artistas: {s['artists']}  Álbumes: {s['albums']}  Pistas: {s['tracks']}"
              f"  Videos: {s['videos']}", file=out)
        print(f"Duración total: {_fmt_duration(s['seconds'])}  Tamaño: {s['bytes'] / 1e9:.2f} GB",
              file=out)
    elif args.cmd == "incomplete":
        rows = library.list_incomplete(conn)
        for r in rows:
            reasons = []
            if r["inferred"]:
                reasons.append("deducido del nombre")
            if r["no_artist"]:
                reasons.append("sin artista")
            if r["no_album"]:
                reasons.append("sin álbum")
            print(f"[{r['id']}] {r['artist']} - {r['title']}  ({', '.join(reasons)})\n      {r['path']}",
                  file=out)
        print(f"Total: {len(rows)}", file=out)
    elif args.cmd == "artists":
        for r in library.list_artists(conn):
            print(f"[{r['id']}] {r['name']}  ({r['albums']} álbumes, {r['tracks']} pistas)",
                  file=out)
    elif args.cmd == "albums":
        for r in library.list_albums(conn, artist_id=args.artist, year=args.year,
                                     decade=args.decade):
            print(f"[{r['id']}] {r['artist']} - {r['title']} ({r['year'] or '????'})"
                  f"  {r['tracks']} pistas, {_fmt_duration(r['duration'])}", file=out)
    elif args.cmd == "tracks":
        for r in library.list_tracks(conn, album_id=args.album, artist_id=args.artist):
            no = f"{r['track_no']:02d}" if r["track_no"] else "--"
            print(f"[{r['id']}] {no} {r['title']} - {r['artist']} ({r['album']})"
                  f"  {_fmt_duration(r['duration'])}", file=out)
    elif args.cmd == "search":
        for r in library.search(conn, args.text):
            print(f"[{r['id']}] {r['title']} - {r['artist']} ({r['album']}, {r['year'] or '????'})",
                  file=out)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _run(argv)
    except BrokenPipeError:  # p. ej. `sonoteca albums | head`: no es un error
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        return 0
