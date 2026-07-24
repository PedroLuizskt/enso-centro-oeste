"""
Configuracao central do pipeline ENSO - Centro-Oeste.

Todos os caminhos, URLs, assets do Google Earth Engine e parametros de analise
ficam concentrados aqui. Nada de valores "magicos" espalhados pelo codigo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Raiz do repositorio (dois niveis acima de src/enso_co/config.py)
ROOT = Path(__file__).resolve().parents[2]

# ------------------------------------------------------------------------------
# Constantes de dominio
# ------------------------------------------------------------------------------

# Estados do Centro-Oeste (sigla -> nome)
UF_NOME: dict[str, str] = {
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "GO": "Goias",
    "DF": "Distrito Federal",
}

# Rotulo do trimestre movel (RONI/ONI) -> mes central (1-12).
# Ex.: DJF e centrado em janeiro; NDJ em dezembro.
SEASON_TO_MONTH: dict[str, int] = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}

# Janelas sazonais para recorte da analise (meses-calendario do CLIMA).
# OND e o estabelecimento da estacao chuvosa no Cerrado: e a janela em que o
# ENSO exerce maior influencia sobre a precipitacao do Centro-Oeste.
SEASON_WINDOWS: dict[str, tuple[int, ...]] = {
    "ALL":     tuple(range(1, 13)),          # todos os meses (sem recorte)
    "OND":     (10, 11, 12),                 # out-nov-dez  (recomendado)
    "SON":     (9, 10, 11),
    "NDJ":     (11, 12, 1),
    "DJF":     (12, 1, 2),
    "NDJF":    (11, 12, 1, 2),
    "CHUVOSA": (10, 11, 12, 1, 2, 3, 4),     # estacao chuvosa completa
    "SECA":    (5, 6, 7, 8, 9),
}

# Colunas dos shapefiles municipais do IBGE (malha 2025)
COL_CD_MUN = "CD_MUN"       # codigo IBGE de 7 digitos (chave unica)
COL_NM_MUN = "NM_MUN"       # nome do municipio
COL_SIGLA_UF = "SIGLA_UF"   # sigla da UF (MT/MS/GO/DF)
COL_AREA = "AREA_KM2"       # area em km2 (peso da agregacao para a UF)


@dataclass(frozen=True)
class Config:
    """Parametros do pipeline. Imutavel (frozen) para evitar efeitos colaterais."""

    # --- periodo de analise ---
    start_year: int = 2000
    end_year: int = 2024

    # --- indice ENSO ---
    # RONI e a metrica oficial da NOAA desde fev/2026 (remove o aquecimento de
    # fundo do Pacifico). Mesmo formato ASCII do ONI: trocar so a URL migra tudo.
    # O estudo tambem puxa ONI (oceanico, comparacao) e SOI (atmosferico), todos
    # como medias moveis de 3 meses -> comparacao "oceano x atmosfera" homogenea.
    index_name: str = "RONI"                 # indice primario (mapas, fases, regua)
    roni_url: str = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"
    oni_url: str = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
    soi_url: str = "https://www.cpc.ncep.noaa.gov/data/indices/soi.3m.txt"

    # --- Google Earth Engine ---
    asset_precip: str = "UCSB-CHG/CHIRPS/DAILY"          # banda: precipitation (mm)
    band_precip: str = "precipitation"
    scale_precip: int = 5566                             # ~0.05 graus (nativo CHIRPS)
    asset_temp: str = "ECMWF/ERA5_LAND/MONTHLY_AGGR"     # banda: temperature_2m (K)
    band_temp: str = "temperature_2m"
    scale_temp: int = 11132                              # ~0.1 grau (nativo ERA5-Land)
    gee_hv_endpoint: str = "https://earthengine-highvolume.googleapis.com"
    # Projeto do Google Cloud (exigido pelo Earth Engine atual). Definido via
    # variavel de ambiente EE_PROJECT ou pela flag --gee-project.
    gee_project: str = field(default_factory=lambda: os.environ.get("EE_PROJECT", ""))

    # --- estados alvo ---
    estados: tuple[str, ...] = ("MT", "MS", "GO", "DF")

    # --- geometria / projecao ---
    crs_geo: str = "EPSG:4674"       # SIRGAS 2000 (padrao IBGE; ja e o CRS dos shp)
    simplify_tol: float = 0.008      # tolerancia de simplificacao p/ GeoJSON no HTML

    # --- estatistica ---
    lag_max: int = 6                 # varredura de defasagem RONI->clima (meses)
    # Defasagem FIXA (meses). Quando definida, desliga a busca pelo lag otimo:
    # elimina a selecao multipla e torna o p-valor honesto sem permutacao. O
    # ganho de poder e real -- ver docs/METODOLOGIA.md, secao 5d. Use 3 ou 4
    # (RONI de JJA prevendo a chuva de OND), que e o padrao operacional de
    # previsao sazonal e coincide com o maximo empirico observado.
    fixed_lag: int | None = None
    # Janela sazonal aplicada ao CLIMA (o indice defasado pode vir de qualquer
    # mes). "OND" e o padrao cientifico deste estudo; "ALL" desliga o recorte.
    season: str = "OND"
    standardize: bool = True         # z-score da anomalia por municipio/mes
    alpha: float = 0.05              # nivel de significancia dos mapas

    # --- eventos de referencia (anos-pico) ---
    evento_el_nino: int = 2015       # El Nino Muito Forte 2015/16
    evento_la_nina: int = 2010       # La Nina Forte 2010/11

    @property
    def season_months(self) -> tuple[int, ...]:
        """Meses-calendario da janela sazonal configurada."""
        return SEASON_WINDOWS.get(self.season.upper(), SEASON_WINDOWS["ALL"])

    # ---------------------------------------------------------------- caminhos
    @property
    def dir_raw(self) -> Path:
        return ROOT / "data" / "raw"

    @property
    def dir_processed(self) -> Path:
        return ROOT / "data" / "processed"

    def path_shapefile(self, uf: str) -> Path:
        """Shapefile municipal do IBGE para uma UF."""
        name = f"{uf}_Municipios_2025"
        return self.dir_raw / name / f"{name}.shp"

    def path_cache_index(self, name: str) -> Path:
        return self.dir_processed / f"cache_{name.lower()}.csv"

    @property
    def path_cache_climate(self) -> Path:
        return self.dir_processed / "cache_climate_municipal.parquet"

    @property
    def path_html(self) -> Path:
        return ROOT / "index.html"
