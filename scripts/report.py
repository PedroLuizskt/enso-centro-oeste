#!/usr/bin/env python3
"""
Resumo cientifico em texto dos resultados (para compartilhar rapidamente).

Le os caches ja gerados (indices em data/processed/*.csv e clima em
data/processed/cache_climate_municipal.parquet) e imprime, por UF:
  - correlacao indice x clima no lag otimo, com p CORRIGIDO por autocorrelacao
  - composicao por fase (El Nino / La Nina / Neutro)
  - comparacao oceano x atmosfera (RONI/ONI/SOI)
  - varredura de janelas sazonais (qual periodo concentra o sinal)
  - sintese espacial dos municipios (gradiente latitudinal e significancia)

Uso (apos rodar 'enso-co' pelo menos uma vez):
    python scripts/report.py                # janela padrao do Config (OND)
    python scripts/report.py --season ALL   # sem recorte sazonal

Copie a saida inteira e cole na conversa para analisarmos juntos.
"""

import argparse
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from enso_co import analysis, gee, indices  # noqa: E402
from enso_co.cli import _meta_from_gdf  # noqa: E402
from enso_co.config import SEASON_WINDOWS, UF_NOME, Config  # noqa: E402

LINE = "=" * 72


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default=None, help="OND (padrao), DJF, ALL, ...")
    ap.add_argument("--no-standardize", action="store_true")
    ap.add_argument("--permutation", action="store_true",
                    help="Adiciona o teste de permutacao por deslocamento circular "
                         "(padrao-ouro; leva ~1 min).")
    ap.add_argument("--n-perm", type=int, default=1000)
    ap.add_argument("--fixed-lag", type=int, default=None,
                    help="Fixa a defasagem (recomendado 3 ou 4).")
    ap.add_argument("--lag-max", type=int, default=None)
    args = ap.parse_args()

    kw = {}
    if args.season:
        kw["season"] = args.season
    if args.no_standardize:
        kw["standardize"] = False
    if args.fixed_lag is not None:
        kw["fixed_lag"] = args.fixed_lag
    if args.lag_max is not None:
        kw["lag_max"] = args.lag_max
    cfg = Config(**kw)

    if not cfg.path_cache_climate.exists():
        print("[ERRO] Cache de clima nao encontrado:", cfg.path_cache_climate)
        print("       Rode 'enso-co' (com GEE) pelo menos uma vez antes deste resumo.")
        return 1

    gdf = gee.load_municipios(cfg)
    meta = _meta_from_gdf(gdf)
    climate = pd.read_parquet(cfg.path_cache_climate)
    idx_all = {n: indices.fetch_index(cfg, n) for n in ("RONI", "ONI", "SOI")}
    primary = idx_all[cfg.index_name]

    anom = analysis.monthly_anomalies(climate, standardize=cfg.standardize)
    uf_series = analysis.aggregate_to_uf(anom, meta)
    multi = analysis.multi_index_uf(uf_series, idx_all, cfg)
    unidade = "z" if cfg.standardize else "mm | C"

    print("\n" + LINE)
    print(f"RESUMO CIENTIFICO | ENSO x Centro-Oeste | {cfg.index_name} primario")
    print(f"Periodo {cfg.start_year}-{cfg.end_year} | {len(gdf)} municipios | "
          f"clima {climate['date'].min().date()} a {climate['date'].max().date()}")
    print(f"Janela sazonal: {cfg.season.upper()} {cfg.season_months} | "
          f"anomalia: {'z-score' if cfg.standardize else 'bruta'} ({unidade})")
    if cfg.fixed_lag is not None:
        lag_desc = f"FIXA em {cfg.fixed_lag}m (sem selecao multipla)"
    else:
        lag_desc = f"otimizada 0-{cfg.lag_max}m"
    print(f"Defasagem: {lag_desc}")
    print("p_eff = p corrigido por autocorrelacao (Bretherton et al. 1999)")
    print(LINE)

    for uf in cfg.estados:
        sub = uf_series[uf_series["uf"] == uf]
        if sub.empty:
            continue
        blk = analysis.analyze_uf(sub, primary, cfg)
        print(f"\n### {UF_NOME[uf]} ({uf})")
        for var, rot in (("precip", "PRECIPITACAO"), ("temp", "TEMPERATURA")):
            b = blk[var]["correlation"]["best"]
            c = blk[var]["composite"]
            flag = "SIGNIFICATIVO" if b["pearson_p_eff"] < cfg.alpha else "nao signif."
            print(f"  {rot}: r={b['pearson_r']:+.3f} (lag {b['lag']}m) | "
                  f"Spearman={b['spearman_r']:+.3f}")
            print(f"    n={b['n']} -> N_eff={b['n_eff']:.0f} | p_classico="
                  f"{b['pearson_p']:.4f} | p_eff={b['pearson_p_eff']:.4f} [{flag}]")
            print(f"    composicao: El Nino={c['El Nino']['mean']:+.3f} "
                  f"(n={c['El Nino']['n']}) | La Nina={c['La Nina']['mean']:+.3f} "
                  f"(n={c['La Nina']['n']}) | Neutro={c['Neutro']['mean']:+.3f}")
            if args.permutation:
                iv = primary.set_index("date")["value"]
                sd = sub.set_index("date").sort_index()
                season = (cfg.season_months
                          if cfg.season.upper() != "ALL" else None)
                pt = analysis.permutation_pvalue(
                    iv, sd[f"{var}_anom"], cfg.lag_max, season,
                    n_perm=args.n_perm, fixed_lag=cfg.fixed_lag)
                vd = ("SIGNIFICATIVO" if pt["p_perm"] < 0.05
                      else "marginal" if pt["p_perm"] < 0.10 else "nao signif.")
                print(f"    [permutacao] r={pt['r']:+.3f} lag {pt['lag']}m | "
                      f"p_perm={pt['p_perm']:.4f} "
                      f"(nulo p95={pt['null_p95']:.3f}) [{vd}]")
        print("  OCEANO x ATMOSFERA (chuva, lag otimo):")
        for r in multi.get(uf, []):
            mark = "*" if r["sig"] else " "
            print(f"    {r['index']:<5} ({r['kind'][:3]}): r={r['r']:+.3f} "
                  f"lag {r['lag']}m  p_eff={r['p']}{mark}")

    # ---------------- varredura de janelas sazonais ----------------
    print("\n" + LINE)
    print("VARREDURA DE JANELAS SAZONAIS (r indice x chuva; * = p_eff < 0.05)")
    print(LINE)
    hdr = f"{'JANELA':<12}" + "".join(f"{u:>15}" for u in cfg.estados)
    print(hdr + "\n" + "-" * len(hdr))
    for nome in ("ALL", "CHUVOSA", "SON", "OND", "NDJ", "DJF", "SECA"):
        months = SEASON_WINDOWS[nome]
        sel = None if nome == "ALL" else months
        row = f"{nome:<12}"
        for uf in cfg.estados:
            sub = uf_series[uf_series["uf"] == uf].set_index("date").sort_index()
            iv = primary.set_index("date")["value"]
            common = sub.index.intersection(iv.index)
            r, lag, p = analysis.best_lag_r(iv.loc[common],
                                            sub.loc[common, "precip_anom"],
                                            cfg.lag_max, sel, cfg.fixed_lag)
            cell = "—" if pd.isna(r) else f"{r:+.3f}(L{lag}){'*' if p < cfg.alpha else ''}"
            row += cell.rjust(15)
        print(row)

    # ---------------- diagnostico de lag na borda ----------------
    print("\n" + LINE)
    print("DIAGNOSTICO: lag otimo na borda da varredura")
    print(LINE)
    print("  Um lag otimo igual a lag_max sugere que o verdadeiro maximo pode estar")
    print("  fora do intervalo testado -- ou que a curva e plana e a escolha e arbitraria.")

    # ---------------- sintese espacial municipal ----------------
    print("\n" + LINE)
    print("SINTESE ESPACIAL (468 municipios, janela " + cfg.season.upper() + ")")
    print(LINE)
    muni = analysis.municipal_layers(anom, primary, meta, cfg)
    g = gdf.to_crs(cfg.crs_geo)
    # Centroide em CRS geografico: aproximacao suficiente para a latitude usada
    # no teste de gradiente (o aviso do geopandas nao se aplica ao uso aqui).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        lat = {str(row["CD_MUN"]): row.geometry.centroid.y
               for _, row in g.iterrows()}
    rs, las, sigs = [], [], 0
    for cd, m in muni.items():
        if m["r_precip"] is not None and cd in lat:
            rs.append(m["r_precip"]); las.append(lat[cd]); sigs += int(m["sig_precip"])
    rs, las = np.array(rs), np.array(las)
    print(f"  r(chuva): media={rs.mean():+.3f} | mediana={np.median(rs):+.3f} | "
          f"min={rs.min():+.3f} | max={rs.max():+.3f}")
    print(f"  negativos (El Nino seca): {(rs < 0).sum()}/{len(rs)} "
          f"({100*(rs < 0).mean():.0f}%)")
    print(f"  significativos (p_eff<{cfg.alpha}): {sigs}/{len(rs)} "
          f"({100*sigs/max(len(rs),1):.0f}%)")
    from scipy import stats as st
    sl, ic, rr, pp, se = st.linregress(las, rs)
    print(f"  gradiente latitudinal: slope={sl:+.4f}/grau | r={rr:+.3f} | p={pp:.2e}")
    print(f"    -> {'gradiente norte-sul COERENTE' if pp < 0.01 else 'sem gradiente claro'}")

    # lags na borda
    lags = [m["lag_precip"] for m in muni.values() if m["r_precip"] is not None]
    borda = sum(1 for l in lags if l == cfg.lag_max)
    print(f"  lag otimo na borda (={cfg.lag_max}m): {borda}/{len(lags)} "
          f"({100*borda/max(len(lags),1):.0f}%)"
          f"{'  [ATENCAO: considere aumentar lag_max]' if borda > 0.2*len(lags) else ''}")

    # coerencia espacial (Moran's I com k vizinhos mais proximos)
    try:
        from scipy.spatial import cKDTree
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pts = np.array([[row.geometry.centroid.x, row.geometry.centroid.y]
                            for _, row in gdf.to_crs(cfg.crs_geo).iterrows()])
        cds_ord = [str(c) for c in gdf["CD_MUN"]]
        vals = np.array([muni[c]["r_precip"] if muni.get(c, {}).get("r_precip") is not None
                         else np.nan for c in cds_ord])
        ok = ~np.isnan(vals)
        pts, vals = pts[ok], vals[ok]
        tree = cKDTree(pts)
        _, nb = tree.query(pts, k=9)
        W = np.zeros((len(vals), len(vals)))
        for i, row_nb in enumerate(nb):
            for j in row_nb[1:]:
                W[i, j] = 1.0
        W /= W.sum(axis=1, keepdims=True)
        z = vals - vals.mean()
        moran = (len(vals) / W.sum()) * (z @ W @ z) / (z @ z)
        print(f"  coerencia espacial (Moran's I, k=8): {moran:.3f}")
        print(f"    -> {'estrutura espacial forte (nao e ruido)' if moran > 0.3 else 'padrao espacialmente fraco'}")
    except Exception as exc:  # noqa: BLE001
        print(f"  [AVISO] Moran's I nao calculado: {exc}")

    print("\n" + LINE)
    print("Cole este resumo inteiro na conversa para interpretarmos os numeros.")
    print(LINE + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
