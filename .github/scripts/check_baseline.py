#!/usr/bin/env python3
"""Compara los fallos de pytest con la lista de fallos conocidos (.github/known-failures.txt).

Uso: check_baseline.py <salida_de_pytest.log> <pytest_exit_code> [known-failures.txt]

Requiere que pytest se haya ejecutado con ``-rfE`` (resumen corto de FAILED/ERROR).
- Sale con 0 si no hay fallos, o si todos los fallos están en la lista.
- Sale con 1 si hay algún fallo NUEVO, o si pytest terminó mal sin poder leer los fallos
  (código distinto de 0/1: error interno, uso incorrecto, ningún test recogido...).
- Los fallos conocidos que ya no fallan se avisan (hay que quitarlos de la lista), sin romper.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def parse_failures(log: str) -> set[str]:
    """Identificadores de las líneas «FAILED id - msg» / «ERROR id - msg» del resumen de pytest."""
    ids: set[str] = set()
    for line in log.splitlines():
        for prefix in ("FAILED ", "ERROR "):
            if line.startswith(prefix):
                rest = line[len(prefix):].strip()
                ids.add(rest.split(" - ", 1)[0].strip())
    return ids


def parse_baseline(text: str) -> set[str]:
    return {ln.strip() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")}


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    log = Path(argv[1]).read_text(encoding="utf-8", errors="replace")
    rc = int(argv[2])
    base_path = Path(argv[3] if len(argv) > 3 else ".github/known-failures.txt")
    known = parse_baseline(base_path.read_text(encoding="utf-8")) if base_path.exists() else set()
    failed = parse_failures(log)

    out: list[str] = ["## Resultado de pytest frente a fallos conocidos", ""]
    status = 0

    if rc not in (0, 1):
        out.append(f"❌ pytest terminó con código {rc} (no es «tests fallidos»: error interno, uso o nada recogido).")
        status = 1
    elif rc == 1 and not failed:
        out.append("❌ pytest falló pero no se pudo leer ningún FAILED/ERROR del resumen.")
        status = 1

    new = sorted(failed - known)
    still = sorted(failed & known)
    fixed = sorted(known - failed) if rc in (0, 1) else []

    if new:
        status = 1
        out += [f"❌ **{len(new)} fallo(s) NUEVO(S)** (no están en la lista de conocidos):", ""]
        out += [f"- `{i}`" for i in new] + [""]
    if still:
        out += [f"⚠️ {len(still)} fallo(s) conocido(s) siguen fallando (no rompen la CI).", ""]
    if fixed:
        out += [f"✅ {len(fixed)} conocido(s) ya NO fallan: quítalos de `{base_path}`:", ""]
        out += [f"- `{i}`" for i in fixed] + [""]
    if status == 0 and not failed:
        out.append("✅ Todos los tests pasan.")
    if failed:
        out += ["### Lista actual de fallos (formato de `known-failures.txt`)", "", "```"]
        out += sorted(failed) + ["```"]

    text = "\n".join(out)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
