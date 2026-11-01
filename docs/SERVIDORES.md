# Formato estándar para servidores alternativos (descriptor v1)

Sonoteca usa por defecto servicios públicos y gratuitos: **LRCLIB** (letras) y **MusicBrainz + Cover Art Archive +
Wikipedia** (portadas e información). Un *servidor alternativo* los sustituye: una instancia propia, un espejo o un servicio
compatible. Este documento define el **descriptor**: un archivo JSON que describe un servidor para importarlo con un clic
(*Archivo ▸ Servidores de letras y portadas… ▸ Importar descriptor…* o `sonoteca server-import archivo.json`) en lugar de
escribir las direcciones a mano.

## Principios
1. **Sin protocolos nuevos.** Un servidor alternativo habla *exactamente* la API del servicio al que sustituye. El descriptor
   solo dice **dónde** está y **qué protocolo** habla.
2. **Versionado.** `"sonoteca_server": 1`. Una versión desconocida se rechaza con un mensaje claro; los campos desconocidos
   dentro de `services` se ignoran con aviso (compatibilidad hacia delante).
3. **Seguro por construcción.** Solo `http`/`https`; sin usuario ni contraseña en la URL; sin `?` ni `#`; máximo 64 KB;
   nunca se activa solo: importar **agrega**, el usuario elige **Usar**.
4. **Estable.** El `id` identifica al servidor: importar de nuevo el mismo `id` *actualiza* el existente.
5. **Extensible.** Nuevos tipos de servicio o protocolos = nuevos valores permitidos, sin romper la versión 1.

Extensión recomendada: `*.sonoteca-server.json`. Esquema: [`sonoteca-server.schema.json`](sonoteca-server.schema.json)
(JSON Schema 2020-12, útil para validar en un editor). Ejemplo completo:
[`ejemplos/mi-servidor.sonoteca-server.json`](ejemplos/mi-servidor.sonoteca-server.json).

## Campos
| Campo | Obligatorio | Descripción |
|---|---|---|
| `sonoteca_server` | sí | Versión del formato; hoy `1`. |
| `id` | sí | 2–40 caracteres: minúsculas, números y guiones (`mi-servidor`). |
| `name` | sí | Nombre visible, hasta 40 caracteres. |
| `description` | no | Hasta 200 caracteres. |
| `homepage` | no | Dirección `http(s)` de la página del servidor. |
| `services` | sí | Al menos `lyrics` o `metadata`. |
| `services.lyrics` | no | `{ "protocol": "lrclib", "base_url": "https://…/api" }` |
| `services.metadata.musicbrainz` | no | `{ "base_url": "https://…/ws/2" }` (protocolo `musicbrainz-ws2`) |
| `services.metadata.coverart` | no | `{ "base_url": "https://…" }` (protocolo `coverartarchive`) |
| `services.metadata.wikipedia` | no | `{ "base_url": "https://{lang}.…" }` (protocolo `mediawiki-rest`; `{lang}` = idioma de la ficha) |
| `rate_limit.min_interval_ms` | no | Pausa mínima entre consultas a ese servidor, de 100 a 60000 ms. Sin él se usan 500 ms. |

En `metadata`, lo que no se declare sigue usando el servicio predeterminado. `protocol` es opcional en `metadata` (se deduce
de la clave) y, si se indica, debe coincidir.

## Qué hace Sonoteca al importar
- Valida el archivo y muestra el motivo si falla (no se guarda nada).
- Agrega el servidor a la lista de *Letras* y/o de *Portadas e información* según lo que declare (o lo actualiza si el `id`
  ya existe). **No lo activa.**
- Respeta `rate_limit` para las direcciones del servidor cuando está activo.
- Se guarda en `settings.json`; no incluye claves ni credenciales.

## Qué NO cubre (todavía)
- **Autenticación** (claves de API): deliberadamente fuera de la versión 1; no deben viajar en un archivo que se comparte.
- **Descubrimiento por URL** (`/.well-known/sonoteca-server.json`): sería una v2; exige consultar la red y decidir en qué
  se confía.
- **Servicios con otro protocolo** (p. ej. otra API de letras): requieren un adaptador en Sonoteca y un valor nuevo de
  `protocol`; no se resuelven solo con el descriptor.
- **Exportar** el descriptor desde la interfaz.
