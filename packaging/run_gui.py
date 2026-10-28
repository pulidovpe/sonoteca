"""Punto de entrada de la aplicación empaquetada (PyInstaller): abre la interfaz."""
import sys

from musicapp.ui.app import main

if __name__ == "__main__":
    sys.exit(main())
