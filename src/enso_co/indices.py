"""
Indices ENSO da NOAA/CPC: download, parsing e classificacao de fase.

O estudo trabalha com tres indices, todos como medias moveis de 3 meses e todos
puxaveis via Python (nenhum download manual):

  RONI  (oceanico, PRIMARIO) - Relative Oceanic Nino Index. Metrica oficial da
        NOAA desde fev/2026; subtrai a media tropical (20N-20S) da anomalia da
        Nino 3.4, removendo o aquecimento de fundo do Pacifico. El Nino > 0.
  ONI   (oceanico, comparacao) - Oceanic Nino Index classico (base movel).
        Serie historica mais longa; comparar com RONI mostra o efeito do ajuste
        de tendencia. El Nino > 0.
  SOI   (atmosferico) - Southern Oscillation Index (Tahiti - Darwin, SLP
        padronizado, media 3 meses). E o "outro lado" do ENSO: o gangorra de
        pressao. Convencao INVERTIDA: El Nino < 0 (SOI negativo).

Comparar o poder preditivo do oceano (RONI/ONI) contra a atmosfera (SOI) sobre a
chuva do Centro-Oeste e uma das contribuicoes cientificas do projeto.

Formatos de arquivo:
  RONI/ONI  -> tabela "longa": SEAS YR [TOTAL] ANOM (trimestre movel por linha).
  SOI (3m)  -> tabela "larga" de largura fixa: YEAR + 12 colunas mensais; ausente
               = -999.9. Fixed-width e obrigatorio: quando o valor e -999.9, ele
               cola no ano (ex.: "1951-999.9").
"""

from __future__ import annotations

import io
import logging

import numpy as np
import pandas as pd
import requests

from .config import SEASON_TO_MONTH, Config

log = logging.getLogger("enso_co")

# O servidor da NOAA responde 403 ao User-Agent padrao do requests.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/plain,*/*",
}

# Metadados dos indices. el_nino_sign: sinal do indice numa fase quente.
INDEX_META: dict[str, dict] = {
    "RONI": {"kind": "oceanico", "fmt": "seasonal", "el_nino_sign": +1,
             "label": "RONI", "desc": "Relative Oceanic Nino Index"},
    "ONI":  {"kind": "oceanico", "fmt": "seasonal", "el_nino_sign": +1,
             "label": "ONI", "desc": "Oceanic Nino Index"},
    "SOI":  {"kind": "atmosferico", "fmt": "wide", "el_nino_sign": -1,
             "label": "SOI", "desc": "Southern Oscillation Index (3m)"},
}


# ---------------------------------------------------------------- classificacao
def classify_phase(value: float) -> str:
    """Intensidade de fase a partir de um valor de indice OCEANICO (limiar +/-0.5)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "Sem dado"
    if value >= 2.0:
        return "El Nino Muito Forte"
    if value >= 1.5:
        return "El Nino Forte"
    if value >= 1.0:
        return "El Nino Moderado"
    if value >= 0.5:
        return "El Nino Fraco"
    if value <= -1.5:
        return "La Nina Forte"
    if value <= -1.0:
        return "La Nina Moderada"
    if value <= -0.5:
        return "La Nina Fraca"
    return "Neutro"


def phase_group(value: float) -> str:
    """Reduz a classificacao as tres macro-fases (indice oceanico)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "Neutro"
    if value >= 0.5:
        return "El Nino"
    if value <= -0.5:
        return "La Nina"
    return "Neutro"


