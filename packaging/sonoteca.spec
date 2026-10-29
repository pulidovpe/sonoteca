# -*- mode: python ; coding: utf-8 -*-
# Empaquetado con PyInstaller (modo carpeta; en macOS además Sonoteca.app):
#   pip install -e ".[ui,build]" && pyinstaller packaging/sonoteca.spec --noconfirm --clean
#
# Tamaño: PyInstaller no puede saber qué módulos QML usa una app, así que al ver QtQml copia TODOS
# los módulos QML de Qt y, con ellos, sus bibliotecas (WebEngine, 3D, Charts...; cientos de MB).
# Aquí se podan los que Sonoteca no usa. La app solo importa QtQuick, QtQuick.Controls (estilo
# Basic), QtQuick.Layouts, QtQuick.Dialogs, QtQuick.Shapes y QtMultimedia.
# La lista se imprime en build/pruned.txt. Para desactivar la poda: SONOTECA_NO_PRUNE=1.
import os
import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent
VERSION = re.search(r'__version__ = "([^"]+)"',
                    (ROOT / "src" / "sonoteca" / "__init__.py").read_text(encoding="utf-8")).group(1)

# Fragmentos (en minúsculas) de la ruta destino; un archivo que contenga alguno se descarta.
PRUNE = [
    # módulos QML y bibliotecas de Qt que la app no usa
    "qt3d", "qt63d", "quick3d", "webengine", "webview", "qtcharts", "qt6charts", "datavisualization",
    "qtgraphs", "qt6graphs", "qtpdf", "qt6pdf", "qtsensors", "qt6sensors", "qtbluetooth", "qt6bluetooth",
    "qtnfc", "qt6nfc", "remoteobjects", "scxml", "texttospeech", "virtualkeyboard", "qtlocation",
    "qt6location", "qtdesigner", "qt6designer", "qthelp", "qt6help", "qml/qttest", "qml/qtquick/timeline",
    "qml/qt5compat", "qml/qtwebchannel", "qml/qtwebsockets", "qml/qtspatialaudio", "qml/qthttpserver",
    "qml/qtquick/pdf",
    # estilos de Quick Controls distintos de Basic (la app fuerza Basic en ui/app.py)
    "qml/qtquick/controls/material", "qml/qtquick/controls/universal", "qml/qtquick/controls/fusion",
    "qml/qtquick/controls/imagine", "qml/qtquick/controls/fluentwinui3", "qml/qtquick/controls/ios",
    "qml/qtquick/controls/macos", "qml/qtquick/controls/windows",
    # traducciones de Qt (los textos de la app están en español en el propio QML)
    "qt/translations/",
]

a = Analysis(
    [str(ROOT / "packaging" / "run_gui.py")],
    pathex=[str(ROOT / "src")],
    datas=[
        (str(ROOT / "src" / "sonoteca" / "ui" / "qml"), "sonoteca/ui/qml"),
        (str(ROOT / "src" / "sonoteca" / "ui" / "icon.png"), "sonoteca/ui"),   # icono de la ventana (QIcon en app.py)
    ],
    hiddenimports=collect_submodules("sonoteca") + ["keyring.backends"]
    + (["objc", "Foundation", "AppKit", "MediaPlayer"] if sys.platform == "darwin" else []),   # teclas multimedia (PyObjC)
    excludes=["pytest", "tkinter"],
)

if not os.environ.get("SONOTECA_NO_PRUNE"):
    def _keep(entry):
        dest = entry[0].replace("\\", "/").lower()
        return not any(token in dest for token in PRUNE)

    removed = [e[0] for e in list(a.binaries) + list(a.datas) if not _keep(e)]
    a.binaries = [e for e in a.binaries if _keep(e)]
    a.datas = [e for e in a.datas if _keep(e)]
    Path("build").mkdir(exist_ok=True)
    Path("build/pruned.txt").write_text("\n".join(sorted(removed)) + "\n", encoding="utf-8")
    print(f"[sonoteca.spec] podados {len(removed)} archivos (lista en build/pruned.txt)")

# Iconos del archivo ejecutable (se generan con packaging/make_icons.py). Windows incrusta el .ico en el .exe;
# macOS usa el .icns en el .app; Linux no incrusta iconos en el binario (ver packaging/linux/sonoteca.desktop).
ICON_DIR = ROOT / "assets" / "icons"
EXE_ICON = str(ICON_DIR / "sonoteca.ico") if sys.platform == "win32" else None

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="sonoteca",
    console=False,          # aplicación de ventana: sin terminal
    icon=EXE_ICON,
)
coll = COLLECT(exe, a.binaries, a.datas, name="sonoteca")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Sonoteca.app",
        icon=str(ICON_DIR / "sonoteca.icns"),
        bundle_identifier=None,   # TODO: definir un identificador propio antes de firmar/notarizar
        version=VERSION,
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": VERSION,
            "CFBundleDisplayName": "Sonoteca",
            "CFBundleName": "Sonoteca",
        },
    )
