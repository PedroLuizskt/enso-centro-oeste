# Metodologia

Detalhamento tecnico do pipeline de teleconexao ENSO x clima do Centro-Oeste.

## 1. Indices ENSO (NOAA/CPC)

O estudo usa tres indices, todos como medias moveis de 3 meses e todos obtidos
por download automatico (arquivos ASCII de URL fixa, com cache local).

**RONI (Relative Oceanic Nino Index)** — indice primario. E a media movel de 3
meses das anomalias de TSM (ERSST v5) na regiao Nino 3.4 (5N-5S, 170-120W),
subtraida a media das anomalias tropicais (20N-20S) e reescalada para preservar a
variancia original da Nino 3.4. Base 1991-2020. Metrica oficial da NOAA desde
02/2026. Arquivo com 3 colunas: `SEAS YR ANOM`.

**ONI (Oceanic Nino Index)** — comparacao. Media movel de 3 meses das anomalias
da Nino 3.4 com periodos-base moveis. Serie mais longa e classificacao classica.
Arquivo com 4 colunas: `SEAS YR TOTAL ANOM` (o parser seleciona `ANOM`).

**SOI (Southern Oscillation Index, 3 meses)** — lado atmosferico. Diferenca
padronizada de pressao ao nivel do mar Taiti - Darwin. Convencao invertida: SOI
negativo em El Nino. Arquivo em formato de largura fixa (YEAR + 12 meses;
ausente = -999.9). A leitura de largura fixa e obrigatoria porque o sentinela
"-999.9" cola na coluna do ano (ex.: `1951-999.9`).

Cada rotulo trimestral e mapeado ao **mes central** (DJF -> janeiro, ...,
NDJ -> dezembro), produzindo uma serie mensal comum aos tres indices.

Classificacao de fase (indices oceanicos), pelo limiar NOAA de +/-0.5 C:
El Nino (>= 0.5) e La Nina (<= -0.5), com intensidades Fraco/Moderado/Forte/Muito
Forte; entre -0.5 e 0.5, Neutro.

## 2. Dados climaticos (Google Earth Engine)

**Precipitacao**: `UCSB-CHG/CHIRPS/DAILY`, banda `precipitation` (mm), somada por
mes. Resolucao nativa ~0,05 grau (~5,5 km).

**Temperatura**: `ECMWF/ERA5_LAND/MONTHLY_AGGR`, banda `temperature_2m` (K),
media mensal convertida para C. Resolucao nativa ~0,1 grau (~11 km).

Extracao no nivel municipal por estatistica zonal: para cada mes monta-se uma
imagem de 2 bandas (precipitacao acumulada + temperatura media) e faz-se uma
unica chamada `reduceRegions` com o redutor de media sobre a FeatureCollection
dos 468 municipios. Isso resulta em uma requisicao `getInfo` por mes para toda a
regiao, evitando lacos por poligono ou por pixel. As geometrias sao simplificadas
antes de irem ao GEE; como a resolucao dos satelites e muito maior que o erro de
simplificacao, a estatistica zonal permanece fiel.

## 3. Anomalias e padronizacao

Para cada municipio, remove-se o **ciclo sazonal** subtraindo a climatologia
mes-a-mes (media de cada mes-calendario ao longo do periodo). Assim,
`precip_anom` e `temp_anom` isolam o desvio em relacao ao comportamento tipico
daquele mes, que e o sinal onde a modulacao do ENSO aparece.

Por padrao a anomalia e ainda **padronizada** (z-score) pelo desvio-padrao do
mesmo municipio/mes. Sem isso, a correlacao de Pearson sobre a serie completa e
dominada pelos meses de alta variancia: no Cerrado, o desvio-padrao da anomalia
de chuva vai de ~48 mm em dezembro a ~5 mm em julho, quase uma ordem de
grandeza.

## 3b. Recorte sazonal

A teleconexao ENSO e sazonalmente dependente: o mesmo indice tem efeitos de
magnitude e ate de sinal diferentes conforme o mes-alvo. Por isso as estatisticas
sao calculadas dentro de uma **janela sazonal** (padrao: OND, o estabelecimento
da estacao chuvosa). O filtro incide sobre o mes do **clima**; o indice defasado
pode vir de qualquer mes -- e exatamente isso que confere poder preditivo, pois o
estado do Pacifico em julho ajuda a antecipar a chuva de novembro.

## 4. Agregacao municipio -> UF

Para as analises temporais, as series municipais sao agregadas a UF por **media
ponderada pela area** (`AREA_KM2` do IBGE). A ponderacao por area evita que muitos
municipios pequenos dominem a media da UF.

## 5. Correlacao com defasagem (lag)

Correlaciona-se `indice(t - lag)` contra `anomalia(t)`, para lag de 0 a 6 meses.
Um lag positivo significa que o oceano **antecede** a resposta climatica local.
Para cada lag calcula-se Pearson e Spearman (com p-valor) e o **lag otimo** e o de
maior |Pearson|. Spearman entra como checagem de robustez a nao-linearidade:
quando Pearson e Spearman divergem em sinal, nao ha relacao monotonica confiavel.

**Significancia corrigida.** Series climaticas mensais e indices ENSO sao
fortemente autocorrelacionados -- o RONI, por ser media movel de 3 meses, tem
autocorrelacao lag-1 de aproximadamente 0,97. O p-valor classico de Pearson
pressupoe observacoes independentes e, aplicado diretamente, superestima a
significancia (uma serie de 300 meses pode conter o equivalente a poucas dezenas
de graus de liberdade). Adota-se o tamanho amostral efetivo de
Bretherton et al. (1999):

    N_eff = N * (1 - a1*a2) / (1 + a1*a2)

