"""
Extracao climatica via Google Earth Engine, no nivel municipal.

Estrategia central (sem gargalo): uma imagem de 2 bandas por mes
(precipitacao acumulada CHIRPS + temperatura media ERA5-Land) e uma unica
chamada ``reduceRegions`` sobre a FeatureCollection dos municipios. Isso da
1 ``getInfo`` por mes para TODOS os municipios, em vez de laco por poligono ou
por pixel.

As geometrias sao simplificadas antes de irem ao GEE: a resolucao do CHIRPS
(~5,5 km) e do ERA5-Land (~11 km) e muito maior que o erro da simplificacao,
entao a estatistica zonal permanece fiel enquanto o payload fica leve.
"""

from __future__ import annotations

import logging

import geopandas as gpd
import pandas as pd

from .config import COL_AREA, COL_CD_MUN, COL_NM_MUN, COL_SIGLA_UF, Config

log = logging.getLogger("enso_co")

# Simplificacao da geometria enviada ao GEE (graus; ~0.01 deg ~ 1 km).
_GEE_SIMPLIFY = 0.01


def init_gee(cfg: Config) -> None:
    """Inicializa a API do Earth Engine no endpoint high-volume."""
    import ee
    kwargs = {"opt_url": cfg.gee_hv_endpoint}
    if cfg.gee_project:
        kwargs["project"] = cfg.gee_project
    try:
        ee.Initialize(**kwargs)
    except Exception:
        ee.Authenticate()
        ee.Initialize(**kwargs)
    proj = cfg.gee_project or "(projeto padrao das credenciais)"
    log.info("[OK] Google Earth Engine inicializado | projeto: %s", proj)


def load_municipios(cfg: Config) -> gpd.GeoDataFrame:
    """Carrega e concatena os shapefiles municipais das 4 UFs alvo."""
    frames = []
    for uf in cfg.estados:
        shp = cfg.path_shapefile(uf)
        if not shp.exists():
            raise FileNotFoundError(
                f"Shapefile nao encontrado: {shp}\n"
                f"Rode 'python scripts/download_ibge.py' ou coloque as malhas em data/raw/."
            )
        g = gpd.read_file(shp)[[COL_CD_MUN, COL_NM_MUN, COL_SIGLA_UF, COL_AREA, "geometry"]]
        frames.append(g)
    gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)
    gdf = gdf.to_crs(cfg.crs_geo)
    log.info("[OK] %d municipios carregados (%s).", len(gdf), ", ".join(cfg.estados))
    return gdf


def _fc_from_gdf(gdf: gpd.GeoDataFrame):
    """Converte o GeoDataFrame em ee.FeatureCollection com geometria simplificada."""
    import ee
    g = gdf.copy()
    g["geometry"] = g.geometry.simplify(_GEE_SIMPLIFY, preserve_topology=True)
    feats = []
    for _, row in g.iterrows():
        geom = ee.Geometry(row.geometry.__geo_interface__)
        feats.append(ee.Feature(geom, {"cd_mun": str(row[COL_CD_MUN])}))
    return ee.FeatureCollection(feats)


def extract_climate(cfg: Config, gdf: gpd.GeoDataFrame, force: bool = False) -> pd.DataFrame:
    """
    Extrai precipitacao (mm/mes) e temperatura (C/mes) por municipio e mes.

    Retorna DataFrame longo: cd_mun, date, precip, temp. Faz cache em Parquet.
    """
    cache = cfg.path_cache_climate
    if cache.exists() and not force:
        log.info("[OK] Clima municipal em cache: %s", cache.name)
        return pd.read_parquet(cache)

    import ee
    fc = _fc_from_gdf(gdf)
    precip_ic = ee.ImageCollection(cfg.asset_precip).select(cfg.band_precip)
    temp_ic = ee.ImageCollection(cfg.asset_temp).select(cfg.band_temp)

    months = pd.date_range(f"{cfg.start_year}-01-01", f"{cfg.end_year}-12-01", freq="MS")
    rows: list[dict] = []
    log.info("[..] Extraindo %d meses x %d municipios via reduceRegions...",
             len(months), len(gdf))

    for i, m in enumerate(months):
        start = ee.Date.fromYMD(m.year, m.month, 1)
        end = start.advance(1, "month")
        precip_img = precip_ic.filterDate(start, end).sum().rename("precip")
        temp_img = (temp_ic.filterDate(start, end).mean()
                    .subtract(273.15).rename("temp"))
        img = precip_img.addBands(temp_img)

        # Uma chamada para todos os municipios naquele mes.
        reduced = img.reduceRegions(
            collection=fc,
            reducer=ee.Reducer.mean(),
            scale=cfg.scale_precip,
        )
        try:
            feats = reduced.getInfo()["features"]
        except Exception as exc:  # noqa: BLE001
            log.warning("[AVISO] Falha no mes %s: %s", m.date(), exc)
            continue

        for f in feats:
            p = f["properties"]
            rows.append({
                "cd_mun": p.get("cd_mun"),
                "date": m,
                "precip": p.get("precip"),
                "temp": p.get("temp"),
            })

        if (i + 1) % 24 == 0:
            log.info("    ... %d/%d meses", i + 1, len(months))

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)
    log.info("[OK] Clima municipal extraido e salvo: %d linhas.", len(df))
    return df
