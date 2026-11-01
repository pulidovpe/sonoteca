"""Descriptor de servidor alternativo (v1): validación, importación y límite de tasa."""
import json
from pathlib import Path

import pytest

from sonoteca.online import http, server_descriptor as sd, servers
from sonoteca.online import settings as online_settings

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "docs" / "ejemplos" / "mi-servidor.sonoteca-server.json"


def _doc(**changes):
    base = {"sonoteca_server": 1, "id": "mi-servidor", "name": "Mi servidor",
            "services": {"lyrics": {"protocol": "lrclib", "base_url": "https://letras.casa/api/"}}}
    base.update(changes)
    return base


def test_the_documented_example_is_valid_and_complete():
    desc = sd.load_file(EXAMPLE)
    assert desc.id == "mi-servidor" and desc.lyrics_url == "https://mi-servidor.example/api"
    assert desc.musicbrainz.endswith("/ws/2") and desc.coverart and "{lang}" in desc.wikipedia
    assert desc.min_interval_ms == 500 and desc.has_lyrics and desc.has_metadata and desc.warnings == []


def test_minimal_lyrics_only_descriptor_and_url_normalisation():
    desc = sd.parse(json.dumps(_doc()))
    assert desc.lyrics_url == "https://letras.casa/api" and not desc.has_metadata and desc.min_interval_ms is None


@pytest.mark.parametrize("bad, fragment", [
    ({"sonoteca_server": 2}, "versi"),
    ({"id": "Mal Id"}, "«id»"),
    ({"name": ""}, "name"),
    ({"services": {}}, "al menos"),
    ({"services": {"lyrics": {"protocol": "genius", "base_url": "https://x.y"}}}, "protocol"),
    ({"services": {"lyrics": {"protocol": "lrclib", "base_url": "https://u:p@x.y/api"}}}, "usuario"),
    ({"services": {"lyrics": {"protocol": "lrclib", "base_url": "ftp://x.y"}}}, "http"),
    ({"services": {"metadata": {"wikipedia": {"base_url": "https://{x}.wiki.org"}}}}, "llaves"),
    ({"services": {"metadata": {"musicbrainz": {"protocol": "otro", "base_url": "https://x.y/ws/2"}}}}, "protocol"),
    ({"rate_limit": {"min_interval_ms": 5}}, "min_interval_ms"),
    ({"homepage": "javascript:alert(1)"}, "homepage"),
])
def test_invalid_descriptors_are_rejected_with_a_clear_message(bad, fragment):
    with pytest.raises(sd.DescriptorError) as err:
        sd.parse(_doc(**bad))
    assert fragment in str(err.value)


def test_rejects_non_json_oversized_and_non_object_input():
    for source in ("no es json", "[1, 2]"):
        with pytest.raises(sd.DescriptorError):
            sd.parse(source)
    with pytest.raises(sd.DescriptorError, match="grande"):
        sd.parse("x" * (sd.MAX_BYTES + 1))


def test_unknown_service_kinds_are_ignored_with_a_warning():
    doc = _doc()
    doc["services"]["traduccion"] = {"base_url": "https://t.example"}
    doc["services"]["metadata"] = {"coverart": {"base_url": "https://caa.casa"}, "musica": {"base_url": "https://m"}}
    desc = sd.parse(doc)
    assert len(desc.warnings) == 2 and desc.coverart == "https://caa.casa"


def test_import_adds_updates_by_id_and_never_activates():
    s = online_settings.Settings()
    added = sd.import_into(s, sd.load_file(EXAMPLE))
    assert added == ["letras", "portadas e información"]
    assert s.lyrics_active == "default" and s.meta_active == "default"            # importar no activa
    assert s.lyrics_servers[0]["id"] == "mi-servidor" and s.meta_servers[0]["min_interval_ms"] == 500
    sd.import_into(s, sd.parse(_doc(name="Nombre nuevo")))                         # mismo id: actualiza, no duplica
    assert len(s.lyrics_servers) == 1 and s.lyrics_servers[0]["name"] == "Nombre nuevo" and len(s.meta_servers) == 1
    servers.set_active(s, "lyrics", "mi-servidor")
    assert servers.lyrics_base(s) == "https://letras.casa/api"


def test_declared_rate_limit_is_applied_to_the_servers_hosts():
    s = online_settings.Settings()
    sd.import_into(s, sd.load_file(EXAMPLE))
    servers.set_active(s, "lyrics", "mi-servidor")
    servers.set_active(s, "meta", "mi-servidor")
    http.CUSTOM_INTERVAL.clear()
    servers.lyrics_base(s)
    servers.wikipedia_base("es", s)
    assert http.CUSTOM_INTERVAL["mi-servidor.example"] == 0.5 and http.CUSTOM_INTERVAL["es.wiki.mi-servidor.example"] == 0.5
    waits = []
    limiter = http.RateLimiter(clock=lambda: 0.0, sleep=waits.append)
    limiter.wait("mi-servidor.example")
    limiter.wait("mi-servidor.example")
    assert waits == [0.5]


def test_json_schema_file_matches_the_validator():
    schema = json.loads((ROOT / "docs" / "sonoteca-server.schema.json").read_text(encoding="utf-8"))
    assert schema["required"] == ["sonoteca_server", "id", "name", "services"]
    assert schema["properties"]["sonoteca_server"]["const"] == sd.VERSION
    assert schema["properties"]["services"]["properties"]["lyrics"]["properties"]["protocol"]["enum"] == sorted(sd.LYRICS_PROTOCOLS)
    assert set(schema["properties"]["services"]["properties"]["metadata"]["properties"]) == set(sd.METADATA_KEYS)
    assert json.loads(EXAMPLE.read_text(encoding="utf-8"))["sonoteca_server"] == 1


def test_cli_server_import_adds_the_server_without_activating_it(tmp_path, monkeypatch, capsys=None):
    import io
    import sys

    from sonoteca import cli
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    monkeypatch.setenv("SONOTECA_CACHE_DIR", str(tmp_path / "cache"))
    buf, old = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        assert cli.main(["server-import", str(EXAMPLE)]) == 0
    finally:
        sys.stdout = old
    stored = online_settings.load(apply_env=False)
    assert stored.lyrics_servers[0]["id"] == "mi-servidor" and stored.lyrics_active == "default"
    assert "Agregado «Mi servidor»" in buf.getvalue()
