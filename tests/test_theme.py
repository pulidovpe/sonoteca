"""Tema «Neón»: los colores salen de Theme.qml y todos los tokens usados existen."""
import re
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"
HEX = re.compile(r'"#[0-9a-fA-F]{6,8}"')
ALLOWED = {("Main.qml", '"#000000"')}   # el fondo del video es negro puro a propósito


def _defined():
    theme = (QML / "Theme.qml").read_text(encoding="utf-8")
    return set(re.findall(r"property \w+ (\w+):", theme)) | set(re.findall(r"function (\w+)\(", theme))


def test_no_hardcoded_colors_outside_theme():
    offenders = []
    for path in sorted(QML.glob("*.qml")):
        if path.name == "Theme.qml":
            continue
        for color in HEX.findall(path.read_text(encoding="utf-8")):
            if (path.name, color) not in ALLOWED:
                offenders.append(f"{path.name}: {color}")
    assert offenders == [], "Colores fijos fuera del tema (usa un token de Theme.qml): " + ", ".join(offenders)


def test_every_theme_token_used_exists():
    defined, missing = _defined(), []
    for path in sorted(QML.glob("*.qml")):
        for token in set(re.findall(r"Theme\.(\w+)", path.read_text(encoding="utf-8"))):
            if token not in defined:
                missing.append(f"{path.name}: Theme.{token}")
    assert missing == [], "Tokens inexistentes: " + ", ".join(missing)


def test_brand_palette_matches_the_logo_colors():
    theme = (QML / "Theme.qml").read_text(encoding="utf-8")
    for name, value in (("cyan", "#00d0fc"), ("blue", "#0396fd"), ("violet", "#9849fd"), ("magenta", "#ba38fc")):
        assert f'property color {name}: "{value}"' in theme
    assert "property color accent: cyan" in theme
