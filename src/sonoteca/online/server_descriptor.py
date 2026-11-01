"""Descriptor de servidor alternativo («Sonoteca server descriptor», versión 1).

Un archivo JSON (`*.sonoteca-server.json`) que describe un servidor de letras y/o de portadas e información, para
importarlo en Sonoteca sin escribir las direcciones a mano. Ver docs/SERVIDORES.md y docs/sonoteca-server.schema.json.

    {
      "sonoteca_server": 1,
      "id": "mi-servidor",
      "name": "Mi servidor",
      "description": "Instancia propia",              (opcional)
      "homepage": "https://mi-servidor.example",      (opcional)
      "services": {
        "lyrics":   { "protocol": "lrclib", "base_url": "https://mi-servidor.example/api" },
        "metadata": {
          "musicbrainz": { "base_url": "https://mb.example/ws/2" },
          "coverart":    { "base_url": "https://caa.example" },
          "wikipedia":   { "base_url": "https://{lang}.wiki.example" }
        }
      },
      "rate_limit": { "min_interval_ms": 500 }        (opcional)
    }

Un servidor alternativo habla el MISMO protocolo que el servicio al que sustituye: no define formatos nuevos.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import servers

FORMAT_KEY = "sonoteca_server"
VERSION = 1
MAX_BYTES = 64 * 1024
LYRICS_PROTOCOLS = {"lrclib"}
METADATA_KEYS = {"musicbrainz": "musicbrainz-ws2", "coverart": "coverartarchive", "wikipedia": "mediawiki-rest"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")


class DescriptorError(ValueError):
    """Mensaje pensado para mostrarse tal cual al usuario."""


@dataclass
class Descriptor:
    id: str
    name: str
    description: str = ""
    homepage: str = ""
    lyrics_url: str = ""
    musicbrainz: str = ""
    coverart: str = ""
    wikipedia: str = ""
    min_interval_ms: int | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def has_lyrics(self) -> bool:
        return bool(self.lyrics_url)

    @property
    def has_metadata(self) -> bool:
        return bool(self.musicbrainz or self.coverart or self.wikipedia)


def _obj(value, where: str) -> dict:
    if not isinstance(value, dict):
        raise DescriptorError(f"«{where}» debe ser un objeto JSON.")
    return value


def _url(value, where: str, template: bool = False) -> str:
    if not isinstance(value, str):
        raise DescriptorError(f"«{where}» debe ser una dirección (texto).")
    try:
        return servers.normalize_url(value, template=template)
    except ValueError as exc:
        raise DescriptorError(f"{where}: {exc}") from exc


def parse(source: str | bytes | dict) -> Descriptor:
    """Valida un descriptor (texto JSON o dict) y lo convierte. Lanza DescriptorError con un mensaje claro."""
    if isinstance(source, (str, bytes)):
        if len(source) > MAX_BYTES:
            raise DescriptorError("El archivo es demasiado grande para ser un descriptor (máximo 64 KB).")
        try:
            data = json.loads(source)
        except ValueError as exc:
            raise DescriptorError(f"No es un JSON válido: {exc}") from exc
    else:
        data = source
    data = _obj(data, "raíz")
    if data.get(FORMAT_KEY) != VERSION:
        raise DescriptorError(f"Falta «{FORMAT_KEY}»: {VERSION} o es de una versión que esta Sonoteca no conoce.")
    server_id = data.get("id")
    if not isinstance(server_id, str) or not ID_RE.match(server_id):
        raise DescriptorError("«id» debe ser un identificador de 2 a 40 caracteres: minúsculas, números y guiones.")
    try:
        name = servers._clean_name(data.get("name"))
    except ValueError as exc:
        raise DescriptorError(f"name: {exc}") from exc
    desc = Descriptor(id=server_id, name=name)
    if data.get("description") is not None:
        text = data["description"]
        if not isinstance(text, str) or len(text) > 200:
            raise DescriptorError("«description» debe ser texto de hasta 200 caracteres.")
        desc.description = text
    if data.get("homepage"):
        desc.homepage = _url(data["homepage"], "homepage")

    services = _obj(data.get("services"), "services")
    if "lyrics" in services:
        lyrics = _obj(services["lyrics"], "services.lyrics")
        if lyrics.get("protocol") not in LYRICS_PROTOCOLS:
            raise DescriptorError(f"services.lyrics.protocol debe ser uno de: {', '.join(sorted(LYRICS_PROTOCOLS))}.")
        desc.lyrics_url = _url(lyrics.get("base_url"), "services.lyrics.base_url")
    if "metadata" in services:
        meta = _obj(services["metadata"], "services.metadata")
        for key, protocol in METADATA_KEYS.items():
            if key not in meta:
                continue
            entry = _obj(meta[key], f"services.metadata.{key}")
            if entry.get("protocol", protocol) != protocol:
                raise DescriptorError(f"services.metadata.{key}.protocol debe ser «{protocol}».")
            setattr(desc, key, _url(entry.get("base_url"), f"services.metadata.{key}.base_url", template=key == "wikipedia"))
        for key in meta:
            if key not in METADATA_KEYS:
                desc.warnings.append(f"services.metadata.{key}: servicio desconocido, se ignora.")
    if not (desc.has_lyrics or desc.has_metadata):
        raise DescriptorError("«services» debe incluir al menos «lyrics» o «metadata» con una dirección.")
    for key in services:
        if key not in ("lyrics", "metadata"):
            desc.warnings.append(f"services.{key}: tipo de servicio desconocido, se ignora.")

    if "rate_limit" in data:
        rate = _obj(data["rate_limit"], "rate_limit")
        value = rate.get("min_interval_ms")
        if not isinstance(value, int) or isinstance(value, bool) or not 100 <= value <= 60000:
            raise DescriptorError("rate_limit.min_interval_ms debe ser un número entero entre 100 y 60000.")
        desc.min_interval_ms = value
    return desc


def load_file(path: str | Path) -> Descriptor:
    path = Path(path)
    try:
        if path.stat().st_size > MAX_BYTES:
            raise DescriptorError("El archivo es demasiado grande para ser un descriptor (máximo 64 KB).")
        return parse(path.read_bytes())
    except OSError as exc:
        raise DescriptorError(f"No se pudo leer el archivo: {exc}") from exc


def import_into(settings, desc: Descriptor) -> list[str]:
    """Agrega (o actualiza, si el id ya existe) el servidor en los ajustes. No lo activa. Devuelve qué se agregó."""
    added = []
    extra = {"min_interval_ms": desc.min_interval_ms} if desc.min_interval_ms else {}
    if desc.has_lyrics:
        settings.lyrics_servers = [x for x in settings.lyrics_servers if x.get("id") != desc.id]
        settings.lyrics_servers.append({"id": desc.id, "name": desc.name, "url": desc.lyrics_url, **extra})
        added.append("letras")
    if desc.has_metadata:
        settings.meta_servers = [x for x in settings.meta_servers if x.get("id") != desc.id]
        settings.meta_servers.append({"id": desc.id, "name": desc.name, "musicbrainz": desc.musicbrainz,
                                      "coverart": desc.coverart, "wikipedia": desc.wikipedia, **extra})
        added.append("portadas e información")
    return added