# ---------------------------------------------------------------- parsers
def _parse_seasonal(text: str) -> pd.DataFrame:
    """RONI/ONI: tabela longa SEAS YR [TOTAL] ANOM -> date, value."""
    df = pd.read_csv(io.StringIO(text), sep=r"\s+", engine="python")
    df.columns = [c.strip().upper() for c in df.columns]
    if not {"SEAS", "YR", "ANOM"}.issubset(df.columns):
        raise ValueError(f"Colunas inesperadas (seasonal): {list(df.columns)}")
    df = df[["SEAS", "YR", "ANOM"]].copy()
    df["SEAS"] = df["SEAS"].astype(str).str.strip()
    df["YR"] = pd.to_numeric(df["YR"], errors="coerce")
    df["ANOM"] = pd.to_numeric(df["ANOM"], errors="coerce")
    df = df.dropna(subset=["YR", "ANOM"])
    df["month"] = df["SEAS"].map(SEASON_TO_MONTH)
    df = df.dropna(subset=["month"])
    df["date"] = pd.to_datetime(dict(year=df["YR"].astype(int),
                                     month=df["month"].astype(int), day=1))
    return (df.rename(columns={"ANOM": "value"})[["date", "value"]]
            .sort_values("date").reset_index(drop=True))


def _parse_soi_wide(text: str) -> pd.DataFrame:
    """SOI 3m: tabela larga de largura fixa (YEAR + 12 meses) -> date, value."""
    # Largura fixa: YEAR=4, depois 12 campos de 6 chars. Necessario porque
    # "-999.9" cola no ano quando o valor esta ausente (ex.: "1951-999.9").
    widths = [4] + [6] * 12
    names = ["YEAR"] + ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                        "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    df = pd.read_fwf(io.StringIO(text), widths=widths, names=names, skiprows=1)
    df["YEAR"] = pd.to_numeric(df["YEAR"], errors="coerce")
    df = df.dropna(subset=["YEAR"])
    long = df.melt(id_vars="YEAR", var_name="mon", value_name="value")
    mon_num = {m: i + 1 for i, m in enumerate(names[1:])}
    long["month"] = long["mon"].map(mon_num)
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    long = long[long["value"] > -900]  # descarta sentinela -999.9
    long["date"] = pd.to_datetime(dict(year=long["YEAR"].astype(int),
                                       month=long["month"].astype(int), day=1))
    return long[["date", "value"]].sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------- fetch
def _url_for(cfg: Config, name: str) -> str:
    return {"RONI": cfg.roni_url, "ONI": cfg.oni_url, "SOI": cfg.soi_url}[name]


def fetch_index(cfg: Config, name: str, force: bool = False) -> pd.DataFrame:
    """
    Baixa (com cache) um indice pelo nome (RONI/ONI/SOI).

    Retorna DataFrame com colunas date, value. Para indices oceanicos, adiciona
    tambem phase e group (classificacao). O SOI nao recebe fase (convencao
    invertida; e usado so na comparacao de correlacao).
    """
    name = name.upper()
    if name not in INDEX_META:
        raise ValueError(f"Indice desconhecido: {name}")

    cache = cfg.path_cache_index(name)
    if cache.exists() and not force:
        log.info("[OK] %s em cache: %s", name, cache.name)
        df = pd.read_csv(cache, parse_dates=["date"])
    else:
        url = _url_for(cfg, name)
        log.info("[..] Baixando %s de %s", name, url)
        resp = requests.get(url, headers=_HEADERS, timeout=60)
        resp.raise_for_status()
        fmt = INDEX_META[name]["fmt"]
        df = _parse_seasonal(resp.text) if fmt == "seasonal" else _parse_soi_wide(resp.text)
        cache.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache, index=False)
        log.info("[OK] %s: %d meses (%s a %s)", name, len(df),
                 df["date"].min().date(), df["date"].max().date())

    if INDEX_META[name]["el_nino_sign"] > 0:  # oceanico
        df["phase"] = df["value"].apply(classify_phase)
        df["group"] = df["value"].apply(phase_group)
    return df


def fetch_all(cfg: Config, force: bool = False) -> dict[str, pd.DataFrame]:
    """Baixa RONI, ONI e SOI. Se algum secundario falhar, segue sem ele."""
    out: dict[str, pd.DataFrame] = {}
    for name in ("RONI", "ONI", "SOI"):
        try:
            out[name] = fetch_index(cfg, name, force=force)
        except Exception as exc:  # noqa: BLE001
            if name == cfg.index_name:
                raise
            log.warning("[AVISO] Nao foi possivel obter %s (%s); seguindo sem ele.",
                        name, exc)
    return out
