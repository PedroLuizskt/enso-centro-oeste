"""
Montagem do WebMap autonomo (index.html).

Serializa todos os dados (analise por UF, camadas municipais, indices, geometria)
como JSON embutido e injeta no template via str.replace (nunca str.format, para
nao colidir com as chaves literais de CSS/JS).
"""

from __future__ import annotations

import json
import logging
from datetime import date

import geopandas as gpd
import pandas as pd

from .config import COL_CD_MUN, COL_NM_MUN, COL_SIGLA_UF, UF_NOME, Config
from .indices import phase_group
from .template import HTML_TEMPLATE, JS_LOGIC

log = logging.getLogger("enso_co")


def build_geojson(gdf: gpd.GeoDataFrame, cfg: Config) -> dict:
    """GeoJSON dos municipios, simplificado para exibicao, com props cd/nm/uf."""
    g = gdf.copy().to_crs(cfg.crs_geo)
    g["geometry"] = g.geometry.simplify(cfg.simplify_tol, preserve_topology=True)
    feats = []
    for _, row in g.iterrows():
        feats.append({
            "type": "Feature",
            "properties": {
                "cd": str(row[COL_CD_MUN]),
                "nm": str(row[COL_NM_MUN]),
                "uf": str(row[COL_SIGLA_UF]),
            },
            "geometry": row.geometry.__geo_interface__,
        })
    return {"type": "FeatureCollection", "features": feats}


def _indices_payload(indices: dict[str, pd.DataFrame], cfg: Config) -> dict:
    """{name: {dates:[YYYY-MM], value:[...]}} restrito ao periodo de analise."""
    lo = pd.Timestamp(f"{cfg.start_year}-01-01")
    hi = pd.Timestamp(f"{cfg.end_year}-12-01")
    out = {}
    for name, df in indices.items():
        d = df[(df["date"] >= lo) & (df["date"] <= hi)].sort_values("date")
        out[name] = {
            "dates": [x.strftime("%Y-%m") for x in d["date"]],
            "value": [round(float(v), 2) if pd.notna(v) else None for v in d["value"]],
        }
    return out


def render_html(
    cfg: Config,
    gdf: gpd.GeoDataFrame,
    analysis: dict,
    muni_layers: dict,
    multi: dict,
    indices: dict[str, pd.DataFrame],
) -> str:
    """Preenche o template e retorna o HTML final do dashboard."""
    primary = cfg.index_name
    idx_primary = indices[primary].sort_values("date")
    last = idx_primary.dropna(subset=["value"]).iloc[-1]
    last_val = float(last["value"])
    last_month = pd.Timestamp(last["date"]).strftime("%b/%Y")

    # municipios por UF (para o seletor de foco), ordenados por nome
    muni_by_uf: dict[str, list] = {uf: [] for uf in cfg.estados}
    for cd, m in muni_layers.items():
        if m["uf"] in muni_by_uf:
            muni_by_uf[m["uf"]].append({"cd": cd, "nm": m["nm"]})
    for uf in muni_by_uf:
        muni_by_uf[uf].sort(key=lambda x: x["nm"])

    anos = list(range(cfg.start_year, cfg.end_year + 1))
    geojson = build_geojson(gdf, cfg)
    # union_all() existe a partir do geopandas 1.0; antes disso, unary_union.
    geom = gdf.to_crs(cfg.crs_geo).geometry
    try:
        cent = geom.union_all().centroid
    except AttributeError:  # geopandas < 1.0
        cent = geom.unary_union.centroid

    uf_options = "".join(
        f'<option value="{uf}"{" selected" if i == 0 else ""}>{UF_NOME[uf]} ({uf})</option>'
        for i, uf in enumerate(cfg.estados)
    )
    year_options = "".join(
        f'<option value="{y}"{" selected" if y == anos[-1] else ""}>{y}</option>'
        for y in anos
    )

    def js(obj) -> str:
        return json.dumps(obj, ensure_ascii=False)

    repl = {
        "{START_YEAR}": str(cfg.start_year),
        "{END_YEAR}": str(cfg.end_year),
        "{INDEX_PRIMARY}": primary,
        "{MES_ULTIMO}": last_month,
        "{ONI_ULTIMO}": (f"+{last_val:.2f}" if last_val >= 0 else f"{last_val:.2f}"),
        "{DATA_HOJE}": date.today().strftime("%d/%m/%Y"),
        "{UF_OPTIONS}": uf_options,
        "{YEAR_OPTIONS}": year_options,
        "{CENTER_LAT}": f"{cent.y:.4f}",
        "{CENTER_LON}": f"{cent.x:.4f}",
        "{EVENTO_EL_NINO}": str(cfg.evento_el_nino),
        "{EVENTO_LA_NINA}": str(cfg.evento_la_nina),
        "{SEASON}": cfg.season.upper(),
        "{STANDARDIZED}": "true" if cfg.standardize else "false",
        "{ANALYSIS_JS}": js(analysis),
        "{MUNI_JS}": js(muni_layers),
        "{MULTI_JS}": js(multi),
        "{INDICES_JS}": js(_indices_payload(indices, cfg)),
        "{GEOJSON_JS}": js(geojson),
        "{UF_NOME_JS}": js(UF_NOME),
        "{ESTADOS_JS}": js(list(cfg.estados)),
        "{ANOS_JS}": js(anos),
        "{MUNI_BY_UF_JS}": js(muni_by_uf),
    }

    html = HTML_TEMPLATE.replace("{JS_LOGIC}", JS_LOGIC)
    for k, v in repl.items():
        html = html.replace(k, v)
    return html
