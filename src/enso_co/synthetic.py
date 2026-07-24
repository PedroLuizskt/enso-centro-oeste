"""
Dados sinteticos para o modo --offline-demo (sem Google Earth Engine).

Usa a geometria REAL dos municipios (shapefiles do IBGE), mas sintetiza clima e
indices com uma teleconexao ENSO embutida e cientificamente plausivel:

  - RONI: ciclo ENSO (periodo ~3.5 anos) + ruido.
  - ONI:  RONI + leve tendencia de aquecimento (ilustra o motivo do RONI).
  - SOI:  anti-correlacionado ao RONI (gangorra atmosferica) + ruido.
  - Precipitacao municipal: ciclo sazonal do cerrado + resposta NEGATIVA ao RONI
    defasado ~2-3 meses (El Nino seca a regiao) + ruido. A forca da resposta
    varia com a latitude, gerando um mapa de correlacao espacialmente coerente.
  - Temperatura municipal: ciclo sazonal + resposta POSITIVA fraca ao RONI.

Semente fixa -> saida reproduzivel (util para testes e CI).
"""

from __future__ import annotations

import logging
import warnings

import numpy as np
import pandas as pd

from .config import COL_CD_MUN, Config
from .indices import classify_phase, phase_group

log = logging.getLogger("enso_co")


def _months(cfg: Config) -> pd.DatetimeIndex:
    return pd.date_range(f"{cfg.start_year}-01-01", f"{cfg.end_year}-12-01", freq="MS")


def make_indices(cfg: Config, rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    """Gera RONI, ONI e SOI sinteticos coerentes entre si."""
    dates = _months(cfg)
    t = np.arange(len(dates))
    # Ciclo ENSO: combinacao de dois periodos (~3.6 e ~5 anos) + ruido suavizado
    base = 1.15 * np.sin(2 * np.pi * t / 43) + 0.55 * np.sin(2 * np.pi * t / 61 + 1.0)
    noise = pd.Series(rng.normal(0, 0.5, len(t))).rolling(3, min_periods=1).mean().to_numpy()
    roni = np.round(base + noise, 2)

    warming = 0.010 * (t - t.mean()) / 12.0     # ~0.01 C/ano de fundo
    oni = np.round(roni + warming + rng.normal(0, 0.05, len(t)), 2)
    soi = np.round(-0.9 * roni + rng.normal(0, 0.35, len(t)), 1)  # atmosfera invertida

    def _ocean(vals):
        d = pd.DataFrame({"date": dates, "value": vals})
        d["phase"] = d["value"].apply(classify_phase)
        d["group"] = d["value"].apply(phase_group)
        return d

    return {
        "RONI": _ocean(roni),
        "ONI": _ocean(oni),
        "SOI": pd.DataFrame({"date": dates, "value": soi}),
    }


def make_climate(cfg: Config, gdf, roni: pd.DataFrame,
                 rng: np.random.Generator) -> pd.DataFrame:
    """Gera clima municipal com teleconexao embutida (usa geometria real)."""
    dates = _months(cfg)
    month_of = np.array([d.month for d in dates])
    roni_v = roni.set_index("date")["value"].reindex(dates).to_numpy()
    lag = 2                                            # El Nino antecede a chuva ~2m
    roni_lag = pd.Series(roni_v).shift(lag).fillna(0).to_numpy()

    # Ciclo sazonal do cerrado: chuva concentrada no verao (out-mar)
    seasonal_p = 150 + 130 * np.cos(2 * np.pi * (month_of - 1) / 12)
    seasonal_t = 24 + 3.2 * np.cos(2 * np.pi * (month_of - 1) / 12 + np.pi)

    # O centroide em CRS geografico gera aviso do geopandas por nao ser exato em
    # area. Aqui ele so define a latitude aproximada usada para modular a forca
    # da teleconexao sintetica, entao o erro e irrelevante.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cents = gdf.geometry.centroid
    lat = cents.y.to_numpy()
    lat_norm = (lat - lat.min()) / ((lat.max() - lat.min()) or 1)

    rows = []
    for i, (_, row) in enumerate(gdf.iterrows()):
        # Forca da teleconexao varia com a latitude (norte responde mais)
        beta_p = -28 - 18 * lat_norm[i]                # El Nino -> menos chuva
        beta_t = 0.35 + 0.25 * (1 - lat_norm[i])       # El Nino -> leve aquecimento
        p_noise = rng.normal(0, 22, len(dates))
        t_noise = rng.normal(0, 0.6, len(dates))
        precip = np.clip(seasonal_p + beta_p * roni_lag + p_noise, 0, None)
        temp = seasonal_t + beta_t * roni_lag + t_noise
        cd = str(row[COL_CD_MUN])
        for j, d in enumerate(dates):
            rows.append({"cd_mun": cd, "date": d,
                         "precip": round(float(precip[j]), 1),
                         "temp": round(float(temp[j]), 2)})
    df = pd.DataFrame(rows)
    log.info("[OK] Clima sintetico gerado: %d municipios x %d meses.",
             gdf.shape[0], len(dates))
    return df
