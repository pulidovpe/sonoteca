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
| `GET /v1/manifest` | sí | pistas de audio con huella vigente, listas, listas borradas, `pending_hash` |
| `GET /v1/tracks/{uuid}/file` | sí | audio; admite `Range` (206/416); cabeceras `ETag` y `X-Sonoteca-Hash` |
| `GET /v1/tracks/{uuid}/cover` | sí | JPEG/PNG (404 si no hay) |
| `GET /v1/tracks/{uuid}/lyrics` | sí | `{synced_lrc, original_text, language}` (404 si no hay) |
| `PUT /v1/playlists/{uuid}` | sí | `{name, updated_at, tracks:[uuid…]}` → `{applied, name, updated_at, missing:[uuid…]}` |
| `DELETE /v1/playlists/{uuid}` | sí | `{deleted_at}` → `{deleted, already_gone}` |

Errores: JSON `{"error": "..."}` con 400 (petición inválida), 401 (token), 403 (código), 404, 409 (conflicto de lista), 410
(archivo ausente), 416.

### Manifiesto
`pending_hash` > 0 significa que el escritorio aún calcula huellas (se hace en segundo plano la primera vez, puede tardar
minutos con miles de archivos): esas pistas todavía no aparecen. El móvil vuelve a pedir el manifiesto más tarde.
Cada pista: `uuid, hash, size, format, title, artist, album_artist, album, track_no, disc_no, year, duration, genre,
has_cover, has_lyrics`. Cada lista: `uuid, name, updated_at, tracks` (uuid de pista, en orden).

### Descarga
El móvil guarda en un archivo temporal, calcula el SHA-256 y lo compara con `hash` del manifiesto **y** con
`X-Sonoteca-Hash`. Si no coincide con el manifiesto (el archivo cambió en el escritorio), descarta y vuelve a pedir el
manifiesto. Las descargas se reanudan con `Range`.

### Listas: última modificación gana
`updated_at` es UTC ISO 8601 con milisegundos (`2026-11-12T10:00:00.000Z`). Se aplica la versión con la marca más reciente;
una marca más de 1 día en el futuro se recorta a «ahora». **Limitación conocida**: depende de que ambos relojes estén
razonablemente bien. Un nombre repetido (sin distinguir mayúsculas) recibe el sufijo « (móvil)». Una lista borrada en el
escritorio no revive con una versión anterior del móvil; sí con una editada después del borrado.

## Seguridad: lo que cubre y lo que no
Cifra el tráfico y autentica al servidor (huella fijada) y al móvil (token). No protege frente a alguien con acceso a la
cuenta de usuario del Mac (la clave privada está en `<datos>/sync/server-key.pem`, permisos 0600). Pendiente: probar en red
real y con el cortafuegos de macOS (la primera vez pedirá permitir conexiones entrantes de Python/Sonoteca).
