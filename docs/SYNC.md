# Sincronización con Android — protocolo v1

> **Pruebas con el escritorio**: ejecuta `sonoteca sync-serve` solo con `SONOTECA_DATA_DIR` apuntando a un directorio de desarrollo
> (copia segura de la biblioteca en [`docs/MIGRACIONES.md`](MIGRACIONES.md)), nunca con la biblioteca real.

Contrato entre el escritorio (`sonoteca sync-serve`) y la app Android. Todo va por **HTTPS** con JSON, en la red local
o por USB. Solo audio, portadas y letras (el video no se sincroniza).

## Transporte
- **Wi-Fi**: el móvil se conecta a `https://<ip-del-equipo>:8765`.
- **USB**: el móvil usa `https://localhost:8765` y hace falta `adb reverse tcp:8765 tcp:8765`. Con `--solo-usb` el servidor escucha solo en
  127.0.0.1 (nada expuesto en la red) y **ejecuta `adb reverse` por ti** para cada móvil autorizado (`--sin-adb` lo desactiva). El redireccionamiento
  **se pierde al reiniciar adb (p. ej. Android Studio) o al reconectar el cable**; desde 1.0.13 el servidor lo detecta (sondeo de `adb devices` y
  `adb reverse --list` cada ~2,5 s) y **lo rehace solo**, avisando «adb reverse <serie>: listo (túnel rehecho)». Si aun así el móvil dice «No se pudo
  conectar», pulsa Intro en la terminal del servidor (repite `adb reverse` y genera un código nuevo). El emparejamiento NO se pierde al reconectar:
  el código solo hace falta la primera vez o tras «Olvidar». Con varios dispositivos conectados, adb necesita `-s <serie>` (el servidor ya lo hace).
- **Certificado**: autofirmado (ECDSA P-256, 10 años) en `<datos>/sync/`. El móvil NO valida contra autoridades: compara la
  huella SHA-256 del certificado DER con la recibida al emparejar (TrustManager propio, sin comprobar el nombre de host).

## Emparejamiento
`sonoteca sync-serve` muestra una URL (o un QR en una fase posterior):
`sonoteca-sync://pair?host=<h>&port=<p>&fp=<sha256-hex>&code=<6 dígitos>`.
`POST /v1/pair {"code","device_id"(8–64),"device_name"}` → `{"token","fingerprint","api"}`. El código vale 5 minutos, es de un
solo uso y se invalida tras 5 fallos. El token se manda en `Authorization: Bearer <token>`; el escritorio solo guarda su SHA-256.
Revocar: `sonoteca sync-devices --revocar <id>`.

**Si cambia el certificado** (el servidor arrancó con otra carpeta de datos, se borró `<datos>/sync/` o es otro equipo), el móvil lo rechaza a propósito: la huella
fijada ya no coincide. En la app pulsa «Olvidar» y empareja otra vez con la URL actual. El servidor imprime al arrancar la carpeta de datos que usa;
el certificado vive en `<datos>/sync/server-cert.pem`.

## Identidad
- `uuid` de la pista (v4) = identidad estable. Sobrevive a editar tags y a re-escanear.
- `hash` (SHA-256 del archivo) = contenido. Cambia al editar tags: si la pista conserva el uuid y cambia el hash, el móvil
  la vuelve a descargar. Si una pista se quita y se vuelve a añadir en el escritorio, recibe un uuid nuevo: el móvil puede
  reconocerla por `hash` antes de descargarla de nuevo.

## Rutas
| Método y ruta | Auth | Respuesta |
|---|---|---|
| `GET /v1/ping` | no | `{app, api, name}` |
| `POST /v1/pair` | código | ver arriba |
| `GET /v1/manifest` | sí | TODAS las pistas de audio (con `hash`/`size` en null si su huella aún no está calculada), listas, listas borradas, `pending_hash`, `complete` |
| `GET /v1/tracks/{uuid}/file` | sí | audio; admite `Range` (206/416); cabeceras `ETag` y `X-Sonoteca-Hash` |
| `GET /v1/tracks/{uuid}/cover` | sí | JPEG/PNG (404 si no hay) |
| `GET /v1/tracks/{uuid}/artist` | sí | JPEG/PNG: imagen del artista de ÁLBUM de la pista, con la regla del escritorio (su foto descargada o, si no, la portada de un álbum suyo; 404 si no hay) |
| `GET /v1/tracks/{uuid}/lyrics` | sí | `{synced_lrc, original_text, language}` (404 si no hay) |
| `POST /v1/plays` | sí | `{events:[{id, track_uuid, played_at}]}` → `{accepted, duplicates, unknown:[id…], invalid:[id…]}` (ver «Estadísticas») |
| `PUT /v1/playlists/{uuid}` | sí | `{name, updated_at, tracks:[uuid…]}` → `{applied, name, updated_at, missing:[uuid…]}` |
| `DELETE /v1/playlists/{uuid}` | sí | `{deleted_at}` → `{deleted, already_gone}` |

