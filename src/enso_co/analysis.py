"""
Analise estatistica da teleconexao ENSO x clima.

Etapas:
  1. Anomalias mensais (remove o ciclo sazonal por municipio/mes), com opcao de
     padronizacao (z-score) por municipio/mes.
  2. Agregacao municipal -> UF (media ponderada por area).
  3. Correlacao indice x anomalia com varredura de defasagem (lag) e RECORTE
     SAZONAL do clima.
  4. Composicao por macro-fase (El Nino / La Nina / Neutro).
  5. Correlacao por municipio no lag otimo, com significancia (mapa).

Convencao de defasagem: correlaciona indice(t - lag) contra anomalia(t). Um lag
positivo significa que o oceano ANTECEDE a resposta climatica local.

Recorte sazonal: o filtro se aplica ao MES DO CLIMA (variavel resposta). O indice
defasado pode vir de qualquer mes -- e justamente isso que da poder preditivo
(ex.: o estado do Pacifico em julho ajuda a prever a chuva de novembro).

Significancia: series climaticas mensais e indices ENSO sao fortemente
autocorrelacionados (o RONI e uma media movel de 3 meses, com autocorrelacao
lag-1 proxima de 0,97). O p-valor classico de Pearson pressupoe observacoes
independentes e, por isso, superestima a significancia. Aplica-se aqui o tamanho
amostral efetivo de Bretherton et al. (1999):

    N_eff = N * (1 - a1*a2) / (1 + a1*a2)

onde a1 e a2 sao as autocorrelacoes de lag 1 das duas series. N_eff e limitado ao
intervalo [3, N] (quando a autocorrelacao de uma das series e negativa, a formula
pode exceder N, o que nao teria sentido pratico).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats

from .config import COL_AREA, COL_SIGLA_UF, Config

log = logging.getLogger("enso_co")


# ------------------------------------------------------------------ anomalias
def monthly_anomalies(df: pd.DataFrame, standardize: bool = False) -> pd.DataFrame:
    """
    Adiciona precip_anom e temp_anom removendo a climatologia mes-a-mes por
    municipio. Com standardize=True, divide pelo desvio-padrao do mesmo
    municipio/mes (z-score), tornando comparaveis meses de variancia muito
    diferente (no Cerrado, julho e dezembro diferem em uma ordem de grandeza).
    """
    df = df.copy()
    df["month"] = df["date"].dt.month
    for var in ("precip", "temp"):
        grp = df.groupby(["cd_mun", "month"])[var]
        anom = df[var] - grp.transform("mean")
        if standardize:
            sd = grp.transform("std").replace(0, np.nan)
            anom = anom / sd
        df[f"{var}_anom"] = anom
    return df


# ------------------------------------------------------- agregacao municipal->UF
def aggregate_to_uf(df: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega a serie municipal para a UF por media ponderada de area.

    `meta` traz cd_mun, sigla_uf, area. Retorna serie mensal por UF com
    precip, temp e suas anomalias.
    """
    m = df.merge(meta, on="cd_mun", how="left")
    out = []
    for (uf, date), g in m.groupby([COL_SIGLA_UF, "date"]):
        w = g[COL_AREA].to_numpy(dtype=float)
        rec = {"uf": uf, "date": date}
        for var in ("precip", "temp", "precip_anom", "temp_anom"):
            v = g[var].to_numpy(dtype=float)
            mask = ~np.isnan(v)
            rec[var] = (float(np.sum(v[mask] * w[mask]) / np.sum(w[mask]))
                        if mask.any() else np.nan)
        out.append(rec)
    return pd.DataFrame(out).sort_values(["uf", "date"]).reset_index(drop=True)


