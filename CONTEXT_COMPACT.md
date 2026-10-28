# musicapp — CONTEXTO COMPACTO (v0.8.4)

> Pégalo al inicio de un chat nuevo junto con el zip del proyecto. Reemplaza al CONTEXT.md largo (que sigue siendo el historial detallado de las fases 1-5).

## Rol y preferencias de Pablo
- Ingeniero de software experto; razonar antes de responder, usar documentación oficial reciente, admitir incertidumbre. **Responder en español**, conciso.
- **Entregar un zip descargable (sub-versión) en cada respuesta** y no avanzar de fase hasta cerrar los pedidos. Nada se cambia en archivos/tags sin confirmar. Probar siempre en la Mac (el entorno de Claude no tiene red ni PySide6/mutagen/pytest: solo se ejecuta la lógica pura; la UI Qt llega SIN ejecutar).

## Qué es
App de escritorio **local** (Mac M4 Pro, portable a Win/Linux) para ~2000 archivos (mp3, m4a, mp4 de video), por artista/álbum/año; edita tags; internet **solo** para portadas, info de artistas/álbumes, letras y traducción. Python 3.12 + PySide6/QML, `uv`/pip editable (`pip install -e ".[ui,dev]"`; un `pip install .` no editable usa copia vieja). SQLite con `PRAGMA user_version` (esquema actual **v6**). Modo sin conexión **activo por defecto**; red solo en `online/`.

## Mapa del código (`src/musicapp/`)
- `core/`: `db.py` (migraciones v1-v6), `tags.py`, `scanner.py` (incremental), `library.py` (consultas; `list_artists/albums` ocultan vacíos), `covers.py`, `cover_store.py`, `tag_writer.py` (copia temporal + verificación), `tag_edit.py`, `search.py`, `playlists.py` (+`cover_album_ids`), `lyrics.py` (parser LRC, almacenamiento, `lyrics_doc`), `stats.py` (contador y rankings), `cleanup.py` (`purge_missing`: no borra si falta >50 % de archivos = disco desconectado), `paths.py`.
- `online/`: `http.py` (límite de tasa, caché, `get_json(cache=False)`), `settings.py` (+`translate_lang`), `musicbrainz.py`, `coverart.py`, `wikipedia.py` (+`search_candidates`), `enrich.py` (+candidatos/manual de artista), `lrclib.py`, `lyrics.py` (flujo buscar/traducir), `translate.py` (DeepL, `KeyStore` con keyring o `MUSICAPP_DEEPL_KEY`).
- `player/`: `queue.py`, `backend.py` (interfaz; ahora con `audio_devices/set_audio_device`), `qt_backend.py` (QtMultimedia, sigue la salida predeterminada).
- `ui/`: controladores expuestos a QML: `library` (LibraryController), `player`, `online`, `playlists`, `lyrics`, `scanner` (ScanController); `cover_provider.py` (`image://cover/<albumId>` y `/artist/<id>`); `qml/*.qml` (Main, HomePage, AlbumsPage, AlbumDetail, ArtistsPage, ArtistHeader, ArtistLookup, QueuePage, PlaylistsPage, PlaylistDetail, PlaylistCover, LyricsPage, LyricsSettings, TagEditor, AlbumLookup, ScanDialog, AudioOutputPopup, TrackRow, ListTrackRow, TrackDragHandler, DragState…).
- Tests en `tests/` (pytest; `fakes.FakeBackend`, `conftest.qml_env`).

## Estado por versión (lo hecho desde la Fase 5)
- **0.8.0 Fase 6**: letras LRCLIB (sincronizadas, línea resaltada, clic = seek), traducción DeepL alineada por línea, caché en BD; vistas original/traducción/ambas; Ctrl+6 «Letra» y «Ver letra» en el menú de pista. Editor de tags muestra portada actual y nueva (artista: foto actual; varios álbumes: «(varias portadas)»); botón «Editar tags» en la página del artista.
- **0.8.1**: «Cola» = «Reproduciendo» (menú) / «Lista de reproducción» (página); contador de reproducciones (`play_stats`, v6); badge «En línea» alterna el modo; limpieza de álbumes/artistas vacíos.
- **0.8.2**: listas desplegables en la barra lateral; arrastrar canciones a una lista (DragState/TrackDragHandler) y reordenar arrastrando; botón ⋮ en las filas.
- **0.8.3**: historial adelante/atrás (`go/back/forward`, Alt+←/→, Ctrl+[ ]); canciones destacadas por artista; miniaturas en listas; página **Inicio** (la app arranca ahí).
- **0.8.4**: destacadas: máx. 5 (si hay más: 4 + «Mostrar más»); **una reproducción cuenta tras 3 s de sonar** (cualquier origen, aunque no termine); collage de portada de listas (2-4 álbumes); «¿Artista equivocado?» (elegir artículo de Wikipedia o escribir descripción + imagen); salida de audio (menú del altavoz, recuerda la elección, sigue la predeterminada al conectar audífonos); ventana «Buscar música» (se abre sola con biblioteca vacía; Archivo ▸ Buscar música…, Ctrl+Shift+O).

## Trampas técnicas (no repetir)
- QML: `Action` NO tiene `shortcuts` (usar `shortcut` + `Shortcut{sequence}`); no llamar `data` a una propiedad de Item; la navegación se llama `showSection` (no `show`); emitir señales desde hilos de trabajo (GIL con `image://`); `Theme.dataRevision++` refresca páginas; textos con tildes/escapes `\uXXXX` coherentes.
- Python: nunca `open(f,"w").write(open(f).read())` (vacía el archivo; así se perdió `__version__` en 0.8.2). Versión en `src/musicapp/__init__.py`.
- Navegación: toda página se renderiza con `stack.replace` desde `render(loc)`; no usar `stack.push/pop` ni `stack.depth`.
- LRCLIB y DeepL: formato según documentación; DeepL Free 500 000 caracteres/mes (HTTP 456 al agotar; no verificado en vivo; disponibilidad en Colombia sin verificar).

## Pendiente / ideas
- **Probar en la Mac todo lo de 0.8.x** (UI sin ejecutar): arrastrar a listas, historial, salida de audio con Bluetooth real, collage, búsqueda de música, DeepL con clave real.
- No hecho: importar/exportar M3U, listas inteligentes, lotes 5.3, ficha de álbum con Wikipedia, elegir pista en «Sin álbum» múltiple, teclas multimedia globales, gapless, recordar volumen/cola entre sesiones, soltar canciones sobre «Reproduciendo».
- **Siguiente fase: 7 — empaquetado y CI** (GitLab CI: ruff, pytest, PyInstaller/Briefcase por SO, README con capturas, licencia; repo público: **no incluir letras**).