Errores: JSON `{"error": "..."}` con 400 (petición inválida), 401 (token), 403 (código), 404, 409 (conflicto de lista), 410
(archivo ausente), 416.

### Manifiesto
**Catálogo completo (desde 1.0.22)**: el manifiesto trae TODAS las pistas de audio, `complete: true`. `pending_hash` > 0 significa que el escritorio aún calcula huellas
(en segundo plano; puede tardar minutos con miles de archivos): esas pistas vienen con `hash` y `size` en `null` y **se ven pero aún no se pueden descargar**; el móvil vuelve a sincronizar más tarde.
Con `complete: true` el móvil **borra de su catálogo las pistas que ya no están** aunque haya pendientes (antes solo anunciaba las pistas con huella y, mientras hubiera pendientes, no borraba nada:
no aparecían las novedades y seguían viéndose artistas y nombres viejos). Un servidor antiguo no manda `complete`: el móvil sigue borrando solo si `pending_hash` es 0.
Si el móvil ya conoce una pista y el manifiesto no trae su huella (el archivo cambió), **conserva la huella anterior** hasta recibir la nueva.
**Archivos ausentes y vídeos (desde 1.0.25)**: cada pista lleva `available`; es `false` si su archivo ya NO existe en el disco del escritorio (borrado, movido, disco externo desconectado): se anuncia con `hash`/`size` en `null`, el móvil la
conserva en su catálogo (lo ya descargado no se pierde) pero no la ofrece para descargar (el servidor respondería 410) y NO cuenta en `pending_hash` (antes se quedaba «pendiente» para siempre). El manifiesto añade `missing_files` (cuántas pistas no están en el disco)
y `video_tracks` (vídeos de la biblioteca: no se sincronizan, solo audio). Un servidor antiguo no manda ninguno: el móvil lo toma como disponible y sin cuentas.
Cada pista: `uuid, hash, size, format, title, artist, album_artist, album, track_no, disc_no, year, duration, genre,
has_cover, has_lyrics, plays`. `plays` = reproducciones totales de la pista en el escritorio (0 si ninguna; incluye las que ya subió el móvil). Cada lista: `uuid, name, updated_at, tracks` (uuid de pista, en orden).

### Descarga
El móvil guarda en un archivo temporal, calcula el SHA-256 y lo compara con `hash` del manifiesto **y** con
`X-Sonoteca-Hash`. Si no coincide con el manifiesto (el archivo cambió en el escritorio), descarta y vuelve a pedir el
manifiesto. Las descargas se reanudan con `Range`.

### Estadísticas de reproducción (móvil → escritorio)
El móvil anota cada reproducción SIN conexión como un **evento** `{id, track_uuid, played_at}` (`id`: 8–64 caracteres, único por evento; `played_at`: UTC ISO 8601 con
milisegundos) y los sube con `POST /v1/plays` la próxima vez que se conecta (máx. 5000 por petición; el cuerpo, 2 MB). Cuándo cuenta una reproducción lo decide cada app (hoy: 5 s de escucha en el escritorio y en el móvil; eran 3 s en el escritorio hasta 1.0.16); el protocolo solo transporta las ya contadas.
- **Idempotente**: el escritorio guarda cada `id` en `sync_play_events`; si el móvil reenvía un lote (se cortó antes de recibir la respuesta) los repetidos salen en `duplicates` y no suman.
- Cada evento nuevo suma 1 a `play_stats.plays` (el contador que ya usa la app de escritorio) y adelanta `last_played` si es más reciente (hora local, como el escritorio).
  Una fecha más de 1 día en el futuro se recorta a «ahora».
- `unknown` = eventos de pistas que ya no existen en el escritorio; `invalid` = eventos mal formados. **El móvil descarta todo el lote al recibir 200**: reenviarlos no los arreglaría.
- Un cuerpo sin `events` o con más de 5000 → 400; sin token válido → 401.

### Listas: última modificación gana
`updated_at` es UTC ISO 8601 con milisegundos (`2026-11-12T10:00:00.000Z`). Se aplica la versión con la marca más reciente;
una marca más de 1 día en el futuro se recorta a «ahora». **Limitación conocida**: depende de que ambos relojes estén
razonablemente bien. Un nombre repetido (sin distinguir mayúsculas) recibe el sufijo « (móvil)». Una lista borrada en el
escritorio no revive con una versión anterior del móvil; sí con una editada después del borrado.

## Seguridad: lo que cubre y lo que no
Cifra el tráfico y autentica al servidor (huella fijada) y al móvil (token). No protege frente a alguien con acceso a la
cuenta de usuario del Mac (la clave privada está en `<datos>/sync/server-key.pem`, permisos 0600). Pendiente: probar en red
real y con el cortafuegos de macOS (la primera vez pedirá permitir conexiones entrantes de Python/Sonoteca).
