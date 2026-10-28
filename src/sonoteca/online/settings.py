"""Ajustes de las funciones en línea. Por defecto la app funciona sin conexión."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from sonoteca import __version__
from sonoteca.core import paths


@dataclass
class Settings:
    offline: bool = True  # sin conexión hasta que el usuario lo active
    contact: str = ""  # correo o URL: MusicBrainz y Wikimedia piden identificar la aplicación
    translate_lang: str = "ES"  # idioma al que se traducen las letras (código de DeepL)
    # Servidores alternativos (ver online/servers.py): los que añade el usuario y cuál está en uso
    lyrics_servers: list = field(default_factory=list)   # [{"id", "name", "url"}]  (compatibles con LRCLIB)
    lyrics_active: str = "default"
    meta_servers: list = field(default_factory=list)     # [{"id", "name", "musicbrainz", "coverart", "wikipedia"}]
    meta_active: str = "default"


def settings_path() -> Path:
    return paths.data_dir() / "settings.json"


def _env_bool(name: str) -> bool | None:
    value = paths.env(name)
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def load(apply_env: bool = True) -> Settings:
    """Lee settings.json; SONOTECA_OFFLINE y SONOTECA_CONTACT tienen prioridad sobre el archivo."""
    settings = Settings()
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        settings.offline = bool(data.get("offline", settings.offline))
        settings.contact = str(data.get("contact", settings.contact))
        settings.translate_lang = str(data.get("translate_lang", settings.translate_lang))
        settings.lyrics_servers = [x for x in data.get("lyrics_servers", []) if isinstance(x, dict) and x.get("id")]
        settings.meta_servers = [x for x in data.get("meta_servers", []) if isinstance(x, dict) and x.get("id")]
        settings.lyrics_active = str(data.get("lyrics_active", settings.lyrics_active))
        settings.meta_active = str(data.get("meta_active", settings.meta_active))
    except (OSError, ValueError):
        pass
    if not apply_env:
        return settings
    env_offline = _env_bool("OFFLINE")
    if env_offline is not None:
        settings.offline = env_offline
    env_contact = paths.env("CONTACT")
    if env_contact:
        settings.contact = env_contact.strip()
    return settings


def save(settings: Settings) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def user_agent(contact: str = "") -> str:
    """Los servicios exigen un User-Agent que identifique la aplicación."""
    return f"sonoteca/{__version__} ({contact or 'uso personal local'})"
