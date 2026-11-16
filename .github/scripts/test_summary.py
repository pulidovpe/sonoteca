#!/usr/bin/env python3
"""Resumen de pruebas JUnit (XML) en el resumen del job. Uso: test_summary.py <carpeta con TEST-*.xml>
Nunca rompe el job: si no hay informes, deja un aviso (::warning::), que suele indicar NO-SOURCE o una ruta cambiada."""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main(argv: list[str]) -> int:
    folder = Path(argv[1]) if len(argv) > 1 else Path(".")
    files = sorted(folder.glob("TEST-*.xml"))
    tests = failures = errors = skipped = 0
    suites = []
    for f in files:
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        t, fa, er, sk = (int(root.get(k, 0)) for k in ("tests", "failures", "errors", "skipped"))
        tests, failures, errors, skipped = tests + t, failures + fa, errors + er, skipped + sk
        suites.append((root.get("name", f.stem), t, fa + er, sk))

    if not files or tests == 0:
        print(f"::warning::No hay pruebas JUnit en {folder}: ¿NO-SOURCE o la ruta de informes cambió?")
        text = f"## Pruebas JVM de Android\n\n⚠️ No se encontraron informes en `{folder}`."
    else:
        lines = ["## Pruebas JVM de Android", "",
                 f"**{tests} pruebas** · fallos: {failures} · errores: {errors} · omitidas: {skipped}", "",
                 "| Clase | Pruebas | Fallos/errores | Omitidas |", "|---|---:|---:|---:|"]
        lines += [f"| `{n}` | {t} | {bad} | {sk} |" for n, t, bad, sk in suites]
        text = "\n".join(lines)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
