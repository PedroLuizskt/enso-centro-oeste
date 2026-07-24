#!/usr/bin/env python3
"""
Entrypoint do pipeline ENSO - Centro-Oeste.

Uso (a partir da raiz do repositorio):
    python scripts/build_dashboard.py                 # pipeline real (RONI + GEE)
    python scripts/build_dashboard.py --offline-demo  # dados sinteticos (sem GEE)
    python scripts/build_dashboard.py --force-index --force-climate

Equivalente a `python -m enso_co.cli` (ou ao comando `enso-co` apos pip install).
"""

import sys
from pathlib import Path

# Permite rodar sem instalar o pacote (adiciona src/ ao path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enso_co.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
