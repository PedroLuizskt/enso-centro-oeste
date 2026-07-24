"""
Orquestracao do pipeline ENSO - Centro-Oeste e interface de linha de comando.

Fluxo (run):
    municipios -> indices (RONI/ONI/SOI) -> clima municipal (GEE ou sintetico)
    -> anomalias -> agregacao UF -> analise por UF -> camadas municipais
    -> comparacao oceano/atmosfera -> render do index.html
"""

from __future__ import annotations

import argparse
import logging
import sys

import numpy as np
import pandas as pd

from . import analysis, dashboard, gee, indices, synthetic
from .config import COL_AREA, COL_CD_MUN, COL_NM_MUN, COL_SIGLA_UF, Config

log = logging.getLogger("enso_co")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )


def _meta_from_gdf(gdf) -> pd.DataFrame:
    """Extrai metadados (cd_mun, nm_mun, sigla_uf, area) para agregacao/rotulos."""
    meta = gdf[[COL_CD_MUN, COL_NM_MUN, COL_SIGLA_UF, COL_AREA]].copy()
    meta = meta.rename(columns={COL_CD_MUN: "cd_mun", COL_NM_MUN: "nm_mun"})
    meta["cd_mun"] = meta["cd_mun"].astype(str)
    return meta


def run(cfg: Config, offline_demo: bool = False,
        force_index: bool = False, force_climate: bool = False) -> str:
    """Executa o pipeline e escreve o index.html. Retorna o caminho gerado."""
    log.info("=" * 70)
    log.info("ENSO - Centro-Oeste | indice primario: %s | %d-%d", 
             cfg.index_name, cfg.start_year, cfg.end_year)
    log.info("Janela sazonal: %s %s | anomalia: %s | defasagem: %s%s",
             cfg.season.upper(), cfg.season_months,
             "z-score (padronizada)" if cfg.standardize else "bruta (mm / C)",
             (f"FIXA em {cfg.fixed_lag}m" if cfg.fixed_lag is not None
              else f"otimizada 0-{cfg.lag_max}m"),
             " | MODO DEMO (dados sinteticos)" if offline_demo else "")
    log.info("=" * 70)

    # 1. Geometria municipal (sempre real)
    gdf = gee.load_municipios(cfg)
    meta = _meta_from_gdf(gdf)

    # 2. Indices e clima
    if offline_demo:
        rng = np.random.default_rng(2024)
        idx_all = synthetic.make_indices(cfg, rng)
        climate = synthetic.make_climate(cfg, gdf.to_crs(cfg.crs_geo),
                                          idx_all[cfg.index_name], rng)
    else:
        idx_all = indices.fetch_all(cfg, force=force_index)
        # So conecta ao Earth Engine se realmente for extrair: com o cache de
        # clima ja gravado, reprocessar outra janela sazonal e instantaneo e
        # dispensa credenciais.
        if force_climate or not cfg.path_cache_climate.exists():
            gee.init_gee(cfg)
        else:
            log.info("[OK] Cache de clima encontrado: GEE nao sera acionado.")
        climate = gee.extract_climate(cfg, gdf, force=force_climate)

    primary = idx_all[cfg.index_name]

    # 3. Anomalias e agregacao
    anom = analysis.monthly_anomalies(climate, standardize=cfg.standardize)
    uf_series = analysis.aggregate_to_uf(anom, meta)

    # 4. Analise por UF (timeseries, correlacao, composicao)
    analysis_by_uf = {
        uf: analysis.analyze_uf(uf_series[uf_series["uf"] == uf], primary, cfg)
        for uf in cfg.estados if (uf_series["uf"] == uf).any()
    }

    # 5. Camadas municipais (mapa anual + mapa de teleconexao)
    muni_layers = analysis.municipal_layers(anom, primary, meta, cfg)

    # 6. Comparacao oceano x atmosfera
    multi = analysis.multi_index_uf(uf_series, idx_all, cfg)

    # 7. Render
    html = dashboard.render_html(cfg, gdf, analysis_by_uf, muni_layers, multi, idx_all)
    cfg.path_html.parent.mkdir(parents=True, exist_ok=True)
    cfg.path_html.write_text(html, encoding="utf-8")
    log.info("=" * 70)
    log.info("[OK] WebMap gerado: %s  (%.1f KB)",
             cfg.path_html, len(html.encode()) / 1024)
    log.info("  Abra o index.html no navegador (funciona offline).")
    log.info("=" * 70)
    return str(cfg.path_html)


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="enso-co",
        description="Pipeline ENSO x clima do Centro-Oeste (RONI/ONI/SOI + GEE).",
    )
    p.add_argument("--offline-demo", action="store_true",
                   help="Gera dados sinteticos (sem GEE nem download de indices).")
    p.add_argument("--force-index", action="store_true",
                   help="Rebaixa os indices da NOAA, ignorando o cache.")
    p.add_argument("--force-climate", action="store_true",
                   help="Reprocessa o clima via GEE, ignorando o cache.")
    p.add_argument("--start-year", type=int, default=None)
    p.add_argument("--end-year", type=int, default=None)
    p.add_argument("--season", type=str, default=None,
                   help="Janela sazonal do clima: OND (padrao), SON, NDJ, DJF, "
                        "NDJF, CHUVOSA, SECA ou ALL (sem recorte).")
    p.add_argument("--fixed-lag", type=int, default=None,
                   help="Fixa a defasagem (meses) em vez de buscar o lag otimo. "
                        "Elimina a selecao multipla; recomendado 3 ou 4.")
    p.add_argument("--lag-max", type=int, default=None,
                   help="Limite superior da varredura de defasagem (padrao 6).")
    p.add_argument("--no-standardize", action="store_true",
                   help="Usa anomalia bruta (mm / C) em vez de z-score.")
    p.add_argument("--gee-project", type=str, default=None,
                   help="ID do projeto do Google Cloud para o Earth Engine "
                        "(sobrepoe a variavel de ambiente EE_PROJECT).")
    return p.parse_args(argv)


def main(argv=None) -> int:
    _setup_logging()
    args = parse_args(argv)
    kwargs = {}
    if args.start_year:
        kwargs["start_year"] = args.start_year
    if args.end_year:
        kwargs["end_year"] = args.end_year
    if args.season:
        kwargs["season"] = args.season
    if args.fixed_lag is not None:
        kwargs["fixed_lag"] = args.fixed_lag
    if args.lag_max is not None:
        kwargs["lag_max"] = args.lag_max
    if args.no_standardize:
        kwargs["standardize"] = False
    if args.gee_project:
        kwargs["gee_project"] = args.gee_project
    cfg = Config(**kwargs)
    try:
        run(cfg, offline_demo=args.offline_demo,
            force_index=args.force_index, force_climate=args.force_climate)
    except FileNotFoundError as exc:
        log.error("[ERRO] %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