# ------------------------------------------------------------- significancia
def _lag1_autocorr(x: np.ndarray) -> float:
    """Autocorrelacao de lag 1, ignorando NaN."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 3:
        return 0.0
    a, b = x[:-1], x[1:]
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def effective_n(x: np.ndarray, y: np.ndarray, n: int) -> float:
    """Tamanho amostral efetivo (Bretherton et al., 1999), limitado a [3, n]."""
    a1, a2 = _lag1_autocorr(x), _lag1_autocorr(y)
    denom = 1.0 + a1 * a2
    if denom <= 0:
        return 3.0
    neff = n * (1.0 - a1 * a2) / denom
    return float(min(max(neff, 3.0), n))


def _p_from_r(r: float, neff: float) -> float:
    """p-valor bicaudal do coeficiente de correlacao dado o N efetivo."""
    if neff <= 2 or abs(r) >= 1:
        return float("nan")
    t = r * np.sqrt((neff - 2) / max(1 - r ** 2, 1e-12))
    return float(2 * (1 - stats.t.cdf(abs(t), neff - 2)))


# ------------------------------------------------- teste de permutacao (ouro)
def permutation_pvalue(index_s: pd.Series, clim_s: pd.Series, lag_max: int,
                       season_months: tuple | None = None,
                       n_perm: int = 1000, seed: int = 42,
                       fixed_lag: int | None = None) -> dict:
    """
    p-valor por deslocamento circular do indice ("circular shift test").

    E o padrao-ouro aqui porque resolve DOIS problemas de uma vez:

    1. Autocorrelacao: deslocar a serie circularmente preserva integralmente sua
       estrutura temporal (ao contrario da permutacao simples, que a destroi e
       produziria um teste demasiado permissivo).
    2. Selecao do lag: a cada deslocamento refaz-se a varredura completa e
       guarda-se o max|r|. A distribuicao nula passa a ser a do MAXIMO sobre os
       lags, e nao a de um lag isolado -- que e exatamente o que se compara,
       ja que o r observado tambem foi escolhido como maximo.

    Retorna {"r": r observado, "lag": lag otimo, "p_perm": p, "n_perm": n,
             "null_p95": percentil 95 da distribuicao nula}.
    """
    common = index_s.index.intersection(clim_s.index)
    idx_v = index_s.loc[common].to_numpy(dtype=float)
    clim = clim_s.loc[common]
    dates = common
    n = len(idx_v)
    if n < 36:
        return {"r": np.nan, "lag": 0, "p_perm": np.nan,
                "n_perm": 0, "null_p95": np.nan}

    lags = [fixed_lag] if fixed_lag is not None else range(lag_max + 1)

    def _max_abs_r(vals) -> tuple:
        s = pd.Series(vals, index=dates)
        best_r, best_lag = 0.0, (fixed_lag or 0)
        for lag in lags:
            pair = pd.concat([s.shift(lag), clim], axis=1, keys=["i", "c"]).dropna()
            if season_months:
                pair = pair[pair.index.month.isin(season_months)]
            if len(pair) < 12:
                continue
            r = float(stats.pearsonr(pair["i"], pair["c"])[0])
            if abs(r) > abs(best_r):
                best_r, best_lag = r, lag
        return best_r, best_lag

    r_obs, lag_obs = _max_abs_r(idx_v)
    rng = np.random.default_rng(seed)
    # Deslocamentos minimos de 12 meses evitam sobreposicao com o sinal real.
    null = np.empty(n_perm)
    for i in range(n_perm):
        sh = int(rng.integers(12, max(13, n - 12)))
        null[i] = abs(_max_abs_r(np.roll(idx_v, sh))[0])
    p = float((np.sum(null >= abs(r_obs)) + 1) / (n_perm + 1))
    return {"r": round(float(r_obs), 3), "lag": int(lag_obs),
            "p_perm": round(p, 4), "n_perm": int(n_perm),
            "null_p95": round(float(np.percentile(null, 95)), 3)}


# ----------------------------------------------------------------- correlacao
def correlate_with_lags(index_s: pd.Series, clim_s: pd.Series, lag_max: int,
                        season_months: tuple | None = None,
                        fixed_lag: int | None = None) -> dict:
    """
    Correlaciona index(t-lag) x clim(t) para lag em 0..lag_max.

    index_s e clim_s sao Series indexadas por data (calendario mensal comum).
    season_months restringe os MESES DO CLIMA considerados (None = todos).

    Retorna dict com per_lag (lista) e best (maior |Pearson|). Cada entrada traz
    o p-valor classico (pearson_p) e o corrigido por autocorrelacao
    (pearson_p_eff), alem de n e n_eff.
    """
    lags = [fixed_lag] if fixed_lag is not None else range(lag_max + 1)
    per_lag = []
    for lag in lags:
        pair = pd.concat([index_s.shift(lag), clim_s], axis=1,
                         keys=["i", "c"]).dropna()
        if season_months:
            pair = pair[pair.index.month.isin(season_months)]
        if len(pair) < 12:
            continue
        xi, yc = pair["i"].to_numpy(), pair["c"].to_numpy()
        pr, pp = stats.pearsonr(xi, yc)
        sr, sp = stats.spearmanr(xi, yc)
        neff = effective_n(xi, yc, len(pair))
        per_lag.append({
            "lag": lag,
            "pearson_r": round(float(pr), 3),
            "pearson_p": round(float(pp), 4),
            "pearson_p_eff": round(_p_from_r(float(pr), neff), 4),
            "spearman_r": round(float(sr), 3),
            "spearman_p": round(float(sp), 4),
            "n": int(len(pair)),
            "n_eff": round(neff, 1),
        })
    if not per_lag:
        return {"per_lag": [], "best": None}
    best = max(per_lag, key=lambda d: abs(d["pearson_r"]))
    return {"per_lag": per_lag, "best": best}


def best_lag_r(index_s: pd.Series, clim_s: pd.Series, lag_max: int,
               season_months: tuple | None = None,
               fixed_lag: int | None = None) -> tuple:
    """Retorna (Pearson r, lag, p corrigido). Com fixed_lag, nao ha busca."""
    res = correlate_with_lags(index_s, clim_s, lag_max, season_months, fixed_lag)
    if res["best"] is None:
        return (np.nan, 0, np.nan)
    b = res["best"]
    return (b["pearson_r"], b["lag"], b["pearson_p_eff"])


# ----------------------------------------------------------------- composicao
def phase_composites(clim_anom: pd.Series, groups: pd.Series,
                     season_months: tuple | None = None) -> dict:
    """Media/desvio/n da anomalia climatica em cada macro-fase ENSO."""
    if season_months:
        clim_anom = clim_anom[clim_anom.index.month.isin(season_months)]
    g = groups.reindex(clim_anom.index)
    out = {}
    for ph in ("El Nino", "La Nina", "Neutro"):
        vals = clim_anom[g == ph].dropna()
        out[ph] = {
            "mean": round(float(vals.mean()), 3) if len(vals) else 0.0,
            "std": round(float(vals.std()), 3) if len(vals) else 0.0,
            "n": int(len(vals)),
        }
    return out


# -------------------------------------------------------------------- scatter
def build_scatter(index_lagged: pd.Series, clim_anom: pd.Series,
                  season_months: tuple | None = None) -> dict:
    """Pontos + reta OLS para a dispersao indice x anomalia."""
    pair = pd.concat([index_lagged, clim_anom], axis=1, keys=["x", "y"]).dropna()
    if season_months:
        pair = pair[pair.index.month.isin(season_months)]
    if len(pair) < 3:
        return {"points": [], "slope": 0, "intercept": 0, "x_min": -2, "x_max": 2}
    lr = stats.linregress(pair["x"], pair["y"])
    return {
        "points": [{"x": round(float(a), 3), "y": round(float(b), 2)}
                   for a, b in zip(pair["x"], pair["y"])],
        "slope": round(float(lr.slope), 3),
        "intercept": round(float(lr.intercept), 3),
        "x_min": round(float(pair["x"].min()), 2),
        "x_max": round(float(pair["x"].max()), 2),
    }


# ------------------------------------------------------------- analise por UF
def analyze_uf(uf_series: pd.DataFrame, index_df: pd.DataFrame,
               cfg: Config) -> dict:
    """
    Bloco analitico de uma UF: serie temporal alinhada ao indice, correlacao com
    lag, composicao e dispersao, para precipitacao e temperatura.

    A serie temporal exibida no dashboard mantem TODOS os meses (contexto
    visual); o recorte sazonal incide sobre as estatisticas.
    """
    idx = index_df.set_index("date")["value"]
    grp = index_df.set_index("date")["group"]
    s = uf_series.set_index("date").sort_index()

    common = s.index.intersection(idx.index)
    s, idx_a, grp_a = s.loc[common], idx.loc[common], grp.loc[common]
    season = cfg.season_months if cfg.season.upper() != "ALL" else None

    block = {
        "timeseries": {
            "dates": [d.strftime("%Y-%m") for d in s.index],
            "oni": [round(float(v), 2) if pd.notna(v) else None for v in idx_a],
            "precip_anom": [round(float(v), 2) if pd.notna(v) else None
                            for v in s["precip_anom"]],
            "temp_anom": [round(float(v), 2) if pd.notna(v) else None
                          for v in s["temp_anom"]],
        },
        "season": cfg.season.upper(),
        "standardized": bool(cfg.standardize),
    }

    for var, key in (("precip_anom", "precip"), ("temp_anom", "temp")):
        corr = correlate_with_lags(idx_a, s[var], cfg.lag_max, season,
                                   cfg.fixed_lag)
        best_lag = corr["best"]["lag"] if corr["best"] else 0
        block[key] = {
            "correlation": corr,
            "scatter": build_scatter(idx_a.shift(best_lag), s[var], season),
            "composite": phase_composites(s[var], grp_a, season),
        }
    return block


# ---------------------------------------------- correlacao/anomalia municipal
def municipal_layers(df_anom: pd.DataFrame, index_df: pd.DataFrame,
                     meta: pd.DataFrame, cfg: Config) -> dict:
    """
    Produz, por municipio:
      - r_precip/lag_precip/p_precip (+ flag de significancia) e os equivalentes
        de temperatura, no lag otimo, com recorte sazonal e p corrigido por
        autocorrelacao -> mapa de teleconexao
      - anomalia anual media por ano -> mapa coropletico anual
    """
    idx = index_df.set_index("date")["value"]
    df_anom = df_anom.copy()
    df_anom["year"] = df_anom["date"].dt.year
    meta_map = meta.set_index("cd_mun")
    season = cfg.season_months if cfg.season.upper() != "ALL" else None

    result: dict = {}
    n_sig = 0
    for cd, g in df_anom.groupby("cd_mun"):
        s = g.sort_values("date").set_index("date")
        common = s.index.intersection(idx.index)
        idx_a = idx.loc[common]

        rp, lp, pp = best_lag_r(idx_a, s.loc[common, "precip_anom"],
                                cfg.lag_max, season, cfg.fixed_lag)
        rt, lt, pt = best_lag_r(idx_a, s.loc[common, "temp_anom"],
                                cfg.lag_max, season, cfg.fixed_lag)
        sig = bool(pd.notna(pp) and pp < cfg.alpha)
        n_sig += int(sig)

        annual = {}
        for yr, gy in g.groupby("year"):
            annual[str(int(yr))] = {
                "precip_anom": (round(float(gy["precip_anom"].mean()), 2)
                                if gy["precip_anom"].notna().any() else None),
                "temp_anom": (round(float(gy["temp_anom"].mean()), 2)
                              if gy["temp_anom"].notna().any() else None),
            }

        row = meta_map.loc[cd] if cd in meta_map.index else None
        result[str(cd)] = {
            "nm": str(row["nm_mun"]) if row is not None else str(cd),
            "uf": str(row[COL_SIGLA_UF]) if row is not None else "",
            "r_precip": None if pd.isna(rp) else rp,
            "lag_precip": int(lp),
            "p_precip": None if pd.isna(pp) else round(float(pp), 4),
            "sig_precip": sig,
            "r_temp": None if pd.isna(rt) else rt,
            "lag_temp": int(lt),
            "p_temp": None if pd.isna(pt) else round(float(pt), 4),
            "annual": annual,
        }

    log.info("[OK] Camadas municipais: %d municipios | %d com chuva significativa "
             "(p<%.2f, janela %s).", len(result), n_sig, cfg.alpha,
             cfg.season.upper())
    return result


# ------------------------------------------------ comparacao oceano x atmosfera
def multi_index_uf(uf_series: pd.DataFrame, indices: dict,
                   cfg: Config) -> dict:
    """
    Para cada UF e cada indice (RONI/ONI/SOI), correlaciona no lag otimo contra a
    anomalia de PRECIPITACAO. Responde: o oceano (RONI/ONI) ou a atmosfera (SOI)
    acompanha melhor a chuva do Centro-Oeste?
    """
    from .indices import INDEX_META

    season = cfg.season_months if cfg.season.upper() != "ALL" else None
    out: dict = {}
    for uf, g in uf_series.groupby("uf"):
        s = g.set_index("date").sort_index()["precip_anom"]
        rows = []
        for name, idf in indices.items():
            iv = idf.set_index("date")["value"]
            common = s.index.intersection(iv.index)
            if len(common) < 24:
                continue
            r, lag, p = best_lag_r(iv.loc[common], s.loc[common],
                                   cfg.lag_max, season, cfg.fixed_lag)
            if pd.isna(r):
                continue
            rows.append({
                "index": name,
                "kind": INDEX_META[name]["kind"],
                "r": round(float(r), 3),
                "abs_r": round(abs(float(r)), 3),
                "lag": int(lag),
                "p": None if pd.isna(p) else round(float(p), 4),
                "sig": bool(pd.notna(p) and p < cfg.alpha),
            })
        rows.sort(key=lambda d: d["abs_r"], reverse=True)
        out[uf] = rows
    log.info("[OK] Comparacao multi-indice (oceano x atmosfera) por UF concluida.")
    return out
