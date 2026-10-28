"""Punto de entrada de la aplicación empaquetada (PyInstaller): abre la interfaz.

MUSICAPP_SELFTEST=1: prueba de humo para el empaquetado. Abre la interfaz y termina con código 0
tras unos segundos si la ventana cargó; si el QML no carga, `main()` devuelve 1 enseguida."""
import os
import sys

from musicapp.ui.app import main

if __name__ == "__main__":
    if os.environ.get("MUSICAPP_SELFTEST"):
        import threading

        timer = threading.Timer(5.0, lambda: os._exit(0))
        timer.daemon = True
        timer.start()
    sys.exit(main())