com a1 e a2 as autocorrelacoes de lag 1 das duas series, limitando N_eff ao
intervalo [3, N]. O p-valor e entao recalculado com N_eff graus de liberdade e
reportado como `p_eff`. Os mapas usam `p_eff` para decidir o que e sinal e o que
e ruido.

## 5b. Teste de permutacao (padrao-ouro)

A correcao por N efetivo trata a autocorrelacao, mas nao a **selecao do lag**:
ao escolher o maior |r| entre sete defasagens e reportar o p daquele lag, o
resultado e otimista, pois o mesmo dado foi usado para escolher e para testar.

O teste de deslocamento circular resolve os dois problemas simultaneamente. O
indice e rotacionado ciclicamente (o que preserva integralmente sua
autocorrelacao, ao contrario da permutacao simples) e, a cada rotacao, refaz-se a
varredura completa de lags guardando o max|r|. A distribuicao nula passa a ser a
do maximo sobre os lags -- a mesma estatistica que se observou. O p-valor e a
fracao de rotacoes que atingem ou superam o |r| observado.

Disponivel em `analysis.permutation_pvalue()` e em
`python scripts/report.py --permutation`. E computacionalmente caro, por isso nao
integra o fluxo padrao: use-o para validar as conclusoes finais.

## 5d. Defasagem fixa versus otimizada

Buscar o lag de maior |r| entre sete candidatos e depois testar aquele mesmo lag
e uma forma sutil de usar o dado duas vezes. Ha duas saidas legitimas.

A primeira e manter a busca e pagar o preco no teste, usando o deslocamento
circular descrito acima, cuja hipotese nula ja e a do maximo sobre os lags.

A segunda, mais poderosa, e **fixar a defasagem a priori** (`--fixed-lag`). Nesse
caso nao ha selecao, e o p classico corrigido por N efetivo volta a ser valido.
No Centro-Oeste a curva de correlacao por defasagem e larga e achatada -- entre
lag 0 e 6 a variacao e pequena, com maximo raso em 3-4 meses --, de modo que
fixar em 3 ou 4 quase nao sacrifica magnitude e devolve poder estatistico. A
escolha tem respaldo fisico: o lag 4 corresponde ao RONI de junho-julho-agosto
antecipando a chuva de outubro-dezembro, que e a pratica operacional de previsao
sazonal.

O ganho e mensuravel. No Distrito Federal, a correlacao com busca livre resulta
em p de permutacao de 0,061 (marginal); com o lag fixado em 3 meses, o mesmo dado
produz p de 0,031 (significativo). Nao se trata de escolher o resultado mais
conveniente: e que o teste sem selecao multipla e simplesmente mais sensivel.

Um sintoma de que a busca esta atrapalhando e o lag otimo encostar no limite da
varredura. O relatorio contabiliza esses casos; uma proporcao alta indica que a
curva e plana e a escolha, arbitraria -- momento de fixar a defasagem.

## 5c. Significancia de campo e coerencia espacial

Testes locais municipio a municipio sofrem de multiplicidade: com 468 testes a
5%, esperam-se ~23 falsos positivos mesmo sem sinal algum. A pergunta relevante
nao e quantos municipios isolados passam, e sim se o **campo** tem estrutura.

Por isso o relatorio calcula o **I de Moran** (vizinhanca dos 8 municipios mais
proximos) sobre o mapa de correlacoes. Ruido espacialmente independente produz I
proximo de zero; valores altos indicam que municipios vizinhos compartilham o
mesmo sinal, o que so acontece se houver processo fisico comum. Somado ao teste
do gradiente latitudinal, isso fornece evidencia de campo muito mais forte do que
a soma de testes pontuais.

## 6. Composicao por fase

Agrupam-se os meses em El Nino / La Nina / Neutro (pela fase do RONI naquele mes)
e reporta-se media, desvio-padrao e n de cada grupo para a anomalia climatica.
Da a resposta direta: "quanto, em media, chove a mais/menos em cada fase".

## 7. Camadas municipais (mapas)

Por municipio calcula-se: (a) a correlacao RONI x anomalia no lag otimo, para
precipitacao e temperatura — base do **mapa de teleconexao**; e (b) a anomalia
anual media de cada ano — base dos **mapas coropleticos anuais**. O mapa de
teleconexao e a leitura espacial central: mostra onde, dentro do Centro-Oeste, o
ENSO tem o vinculo mais forte com a chuva.

## 8. Comparacao oceano x atmosfera

Para cada UF, correlaciona-se a anomalia de precipitacao contra RONI, ONI e SOI
no respectivo lag otimo, e ordena-se por |r|. Como o SOI tem sinal invertido, a
comparacao usa o modulo. O resultado indica se o preditor mais forte da chuva
local e oceanico (RONI/ONI) ou atmosferico (SOI).

## 9. Dashboard

Todos os resultados sao serializados como JSON embutido em um unico `index.html`
autonomo (Leaflet + Chart.js via CDN, com degradacao graciosa se a CDN falhar).
Os placeholders do template sao preenchidos por substituicao literal de string
(nunca `str.format`), preservando as chaves de CSS/JS. Paleta divergente
daltonismo-safe (marrom-seco <-> teal-umido) para anomalias; a "regua RONI"
traduz o valor do indice em posicao e cor.

## Reprodutibilidade

Caches deterministicos (indices em CSV, clima em Parquet) permitem re-render
instantaneo sem refazer o download/extracao. O modo `--offline-demo` gera clima e
indices sinteticos (semente fixa) sobre a geometria real, reproduzindo a
teleconexao embutida — util para CI e para validar a montagem do dashboard sem
credenciais do GEE.
