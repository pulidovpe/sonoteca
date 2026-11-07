"""La poda de Qt del empaquetado no debe quitar nada de lo que importa el QML de la aplicación."""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "src" / "sonoteca" / "ui" / "qml"


def _prune_tokens():
    tree = ast.parse((ROOT / "packaging" / "sonoteca.spec").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "PRUNE" for t in node.targets):
            return [str(ast.literal_eval(e)).lower() for e in node.value.elts]
    raise AssertionError("no se encontró PRUNE en el .spec")


def _imported_modules():
    modules = set()
    for path in QML.glob("*.qml"):
        for m in re.finditer(r"(?m)^import (Qt[\w.]+)", path.read_text(encoding="utf-8")):
            modules.add(m.group(1))
    return modules


def test_prune_never_removes_a_module_the_qml_imports():
    tokens = _prune_tokens()
    assert tokens, "la lista de poda está vacía"
    for module in _imported_modules():
        qml_path = "qml/" + module.lower().replace(".", "/")
        for token in tokens:
            if "qml/" in token:
                assert not (qml_path + "/").startswith(token.rstrip("/") + "/"), f"{token!r} poda {module}"
    # lo que la interfaz sí necesita, escrito a mano por si cambia la detección de imports
    needed = ("qml/qtquick/dialogs", "qml/qtquick/controls/basic", "qml/qtquick/layouts", "qml/qtquick/shapes",
              "qml/qtquick/templates", "qml/qtquick/window", "qml/qtmultimedia", "qml/qtcore")
    for token in tokens:
        for path in needed:
            assert not (path + "/").startswith(token.rstrip("/") + "/") and token not in path, f"{token!r} poda {path}"


def test_pyobjc_hidden_imports_keep_mediaplayer():
    spec = (ROOT / "packaging" / "sonoteca.spec").read_text(encoding="utf-8")
    assert '"MediaPlayer"' in spec            # se importa dinámicamente: sin esto no hay teclas multimedia en el binario de macOS
