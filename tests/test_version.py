"""El paquete debe exponer __version__ (la CLI lo usa en --version)."""
import re

import sonoteca


def test_package_exposes_version():
    assert re.fullmatch(r"\d+\.\d+\.\d+(\.\d+)?", sonoteca.__version__)
