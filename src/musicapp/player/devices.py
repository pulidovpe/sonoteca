"""Clasificación de salidas de audio por su nombre (Qt no expone el tipo de conexión)."""
from __future__ import annotations

_HEADPHONES = ("headphone", "headset", "airpods", "earbud", "earphone", "buds", "beats",
               "auricular", "audifon", "audífon", "cascos")
_DISPLAY = ("hdmi", "displayport", "display port", "monitor", "tv", "televis")


def classify_audio_device(name: str) -> str:
    """'headphones' | 'display' | 'speaker' según el nombre que da el sistema."""
    text = (name or "").lower()
    if any(word in text for word in _HEADPHONES):
        return "headphones"
    if any(word in text for word in _DISPLAY):
        return "display"
    return "speaker"
