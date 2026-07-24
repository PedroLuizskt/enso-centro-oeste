# ENSO &middot; Centro-Oeste do Brasil — Monitor de Teleconexao Climatica

Analise reprodutivel da teleconexao entre o **El Nino-Oscilacao Sul (ENSO)** e o
clima do Centro-Oeste brasileiro (MT, MS, GO e DF), no nivel **municipal** (468
municipios), com um dashboard WebMap autonomo (`index.html`) que funciona
offline.

O projeto cruza tres indices oficiais da **NOAA/CPC** — **RONI**, **ONI** e
**SOI** — com **precipitacao (CHIRPS)** e **temperatura (ERA5-Land)** extraidas
via **Google Earth Engine**, e responde a duas perguntas:

1. Qual variavel climatica o ENSO mais modula no Centro-Oeste?
2. O lado **oceanico** (RONI/ONI) ou o **atmosferico** (SOI) do ENSO prevê melhor
   a chuva da regiao?

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![GEE](https://img.shields.io/badge/Google%20Earth%20Engine-CHIRPS%20%2B%20ERA5--Land-4285F4)
![Indices](https://img.shields.io/badge/NOAA%2FCPC-RONI%20%7C%20ONI%20%7C%20SOI-EE6C4D)
![License](https://img.shields.io/badge/license-MIT-green)

---

## A pergunta cientifica

Para o Centro-Oeste — bioma Cerrado, coracao do agronegocio, regime de chuvas
concentrado no verao e dependente da "safrinha" — a variavel que o ENSO mais
modula e a **precipitacao acumulada**. O regime pluviometrico da regiao e
fortemente sensivel a fase do ENSO: eventos de **El Nino** tendem a **reduzir** a
chuva com uma defasagem caracteristica de alguns meses, enquanto **La Nina**
tende a favorece-la. A temperatura responde tambem, mas como sinal secundario. O
dashboard trata precipitacao como variavel primaria e temperatura como
comparacao.

## Por que RONI (e nao so ONI)

Desde **fevereiro de 2026**, a NOAA adotou o **RONI (Relative Oceanic Nino
Index)** como metrica **oficial** de monitoramento do ENSO, no lugar do ONI. O
RONI subtrai da anomalia da regiao Nino 3.4 a media das anomalias tropicais
(20N-20S), removendo o **aquecimento de fundo** do oceano. Num clima em
aquecimento, o ONI classifica cada vez mais meses como "El Nino" simplesmente
porque o Pacifico esta mais quente em termos absolutos; o RONI corrige esse vies
e representa melhor o acoplamento oceano-atmosfera que efetivamente gera
teleconexoes de chuva. Por isso o RONI e o indice **primario** aqui, com o ONI
mantido para comparacao historica.

## Oceano x atmosfera: RONI/ONI vs SOI

O ENSO tem dois lados acoplados. O **oceanico** e medido por temperatura da
superficie do mar (RONI, ONI). O **atmosferico** e medido pelo **SOI (Southern
Oscillation Index)**, a gangorra de pressao ao nivel do mar entre o Taiti e
Darwin. Por convencao o SOI tem **sinal invertido**: SOI **negativo** = El Nino.
O dashboard correlaciona os tres indices com a chuva de cada UF no lag otimo e
mostra qual "lado" do ENSO melhor acompanha a precipitacao local — uma
comparacao que so faz sentido porque os tres sao medias moveis de 3 meses,
homogeneas entre si.

## Todos os dados vêm via Python (sem download manual)

Uma pergunta recorrente: e preciso baixar o RONI manualmente da pagina da CPC? **Nao.**
A CPC publica os tres indices em arquivos ASCII de URL fixa, atualizados
mensalmente, e o pipeline os baixa e faz cache automaticamente:

| Indice | Tipo | Arquivo (NOAA/CPC) | El Nino |
|--------|------|--------------------|---------|
| RONI | oceanico (primario) | `data/indices/RONI.ascii.txt` | valor > 0 |
| ONI  | oceanico (comparacao) | `data/indices/oni.ascii.txt` | valor > 0 |
| SOI  | atmosferico | `data/indices/soi.3m.txt` | valor < 0 |

A pagina `.../CWlink/MJO/enso.shtml` e apenas o **hub** de monitoramento do ENSO
(aponta para as series, mas nao hospeda tabelas proprias); os dados de fato saem
dos arquivos acima. Detalhe de implementacao: o servidor da NOAA rejeita o
`User-Agent` padrao do `requests` (HTTP 403), entao o cliente envia um cabecalho
de navegador.

Clima (via Google Earth Engine):

- Precipitacao: `UCSB-CHG/CHIRPS/DAILY` (banda `precipitation`, mm)
- Temperatura: `ECMWF/ERA5_LAND/MONTHLY_AGGR` (banda `temperature_2m`, K -> C)

Geometria: malhas **municipais 2025 do IBGE** (`data/raw/{UF}_Municipios_2025/`),
ja em SIRGAS 2000 (EPSG:4674).

## O que o dashboard mostra

- **Mapa municipal** dos 4 estados (468 municipios) com tres modos:
  anomalia de precipitacao, anomalia de temperatura e — o destaque — o **mapa de
  teleconexao**, que colore cada municipio pela correlacao RONI x chuva no lag
  otimo (onde o "aperto" do ENSO sobre a chuva e mais forte).
- **Drill-down estado -> municipio**, com zoom e leitura da correlacao local.
- **Serie temporal** por UF: anomalia climatica + linha do indice (RONI/ONI/SOI
  alternavel).
- **Correlacao** com varredura de defasagem (lag 0-6 meses), dispersao com reta
  OLS e o card **Oceano x Atmosfera**.
- **Composicao por fase** (El Nino / La Nina / Neutro) com media e desvio.
- **Regua RONI** como assinatura visual, ancorando a leitura da fase.

## Arquitetura

```
enso-centro-oeste/
├── src/enso_co/
│   ├── config.py      # dataclass Config: caminhos, URLs, assets, parametros
│   ├── indices.py     # RONI/ONI/SOI: download, parsing, classificacao de fase
│   ├── gee.py         # Earth Engine: extracao municipal em lote (reduceRegions)
│   ├── analysis.py    # anomalias, correlacao com lag, composicao, agregacao UF
│   ├── synthetic.py   # dados sinteticos p/ --offline-demo (sem GEE)
│   ├── template.py    # HTML + CSS + JS do dashboard (com placeholders)
│   ├── dashboard.py   # monta GeoJSON e injeta dados no template
│   └── cli.py         # orquestracao (run) + linha de comando
├── scripts/
│   ├── build_dashboard.py   # entrypoint: python scripts/build_dashboard.py
│   ├── download_ibge.py     # baixa as malhas municipais do IBGE
│   ├── report.py            # resumo cientifico em texto (com testes de robustez)
│   └── check_compat.py      # verifica compatibilidade com Python 3.10+
├── data/
│   ├── raw/           # shapefiles do IBGE (por UF)
│   └── processed/     # caches (indices .csv, clima .parquet)
├── docs/METODOLOGIA.md
├── index.html         # WebMap gerado (autonomo)
├── pyproject.toml     # torna o pacote instalavel (pip install -e .)
└── requirements.txt
```

O fluxo do `run()`: carrega municipios -> baixa indices (RONI/ONI/SOI) -> extrai
clima municipal (GEE) -> anomalias -> agrega para UF (media ponderada por area)
-> analise por UF -> camadas municipais (mapa anual + teleconexao) -> comparacao
oceano/atmosfera -> renderiza o `index.html`.

## Como reproduzir (PowerShell / VS Code no Windows)

No terminal integrado do VS Code (PowerShell), a partir da pasta do projeto:

```powershell
# 1. Ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# Se o PowerShell bloquear o script de ativacao, rode uma vez:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 2. Instalar (o pacote editavel ja puxa todas as dependencias)
python -m pip install --upgrade pip
pip install -e .
#   (alternativa: pip install -r requirements.txt)

# 3. Malhas municipais do IBGE
#    Opcao A: baixar automaticamente
python scripts\download_ibge.py
#    Opcao B: se voce ja tem os shapefiles, copie-os para data\raw\, ex.:
#      Copy-Item -Recurse "C:\...\MT_Municipios_2025" "data\raw\MT_Municipios_2025"
#    (o pipeline espera data\raw\{UF}_Municipios_2025\{UF}_Municipios_2025.shp)

# 4. Autenticar no Google Earth Engine (uma vez por maquina)
earthengine authenticate

# 5. Gerar o dashboard (pipeline real: RONI + GEE)
python scripts\build_dashboard.py
#   ou, apos o pip install -e .:  enso-co

# 6. Abrir o resultado
Invoke-Item .\index.html
```

Rodar sem GEE nem internet (geometria real, clima e indices sinteticos com a
teleconexao embutida) — util para testar a montagem do dashboard:

```powershell
python scripts\build_dashboard.py --offline-demo
```

Reprocessar ignorando os caches:

```powershell
python scripts\build_dashboard.py --force-index --force-climate
```

Explorar outras janelas sazonais (instantaneo, reaproveita o cache do GEE):

```powershell
enso-co --season DJF
enso-co --season ALL --no-standardize
python scripts\report.py                       # resumo cientifico em texto
enso-co --fixed-lag 4                          # sem selecao multipla
python scripts\report.py --fixed-lag 4 --permutation   # numeros definitivos
```

## Rigor estatistico (v0.3)

Tres decisoes separam este estudo de uma correlacao ingenua:

**Recorte sazonal.** A teleconexao ENSO nao e constante ao longo do ano. No
Cerrado o sinal se concentra no estabelecimento da estacao chuvosa; correlacionar
todos os meses mistura o auge das chuvas com o inverno seco (onde o desvio-padrao
da anomalia cai de ~48 mm para ~5 mm) e dilui o sinal. A janela padrao e **OND**
(outubro-novembro-dezembro), configuravel por `--season` (SON, NDJ, DJF, NDJF,
CHUVOSA, SECA, ALL).

**Padronizacao.** As anomalias sao convertidas em z-score por municipio/mes, de
modo que meses de variancia muito diferente contribuam de forma comparavel. Pode
ser desligado com `--no-standardize`.

**Defasagem fixa como alternativa a busca.** Otimizar o lag e depois testa-lo
usa o dado duas vezes. Como a curva de correlacao por defasagem e larga e
achatada no Centro-Oeste, `--fixed-lag 4` (RONI de JJA antecipando a chuva de
OND, a pratica de previsao sazonal) quase nao perde magnitude e recupera poder
estatistico -- no DF, o p de permutacao cai de 0,061 para 0,031.

**Significancia corrigida por autocorrelacao.** O RONI e uma media movel de 3
meses e tem autocorrelacao lag-1 de ~0,97; series climaticas tambem sao
autocorrelacionadas. O p-valor classico de Pearson pressupoe independencia e
superestima grosseiramente a significancia. O pipeline calcula o tamanho amostral
efetivo de Bretherton et al. (1999) e reporta `p_eff` ao lado do p classico. No
mapa de teleconexao, municipios com `p_eff >= 0.05` aparecem esmaecidos: o
numero existe, mas nao se distingue do acaso.

## Compatibilidade

O projeto declara Python 3.10 como minimo. Como o interpretador de
desenvolvimento pode ser mais recente e aceitar sintaxe que versoes anteriores
rejeitam (o caso tipico e a f-string com quebra de linha na expressao, liberada
so no 3.12 pelo PEP 701), ha uma verificacao dedicada:

```powershell
python scripts\check_compat.py
```

Ela compila todos os arquivos contra as gramaticas de 3.10, 3.11 e 3.12 sem
executa-los. Vale rodar antes de publicar qualquer alteracao.

## Decisoes de desenho

A analise **temporal** (serie, correlacao, composicao) e feita no nivel de **UF**
(agregacao por media ponderada de area a partir dos municipios), o que da um sinal
mais robusto e menos ruidoso. A analise **espacial** (mapas) permanece no nivel
**municipal**, aproveitando toda a resolucao do CHIRPS (~5,5 km). O mapa de
teleconexao — correlacao RONI x chuva por municipio no lag otimo — e a principal
contribuicao que a granularidade municipal viabiliza. As geometrias enviadas ao
GEE sao simplificadas (a resolucao do satelite e muito maior que o erro da
simplificacao), o que mantem a estatistica zonal fiel e o processamento leve.

## Limitacoes

Correlacao nao e causalidade; a teleconexao ENSO -> chuva e mediada por
circulacao atmosferica e varia entre eventos. O periodo padrao (2000-2024) cobre
poucas dezenas de eventos de cada fase, entao composicoes por fase tem incerteza.
O SOI de resolucao mensal e ruidoso; a versao de 3 meses usada aqui suaviza, mas
ainda assim o poder preditivo do lado atmosferico costuma ser inferior ao
oceanico para chuva sazonal.

## Fontes

- NOAA/CPC — indices ENSO: https://www.cpc.ncep.noaa.gov/data/indices/
- L'Heureux et al. (2024), *A Relative Sea Surface Temperature Index for
  Classifying ENSO Events in a Changing Climate* (base do RONI)
- CHIRPS/UCSB — precipitacao: https://www.chc.ucsb.edu/data/chirps
- ERA5-Land/ECMWF — temperatura
- IBGE — malhas municipais 2025

## Licenca

MIT. Ver `LICENSE`.
