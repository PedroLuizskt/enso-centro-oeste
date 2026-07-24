#!/usr/bin/env python3
"""
Baixa as malhas municipais (2025) do IBGE para as 4 UFs do Centro-Oeste e as
descompacta em data/raw/{UF}_Municipios_2025/.

Uso:
    python scripts/download_ibge.py

Se voce ja tem os shapefiles (por exemplo, baixados manualmente do portal do
IBGE), basta coloca-los em data/raw/{UF}_Municipios_2025/ e pular este script.
O pipeline le exatamente esses caminhos.

Fonte oficial (malhas municipais por UF):
    https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/
Estrutura FTP (2025):
    https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/
        malhas_municipais/municipio_2025/UFs/{UF}/{UF}_Municipios_2025.zip
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UFS = ["MT", "MS", "GO", "DF"]

BASE = ("https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
        "malhas_municipais/municipio_2025/UFs")
HEADERS = {"User-Agent": "Mozilla/5.0"}


def download_uf(uf: str) -> None:
    dest = RAW / f"{uf}_Municipios_2025"
    if (dest / f"{uf}_Municipios_2025.shp").exists():
        print(f"[OK] {uf}: shapefile ja existe em {dest}")
        return
    url = f"{BASE}/{uf}/{uf}_Municipios_2025.zip"
    print(f"[..] {uf}: baixando {url}")
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=120) as resp:
            data = resp.read()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERRO] {uf}: falha no download ({exc}).")
        print(f"       Baixe manualmente do portal do IBGE e extraia em {dest}.")
        return
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(dest)
    print(f"[OK] {uf}: extraido em {dest}")


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for uf in UFS:
        download_uf(uf)
    print("\n[OK] Concluido. Verifique data/raw/ antes de rodar o pipeline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
