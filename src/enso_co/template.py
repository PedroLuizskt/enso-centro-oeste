"""
Template do dashboard WebMap autonomo (index.html).

HTML + CSS + JavaScript embutidos. Placeholders {NOME} sao preenchidos por
enso_co.dashboard.render_html via str.replace (nao str.format), entao as
chaves de CSS/JS ficam intactas.
"""

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ENSO &middot; Centro-Oeste do Brasil &mdash; Monitor de Teleconexao</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }

:root {
  /* --- superficie --- */
  --bg:          #0a0e14;
  --bg-1:        #10151f;
  --bg-2:        #161d2b;
  --bg-3:        #1d2636;
  --border:      #232d40;
  --border-2:    #33405a;

  /* --- texto --- */
  --txt:         #e6ecf5;
  --txt-dim:     #8a99b3;
  --txt-mute:    #4f5d78;

  /* --- acento (ONI / destaque) --- */
  --amber:       #f0a202;
  --amber-dim:   #b57a00;

  /* --- paleta divergente daltonismo-safe (BrBG adaptado) --- */
  --dry-3:       #8c510a;   /* muito seco  */
  --dry-2:       #bf812d;
  --dry-1:       #dfc27d;
  --neutral:     #6b7794;
  --wet-1:       #80cdc1;
  --wet-2:       #35978f;
  --wet-3:       #01665e;   /* muito umido */

  /* --- fases ENSO --- */
  --el-nino:     #d1622b;   /* laranja-terra (quente) */
  --la-nina:     #2f9c95;   /* teal (frio)            */
  --neutro:      #6b7794;

  --font-head:   'Space Grotesk', sans-serif;
  --font-body:   'Inter', sans-serif;
}

body {
  font-family: var(--font-body);
  background: var(--bg);
  color: var(--txt);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

/* ============================ HEADER ============================ */
#header {
  background: linear-gradient(100deg, #080b11 0%, #10151f 55%, #0c1119 100%);
  border-bottom: 1px solid var(--border);
  height: 60px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 22px;
  flex-shrink: 0;
  z-index: 600;
  box-shadow: 0 1px 0 rgba(255,255,255,.02), 0 4px 20px rgba(0,0,0,.5);
}
.brand-mark {
  width: 30px; height: 30px;
  border-radius: 7px;
  background: radial-gradient(circle at 30% 30%, var(--amber), var(--el-nino) 70%);
  box-shadow: 0 0 18px rgba(240,162,2,.35);
  flex-shrink: 0;
  position: relative;
}
.brand-mark::after {
  content: ""; position: absolute; inset: 8px;
  border-radius: 50%;
  border: 2px solid rgba(10,14,20,.7);
}
.brand-txt h1 {
  font-family: var(--font-head);
  font-size: 16px; font-weight: 600; letter-spacing: .2px;
  color: #f4f7fc;
}
.brand-txt p {
  font-size: 10.5px; color: var(--txt-dim);
  letter-spacing: .2px; margin-top: 1px;
}
.header-right {
  margin-left: auto;
  display: flex; align-items: center; gap: 18px;
}
.oni-pill {
  display: flex; align-items: center; gap: 9px;
  background: var(--bg-2);
  border: 1px solid var(--border-2);
  border-radius: 999px;
  padding: 6px 14px 6px 10px;
}
.oni-pill .dot {
  width: 9px; height: 9px; border-radius: 50%;
  box-shadow: 0 0 8px currentColor;
}
.oni-pill .lbl { font-size: 10px; color: var(--txt-dim); letter-spacing:.3px; }
.oni-pill .val {
  font-family: var(--font-head); font-weight: 600; font-size: 14px;
}

/* ============================ LAYOUT ============================ */
#main { display: flex; flex: 1; overflow: hidden; }
#map  { flex: 1; position: relative; background: var(--bg-1); }

#panel {
  width: 452px; flex-shrink: 0;
  background: var(--bg-1);
  border-left: 1px solid var(--border);
  display: flex; flex-direction: column;
  overflow: hidden;
  box-shadow: -8px 0 30px rgba(0,0,0,.35);
}

/* ---- controles de topo do painel ---- */
#panel-controls {
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.control-row { display: flex; gap: 10px; }
.field { flex: 1; }
.field label {
  display: block;
  font-family: var(--font-head);
  font-size: 9.5px; font-weight: 500;
  text-transform: uppercase; letter-spacing: .8px;
  color: var(--txt-mute); margin-bottom: 5px;
}
select {
  width: 100%;
  background: var(--bg-3);
  border: 1px solid var(--border-2);
  color: var(--txt);
  padding: 8px 11px;
  border-radius: 7px;
  font-family: var(--font-body); font-size: 13px; font-weight: 500;
  cursor: pointer; outline: none;
  transition: border-color .15s;
}
select:focus { border-color: var(--amber); }
select:hover { border-color: var(--border-2); }

/* ---- regua ONI (assinatura) ---- */
#oni-ruler {
  margin-top: 12px;
  padding: 10px 2px 4px;
}
.ruler-track {
  position: relative; height: 8px; border-radius: 4px;
  background: linear-gradient(to right,
    var(--la-nina) 0%, #4a6a7a 30%, var(--neutro) 50%,
    #a06a4a 70%, var(--el-nino) 100%);
}
.ruler-mark {
  position: absolute; top: -4px;
  width: 3px; height: 16px; border-radius: 2px;
  background: #fff;
  box-shadow: 0 0 8px rgba(255,255,255,.6), 0 0 3px rgba(0,0,0,.8);
  transition: left .4s cubic-bezier(.4,0,.2,1);
}
.ruler-scale {
  display: flex; justify-content: space-between;
  font-size: 8.5px; color: var(--txt-mute);
  margin-top: 6px; font-family: var(--font-head);
}

/* ============================ TABS ============================ */
#tabs {
  display: flex; background: var(--bg);
  border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.tab {
  flex: 1; padding: 12px 4px; text-align: center;
  font-family: var(--font-head); font-size: 11px; font-weight: 500;
  letter-spacing: .6px; text-transform: uppercase;
  color: var(--txt-dim); cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color .15s, border-color .15s, background .15s;
}
.tab.active {
  color: var(--amber); border-bottom-color: var(--amber);
  background: rgba(240,162,2,.05);
}
.tab:hover:not(.active) { color: var(--txt); }

/* ============================ CONTENT ============================ */
.tab-content {
  flex: 1; overflow-y: auto; display: none;
  flex-direction: column; gap: 11px; padding: 14px 16px 22px;
}
.tab-content.active { display: flex; }
.tab-content::-webkit-scrollbar { width: 4px; }
.tab-content::-webkit-scrollbar-track { background: transparent; }
.tab-content::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 3px; }

.card {
  background: var(--bg-2);
  border: 1px solid var(--border);
  border-radius: 11px;
  padding: 15px;
  flex-shrink: 0;
}
.card h3 {
  font-family: var(--font-head);
  font-size: 10px; font-weight: 600;
  letter-spacing: .8px; text-transform: uppercase;
  color: var(--txt-dim); margin-bottom: 12px;
  display: flex; align-items: center; gap: 7px;
}
.card h3 .tag {
  margin-left: auto;
  font-size: 9px; font-weight: 500; letter-spacing: .3px;
  color: var(--txt-mute); text-transform: none;
}

/* ---- narrativa ---- */
.narrative {
  border-left: 3px solid var(--amber);
  background: rgba(240,162,2,.05);
  border-radius: 0 8px 8px 0;
  padding: 12px 14px;
  font-size: 12.5px; line-height: 1.6; color: #cdd6e6;
}
.narrative strong { color: var(--txt); font-weight: 600; }
.narrative.enso-nino { border-left-color: var(--el-nino); background: rgba(209,98,43,.06); }
.narrative.enso-nina { border-left-color: var(--la-nina); background: rgba(47,156,149,.06); }

/* ---- KPIs ---- */
.kpi-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }
.kpi {
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 9px; padding: 12px;
}
.kpi .v {
  font-family: var(--font-head); font-size: 23px; font-weight: 600;
  line-height: 1; letter-spacing: .3px;
}
.kpi .v.pos { color: var(--wet-2); }
.kpi .v.neg { color: var(--dry-2); }
.kpi .v.amber { color: var(--amber); }
.kpi .l { font-size: 10px; color: var(--txt-dim); margin-top: 6px; letter-spacing: .2px; }
.kpi .sub { font-size: 9px; color: var(--txt-mute); margin-top: 2px; }

/* ---- correlacao / lag ---- */
.corr-headline {
  display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px;
}
.corr-headline .r {
  font-family: var(--font-head); font-size: 34px; font-weight: 700; line-height: 1;
}
.corr-headline .meta { font-size: 11px; color: var(--txt-dim); line-height: 1.4; }
.corr-headline .meta b { color: var(--txt); font-weight: 600; }
.sig {
  display: inline-block; font-size: 9px; font-weight: 600;
  padding: 2px 7px; border-radius: 4px; letter-spacing: .4px;
  font-family: var(--font-head);
}
.sig.strong { background: rgba(47,156,149,.15); color: var(--wet-1); }
.sig.weak   { background: rgba(107,119,148,.15); color: var(--txt-dim); }

.lag-bars { display: flex; flex-direction: column; gap: 5px; margin-top: 4px; }
.lag-bar {
  display: grid; grid-template-columns: 42px 1fr 46px;
  align-items: center; gap: 8px; font-size: 10.5px;
}
.lag-bar .lg { color: var(--txt-dim); font-family: var(--font-head); }
.lag-bar .track { position: relative; height: 6px; background: var(--bg); border-radius: 3px; overflow: hidden; }
.lag-bar .fill { position: absolute; top: 0; height: 100%; border-radius: 3px; }
.lag-bar .rv { text-align: right; font-family: var(--font-head); font-weight: 500; color: var(--txt); }
.lag-bar.best .track { box-shadow: 0 0 0 1px var(--amber); }
.lag-bar.best .lg { color: var(--amber); }

/* ---- composicao ---- */
.comp-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
.comp {
  border: 1px solid var(--border); border-radius: 9px;
  padding: 11px 8px; text-align: center; background: var(--bg);
}
.comp .ph {
  font-family: var(--font-head); font-size: 10px; font-weight: 600;
  letter-spacing: .3px; margin-bottom: 7px;
}
.comp.nino .ph { color: var(--el-nino); }
.comp.nina .ph { color: var(--la-nina); }
.comp.neutro .ph { color: var(--txt-dim); }
.comp .cv { font-family: var(--font-head); font-size: 18px; font-weight: 600; }
.comp .cu { font-size: 9px; color: var(--txt-mute); margin-top: 3px; }
.comp .cn { font-size: 8.5px; color: var(--txt-mute); margin-top: 4px; }

/* ---- charts ---- */
.chart-box { position: relative; }
.h-200 { height: 200px; }
.h-230 { height: 230px; }
.h-250 { height: 250px; }

/* ---- var toggle ---- */
.var-toggle { display: flex; gap: 6px; }
.var-toggle button {
  flex: 1; padding: 7px; border-radius: 7px;
  background: var(--bg-3); border: 1px solid var(--border-2);
  color: var(--txt-dim); font-family: var(--font-head);
  font-size: 11px; font-weight: 500; cursor: pointer;
  transition: all .15s;
}
.var-toggle button.active {
  background: rgba(240,162,2,.12); border-color: var(--amber); color: var(--amber);
}

/* ============================ MAP OVERLAYS ============================ */
#legend {
  position: absolute; bottom: 22px; left: 16px; z-index: 700;
  background: rgba(10,14,20,.92);
  border: 1px solid var(--border-2); border-radius: 11px;
  padding: 13px 15px; min-width: 190px;
  backdrop-filter: blur(8px);
  box-shadow: 0 6px 24px rgba(0,0,0,.5);
}
#legend h5 {
  font-family: var(--font-head); font-size: 9.5px; font-weight: 600;
  letter-spacing: .7px; text-transform: uppercase;
  color: var(--txt-dim); margin-bottom: 9px;
}
.leg-bar { height: 11px; border-radius: 6px; }
.leg-bar.precip { background: linear-gradient(to right,
  var(--dry-3), var(--dry-1), var(--neutral), var(--wet-1), var(--wet-3)); }
.leg-bar.temp { background: linear-gradient(to right,
  #2166ac, #92c5de, #f7f7f7, #f4a582, #b2182b); }
.leg-labels { display: flex; justify-content: space-between; font-size: 9.5px;
  color: var(--txt-dim); margin-top: 5px; font-family: var(--font-head); }

#map-mode {
  position: absolute; top: 14px; left: 16px; z-index: 700;
  display: flex; gap: 6px;
  background: rgba(10,14,20,.9); border: 1px solid var(--border-2);
  border-radius: 9px; padding: 5px; backdrop-filter: blur(8px);
}
#map-mode button {
  padding: 6px 12px; border: none; background: transparent;
  color: var(--txt-dim); font-family: var(--font-head);
  font-size: 11px; font-weight: 500; border-radius: 6px; cursor: pointer;
  transition: all .15s;
}
#map-mode button.active { background: var(--bg-3); color: var(--amber); }

.leaflet-tooltip.enso-tip {
  background: #0c1119 !important;
  border: 1px solid var(--border-2) !important;
  color: var(--txt) !important;
  font-family: var(--font-body) !important;
  border-radius: 8px !important;
  padding: 9px 12px !important;
  box-shadow: 0 4px 16px rgba(0,0,0,.6) !important;
}
.leaflet-tooltip.enso-tip::before { display: none; }

/* ============================ LOADING ============================ */
#loading {
  position: fixed; inset: 0; background: var(--bg);
  display: flex; align-items: center; justify-content: center;
  flex-direction: column; gap: 16px; z-index: 9999;
}
.spinner {
  width: 40px; height: 40px; border-radius: 50%;
  border: 3px solid var(--border);
  border-top-color: var(--amber);
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
#loading p { font-size: 12.5px; color: var(--txt-dim); letter-spacing: .3px; }

/* ============================ FOOTER NOTE ============================ */
.src-note {
  font-size: 9.5px; color: var(--txt-mute); line-height: 1.5;
  padding: 2px 2px 4px; text-align: center;
}
.src-note a { color: var(--txt-dim); text-decoration: none; }
.src-note a:hover { color: var(--amber); }

/* ============================ RESPONSIVE ============================ */
@media (max-width: 900px) {
  #main { flex-direction: column; }
  #panel { width: 100%; border-left: none; border-top: 1px solid var(--border); }
  #map { min-height: 42vh; }
}
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}

/* ---- comparacao multi-indice (oceano x atmosfera) ---- */
.idx-rows { display:flex; flex-direction:column; gap:7px; margin-top:2px; }
.idx-row { display:grid; grid-template-columns:52px 1fr 52px; align-items:center; gap:9px; }
.idx-row .nm { font-family:var(--font-head); font-size:11px; font-weight:600; color:var(--txt); }
.idx-row .nm small { display:block; font-weight:400; font-size:8px; color:var(--txt-mute); letter-spacing:.3px; }
.idx-row .track { position:relative; height:14px; background:var(--bg); border-radius:4px; overflow:hidden; }
.idx-row .fill { position:absolute; left:0; top:0; height:100%; border-radius:4px; }
.idx-row .rv { text-align:right; font-family:var(--font-head); font-weight:600; font-size:12px; color:var(--txt); }
.idx-row.win .track { box-shadow:0 0 0 1px var(--amber); }
.idx-row .badge { display:inline-block; font-size:7.5px; padding:1px 4px; border-radius:3px; margin-left:5px;
  letter-spacing:.3px; vertical-align:middle; }
.badge.oce { background:rgba(47,156,149,.18); color:var(--wet-1); }
.badge.atm { background:rgba(240,162,2,.15); color:var(--amber); }
.idx-note { font-size:10.5px; color:var(--txt-dim); line-height:1.5; margin-top:11px;
  padding-top:10px; border-top:1px solid var(--border); }
.idx-note b { color:var(--txt); }

/* ---- legenda de correlacao (mapa teleconexao) ---- */
.leg-bar.corr { background:linear-gradient(to right,
  var(--wet-3), var(--wet-1), var(--neutral), var(--dry-1), var(--dry-3)); }

/* ---- readout de municipio selecionado ---- */
.muni-readout { font-size:11px; color:var(--txt-dim); line-height:1.5;
  background:var(--bg); border:1px solid var(--border); border-radius:8px;
  padding:10px 12px; margin-top:10px; display:none; }
.muni-readout.show { display:block; }
.muni-readout b { color:var(--txt); font-weight:600; }
.muni-readout .r { font-family:var(--font-head); font-weight:600; }

</style></head>
<body>

<div id="loading">
  <div class="spinner"></div>
  <p>Carregando series ENSO e climaticas...</p>
</div>

<div id="header">
  <div class="brand-mark"></div>
  <div class="brand-txt">
    <h1>ENSO &middot; Centro-Oeste</h1>
    <p>Teleconexao El Nino / La Nina &middot; {START_YEAR}&ndash;{END_YEAR} &middot; CHIRPS + ERA5-Land &middot; RONI / ONI / SOI (NOAA/CPC)</p>
  </div>
  <div class="header-right">
    <div class="oni-pill">
      <span class="dot" id="hdr-dot"></span>
      <div><div class="lbl" id="hdr-lbl">{INDEX_PRIMARY} &middot; {MES_ULTIMO}</div></div>
      <span class="val" id="hdr-oni">{ONI_ULTIMO}</span>
    </div>
  </div>
</div>

<div id="main">
  <div id="map">
    <div id="map-mode">
      <button id="mode-precip" class="active" onclick="setMapMode('precip')">Precip.</button>
      <button id="mode-temp" onclick="setMapMode('temp')">Temp.</button>
      <button id="mode-corr" onclick="setMapMode('corr')">Teleconexao</button>
    </div>
    <div id="legend">
      <h5 id="leg-title">Anomalia de precipitacao (mm)</h5>
      <div class="leg-bar precip" id="leg-bar"></div>
      <div class="leg-labels"><span id="leg-min">&mdash;</span><span id="leg-max">&mdash;</span></div>
    </div>
  </div>

  <div id="panel">
    <div id="panel-controls">
      <div class="control-row">
        <div class="field">
          <label>Estado</label>
          <select id="uf-select" onchange="onUfChange(this.value)">{UF_OPTIONS}</select>
        </div>
        <div class="field">
          <label>Ano (mapa)</label>
          <select id="year-select" onchange="onYearChange(this.value)">{YEAR_OPTIONS}</select>
        </div>
      </div>
      <div class="control-row" style="margin-top:9px">
        <div class="field">
          <label>Municipio (foco)</label>
          <select id="muni-select" onchange="onMuniChange(this.value)"></select>
        </div>
      </div>
      <div class="muni-readout" id="muni-readout"></div>
      <div id="oni-ruler">
        <div class="ruler-track"><div class="ruler-mark" id="ruler-mark"></div></div>
        <div class="ruler-scale">
          <span>-2 La Nina</span><span>-1</span><span>0</span><span>+1</span><span>+2 El Nino</span>
        </div>
      </div>
    </div>

    <div id="tabs">
      <div class="tab active" onclick="switchTab('series')">Serie Temporal</div>
      <div class="tab" onclick="switchTab('corr')">Correlacao</div>
      <div class="tab" onclick="switchTab('comp')">Composicao</div>
    </div>

    <!-- ===================== SERIE TEMPORAL ===================== -->
    <div id="tab-series" class="tab-content active">
      <div id="series-narrative" class="narrative">&nbsp;</div>
      <div class="card">
        <h3>Variavel <span class="tag" id="series-var-tag">anomalia de precipitacao</span></h3>
        <div class="var-toggle" style="margin-bottom:11px">
          <button id="sv-precip" class="active" onclick="setSeriesVar('precip')">Precipitacao</button>
          <button id="sv-temp" onclick="setSeriesVar('temp')">Temperatura</button>
        </div>
        <div class="var-toggle" style="margin-bottom:13px">
          <button id="sl-RONI" class="active" onclick="setSeriesIdx('RONI')">RONI</button>
          <button id="sl-ONI" onclick="setSeriesIdx('ONI')">ONI</button>
          <button id="sl-SOI" onclick="setSeriesIdx('SOI')">SOI</button>
        </div>
        <div class="chart-box h-250"><canvas id="chart-series"></canvas></div>
      </div>
      <div class="card">
        <h3>Leitura rapida</h3>
        <div class="kpi-grid" id="series-kpis"></div>
      </div>
    </div>

    <!-- ===================== CORRELACAO ===================== -->
    <div id="tab-corr" class="tab-content">
      <div class="card">
        <h3>Correlacao {INDEX_PRIMARY} &times; clima <span class="tag" id="corr-var-tag">precipitacao</span></h3>
        <div class="var-toggle" style="margin-bottom:14px">
          <button id="cv-precip" class="active" onclick="setCorrVar('precip')">Precipitacao</button>
          <button id="cv-temp" onclick="setCorrVar('temp')">Temperatura</button>
        </div>
        <div class="corr-headline" id="corr-headline"></div>
        <div class="lag-bars" id="lag-bars"></div>
      </div>

      <div class="card">
        <h3>Oceano &times; atmosfera <span class="tag">qual indice prevê a chuva?</span></h3>
        <div class="idx-rows" id="idx-rows"></div>
        <div class="idx-note" id="idx-note"></div>
      </div>

      <div class="card">
        <h3>Dispersao no lag otimo <span class="tag" id="scatter-lag-tag">&mdash;</span></h3>
        <div class="chart-box h-250"><canvas id="chart-scatter"></canvas></div>
      </div>
    </div>

    <!-- ===================== COMPOSICAO ===================== -->
    <div id="tab-comp" class="tab-content">
      <div class="card">
        <h3>Composicao por fase <span class="tag" id="comp-var-tag">precipitacao</span></h3>
        <div class="var-toggle" style="margin-bottom:14px">
          <button id="pv-precip" class="active" onclick="setCompVar('precip')">Precipitacao</button>
          <button id="pv-temp" onclick="setCompVar('temp')">Temperatura</button>
        </div>
        <div class="comp-grid" id="comp-grid"></div>
      </div>
      <div class="card">
        <h3>Anomalia media por fase</h3>
        <div class="chart-box h-230"><canvas id="chart-comp"></canvas></div>
      </div>
      <div class="card">
        <h3 id="event-title">Eventos de referencia</h3>
        <div class="narrative enso-nino" id="event-narrative">&nbsp;</div>
      </div>
    </div>

    <div class="src-note">
      Fontes: precip. <a href="https://www.chc.ucsb.edu/data/chirps" target="_blank" rel="noopener">CHIRPS/UCSB</a>,
      temp. <a href="https://www.ecmwf.int" target="_blank" rel="noopener">ERA5-Land/ECMWF</a>,
      indices <a href="https://www.cpc.ncep.noaa.gov/data/indices/" target="_blank" rel="noopener">NOAA/CPC</a>
      (RONI, ONI, SOI).<br>
      Extracao via Google Earth Engine &middot; gerado em {DATA_HOJE}
    </div>
  </div>
</div>

<script>
const ANALYSIS   = {ANALYSIS_JS};
const MUNI       = {MUNI_JS};
const MULTI      = {MULTI_JS};
const INDICES    = {INDICES_JS};
const GEOJSON    = {GEOJSON_JS};
const UF_NOME    = {UF_NOME_JS};
const ESTADOS    = {ESTADOS_JS};
const ANOS       = {ANOS_JS};
const MUNI_BY_UF = {MUNI_BY_UF_JS};
const EVENTO_EL_NINO = "{EVENTO_EL_NINO}";
const EVENTO_LA_NINA = "{EVENTO_LA_NINA}";
const CENTER     = [{CENTER_LAT}, {CENTER_LON}];
const PRIMARY    = "{INDEX_PRIMARY}";
const SEASON     = "{SEASON}";
const STANDARDIZED = {STANDARDIZED};

{JS_LOGIC}
</script>
</body>
</html>'''

JS_LOGIC = r'''
/* ==================== ESTADO GLOBAL ==================== */
let map, geoLayer, muniHighlight = null;
let currentUf   = ESTADOS[0];
let currentYear = ANOS[ANOS.length - 1];
let currentMuni = "";           // cd_mun em foco ("" = todos)
let mapMode     = 'precip';     // precip | temp | corr
let seriesVar   = 'precip';
let seriesIdx   = 'RONI';
let corrVar     = 'precip';
let compVar     = 'precip';
let chartSeries = null, chartScatter = null, chartComp = null;

/* ==================== PALETAS (daltonismo-safe) ==================== */
const PRECIP_STOPS = [[0,[140,81,10]],[0.25,[223,194,125]],[0.5,[107,119,148]],[0.75,[128,205,193]],[1,[1,102,94]]];
const TEMP_STOPS   = [[0,[33,102,172]],[0.25,[146,197,222]],[0.5,[240,240,240]],[0.75,[244,165,130]],[1,[178,24,43]]];
function lerp(stops,t){t=Math.max(0,Math.min(1,t));let lo=stops[0],hi=stops[stops.length-1];
  for(let i=0;i<stops.length-1;i++){if(t>=stops[i][0]&&t<=stops[i+1][0]){lo=stops[i];hi=stops[i+1];break;}}
  const f=hi[0]===lo[0]?0:(t-lo[0])/(hi[0]-lo[0]);
  const c=[0,1,2].map(k=>Math.round(lo[1][k]+f*(hi[1][k]-lo[1][k])));return `rgb(${c[0]},${c[1]},${c[2]})`;}

/* ==================== INDICE PRIMARIO (RONI) ==================== */
const RONI = INDICES[PRIMARY];
function roniAt(ym){const i=RONI.dates.indexOf(ym);return i>=0?RONI.value[i]:null;}
function phaseColorVar(v){if(v==null)return 'var(--neutro)';if(v>=0.5)return 'var(--el-nino)';if(v<=-0.5)return 'var(--la-nina)';return 'var(--neutro)';}
function phaseLabel(v){if(v==null)return 'Sem dado';
  if(v>=2)return 'El Nino Muito Forte';if(v>=1.5)return 'El Nino Forte';if(v>=1)return 'El Nino Moderado';if(v>=0.5)return 'El Nino Fraco';
  if(v<=-1.5)return 'La Nina Forte';if(v<=-1)return 'La Nina Moderada';if(v<=-0.5)return 'La Nina Fraca';return 'Neutro';}
function roniYearMean(year){const vs=RONI.dates.map((d,i)=>({y:d.slice(0,4),v:RONI.value[i]}))
  .filter(o=>o.y===String(year)&&o.v!=null).map(o=>o.v);
  return vs.length?vs.reduce((a,b)=>a+b,0)/vs.length:null;}

/* ==================== MAPA ==================== */
function initMap(){
  map=L.map('map',{center:CENTER,zoom:5,zoomControl:true,preferCanvas:true});
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    {attribution:'&copy; OpenStreetMap &copy; CARTO',opacity:.9,maxZoom:12}).addTo(map);
  map.attributionControl.setPrefix('');
  buildGeoLayer();
  try{map.fitBounds(geoLayer.getBounds().pad(0.06));}catch(e){}
}
function muniVal(cd){
  const m=MUNI[cd]; if(!m)return null;
  if(mapMode==='corr') return m.r_precip;
  const a=(m.annual||{})[String(currentYear)];
  if(!a)return null;
  return mapMode==='precip'?a.precip_anom:a.temp_anom;
}
function modeRange(){
  if(mapMode==='corr'){
    let mx=0.4; for(const cd in MUNI){const r=MUNI[cd].r_precip; if(r!=null)mx=Math.max(mx,Math.abs(r));}
    return {min:-mx,max:mx,sym:true};
  }
  const vals=Object.keys(MUNI).map(muniVal).filter(x=>x!=null&&!isNaN(x));
  if(!vals.length)return {min:-1,max:1,sym:true};
  const mx=Math.max(Math.abs(Math.min(...vals)),Math.abs(Math.max(...vals)))||1;
  return {min:-mx,max:mx,sym:true};
}
function fillFor(cd){
  const v=muniVal(cd); if(v==null||isNaN(v))return '#161d2b';
  const r=modeRange(); const t=(v-r.min)/((r.max-r.min)||1);
  return lerp(mapMode==='temp'?TEMP_STOPS:PRECIP_STOPS,t);
}
function styleFeature(f){
  const p=f.properties; const inUf=p.uf===currentUf; const isFocus=p.cd===currentMuni;
  let op = inUf?0.9:0.5;
  // No mapa de teleconexao, municipios sem significancia estatistica ficam
  // esmaecidos: o sinal existe no numero, mas nao se distingue do acaso.
  if(mapMode==='corr'){ const m=MUNI[p.cd]; if(m && m.sig_precip===false) op = inUf?0.28:0.15; }
  return {fillColor:fillFor(p.cd), fillOpacity:op,
    color:isFocus?'#fff':(inUf?'#f0a202':'#33405a'),
    weight:isFocus?2.5:(inUf?1.1:0.5), opacity:inUf?1:0.65};
}
function tipHtml(p){
  const m=MUNI[p.cd]||{}; const a=(m.annual||{})[String(currentYear)]||{};
  let body;
  if(mapMode==='corr'){
    const r=m.r_precip; const lg=m.lag_precip;
    const sg=m.sig_precip, pv=m.p_precip;
    body=`<div style="font-size:11.5px;color:#8a99b3">Correl. ${PRIMARY}&times;chuva: <b class="rv" style="color:${r!=null&&r<0?'#dfc27d':'#80cdc1'}">${r!=null?(r>=0?'+':'')+r.toFixed(2):'—'}</b></div>
          <div style="font-size:10.5px;color:#4f5d78">lag otimo ${lg!=null?lg+'m':'—'} &middot; p ${pv!=null?pv.toFixed(3):'—'}</div>
          <div style="font-size:10px;margin-top:3px;color:${sg?'#80cdc1':'#6b7794'}">${sg?'significativo (p<0.05)':'nao significativo'}</div>`;
  }else{
    body=`<div style="font-size:11.5px;color:#8a99b3">An. chuva ${currentYear}: <b style="color:#80cdc1">${a.precip_anom!=null?(a.precip_anom>=0?'+':'')+a.precip_anom+' mm':'—'}</b></div>
          <div style="font-size:11.5px;color:#8a99b3">An. temp ${currentYear}: <b style="color:#f4a582">${a.temp_anom!=null?(a.temp_anom>=0?'+':'')+a.temp_anom+' °C':'—'}</b></div>`;
  }
  return `<div style="min-width:160px"><div style="font-family:'Space Grotesk';font-weight:600;font-size:13px;color:#f4f7fc;margin-bottom:4px">${p.nm} <span style="color:#4f5d78;font-weight:400">${p.uf}</span></div>${body}</div>`;
}
function buildGeoLayer(){
  geoLayer=L.geoJSON(GEOJSON,{style:styleFeature,onEachFeature:(f,layer)=>{
    const p=f.properties;
    layer.on('mouseover',e=>{layer.setStyle({weight:2,color:'#fff'});
      layer.bindTooltip(tipHtml(p),{className:'enso-tip',sticky:true}).openTooltip(e.latlng);});
    layer.on('mouseout',()=>{geoLayer.resetStyle(layer);styleFocus();layer.closeTooltip();});
    layer.on('click',()=>{document.getElementById('uf-select').value=p.uf;onUfChange(p.uf);
      document.getElementById('muni-select').value=p.cd;onMuniChange(p.cd);});
  }}).addTo(map);
}
function styleFocus(){ if(!geoLayer)return;
  geoLayer.eachLayer(l=>{ if(l.feature.properties.cd===currentMuni) l.setStyle({color:'#fff',weight:2.5}); }); }
function refreshMap(){ if(!geoLayer)return; geoLayer.eachLayer(l=>l.setStyle(styleFeature(l.feature))); updateLegend(); }

function updateLegend(){
  const r=modeRange();
  const t=document.getElementById('leg-title'), bar=document.getElementById('leg-bar');
  const lo=document.getElementById('leg-min'), hi=document.getElementById('leg-max');
  if(mapMode==='corr'){
    t.innerHTML=`Teleconexao ${PRIMARY}\u00d7chuva (r) &middot; ${SEASON}
      <span style="display:block;font-size:8.5px;color:#4f5d78;letter-spacing:.2px;
      text-transform:none;margin-top:2px">esmaecido = nao significativo (p &ge; 0.05)</span>`;
    bar.className='leg-bar precip';
    lo.textContent=r.min.toFixed(1)+' (El Nino seca)'; hi.textContent='+'+r.max.toFixed(1);
  }else if(mapMode==='temp'){
    t.textContent=`Anomalia de temperatura (°C) · ${currentYear}`; bar.className='leg-bar temp';
    lo.textContent=r.min.toFixed(1); hi.textContent='+'+r.max.toFixed(1);
  }else{
    t.textContent=`Anomalia de precipitacao (mm) · ${currentYear}`; bar.className='leg-bar precip';
    lo.textContent=r.min.toFixed(0); hi.textContent='+'+r.max.toFixed(0);
  }
  document.getElementById('year-select').disabled = (mapMode==='corr');
  document.getElementById('year-select').style.opacity = mapMode==='corr'?0.45:1;
}

/* ==================== MUNICIPIO (drill-down) ==================== */
function populateMuni(){
  const sel=document.getElementById('muni-select');
  const list=MUNI_BY_UF[currentUf]||[];
  sel.innerHTML='<option value="">(todos os municipios)</option>'+
    list.map(m=>`<option value="${m.cd}">${m.nm}</option>`).join('');
  sel.value=''; currentMuni='';
  document.getElementById('muni-readout').classList.remove('show');
}
function onMuniChange(cd){
  currentMuni=cd; refreshMap(); styleFocus();
  const ro=document.getElementById('muni-readout');
  if(!cd){ro.classList.remove('show');return;}
  const m=MUNI[cd]; if(!m)return;
  const rp=m.r_precip, rt=m.r_temp;
  ro.classList.add('show');
  ro.innerHTML=`<b>${m.nm}</b> (${m.uf}) &mdash; correlacao ${PRIMARY} no lag otimo:<br>
    chuva <b class="r" style="color:${rp!=null&&rp<0?'#dfc27d':'#80cdc1'}">${rp!=null?(rp>=0?'+':'')+rp.toFixed(2):'—'}</b> (lag ${m.lag_precip}m,
    p ${m.p_precip!=null?m.p_precip.toFixed(3):'—'} <span style="color:${m.sig_precip?'#80cdc1':'#6b7794'}">${m.sig_precip?'sig.':'n.s.'}</span>) &middot;
    temp <b class="r" style="color:#f4a582">${rt!=null?(rt>=0?'+':'')+rt.toFixed(2):'—'}</b> (lag ${m.lag_temp}m)`;
  // zoom no municipio
  geoLayer.eachLayer(l=>{ if(l.feature.properties.cd===cd){ try{map.fitBounds(l.getBounds().pad(0.6));}catch(e){} } });
}

/* ==================== REGUA + HEADER (RONI) ==================== */
function updateRuler(v){
  const mark=document.getElementById('ruler-mark');
  const cl=Math.max(-2.5,Math.min(2.5,v==null?0:v)); mark.style.left=`calc(${((cl+2.5)/5)*100}% - 1.5px)`;
  const col=getComputedStyle(document.documentElement).getPropertyValue(v==null?'--neutro':(v>=0.5?'--el-nino':(v<=-0.5?'--la-nina':'--neutro'))).trim();
  document.getElementById('hdr-dot').style.color=col;
  const h=document.getElementById('hdr-oni'); h.style.color=col;
  h.textContent=v==null?'—':(v>=0?`+${v.toFixed(2)}`:v.toFixed(2));
  document.getElementById('hdr-lbl').textContent=`${PRIMARY} medio ${currentYear} · ${phaseLabel(v)}`;
}

/* ==================== TABS + HANDLERS ==================== */
function switchTab(tab){['series','corr','comp'].forEach((t,i)=>{
  document.querySelectorAll('.tab')[i].classList.toggle('active',t===tab);
  document.getElementById('tab-'+t).classList.toggle('active',t===tab);});
  if(tab==='series')renderSeries(); if(tab==='corr'){renderCorr();renderMulti();} if(tab==='comp')renderComp();}
function onUfChange(uf){currentUf=uf; populateMuni(); refreshMap();
  renderSeries();renderCorr();renderMulti();renderComp();}
function onYearChange(y){currentYear=y; refreshMap(); updateRuler(roniYearMean(y));}
function setMapMode(m){mapMode=m;
  ['precip','temp','corr'].forEach(k=>document.getElementById('mode-'+k).classList.toggle('active',k===m));
  refreshMap();}
function setSeriesVar(v){seriesVar=v; renderSeries();}
function setSeriesIdx(v){seriesIdx=v; renderSeries();}
function setCorrVar(v){corrVar=v; renderCorr();}
function setCompVar(v){compVar=v; renderComp();}

/* ==================== CHART BASE ==================== */
const GRID='#232d40',TICK='#8a99b3',FONT="'Inter', sans-serif";
function baseOpts(x){return Object.assign({responsive:true,maintainAspectRatio:false,
  animation:{duration:350},interaction:{intersect:false,mode:'index'}},x);}
function tt(){return {backgroundColor:'#0c1119',titleColor:'#e6ecf5',bodyColor:'#8a99b3',
  borderColor:'#33405a',borderWidth:1,padding:10,cornerRadius:7,titleFont:{family:"'Space Grotesk'"}};}
function zeroLine(id){return {}; }

/* ==================== SERIE TEMPORAL ==================== */
function renderSeries(){
  const blk=ANALYSIS[currentUf]; if(!blk)return;
  const ts=blk.timeseries; const varKey=seriesVar==='precip'?'precip_anom':'temp_anom';
  const unit=seriesVar==='precip'?'mm':'°C'; const anomColor=seriesVar==='precip'?'#35978f':'#f4a582';
  document.getElementById('series-var-tag').textContent=seriesVar==='precip'?'anomalia de precipitacao':'anomalia de temperatura';
  document.getElementById('sv-precip').classList.toggle('active',seriesVar==='precip');
  document.getElementById('sv-temp').classList.toggle('active',seriesVar==='temp');
  ['RONI','ONI','SOI'].forEach(k=>document.getElementById('sl-'+k).classList.toggle('active',seriesIdx===k));

  const c=blk[seriesVar].correlation.best;
  const nEl=document.getElementById('series-narrative'); nEl.className='narrative';
  const dir=c.pearson_r<0?'reduzir':'elevar';
  nEl.innerHTML=`<strong>${UF_NOME[currentUf]}</strong> &mdash; o ${PRIMARY} antecede a
    ${seriesVar==='precip'?'precipitacao':'temperatura'} local em <strong>${c.lag} ${c.lag===1?'mes':'meses'}</strong>,
    com correlacao de <strong>${c.pearson_r>=0?'+':''}${c.pearson_r}</strong>. Fases quentes (El Nino) tendem a
    ${dir} o sinal climatico com essa defasagem.`;

  const bars=ts[varKey].map(v=>v==null?0:v);
  const barColors=bars.map(v=>v>=0?anomColor:(seriesVar==='precip'?'#bf812d':'#4a90d9'));
  // linha do indice escolhido, alinhada as datas da serie da UF
  const idx=INDICES[seriesIdx]; const idxMap={}; idx.dates.forEach((d,i)=>idxMap[d]=idx.value[i]);
  const line=ts.dates.map(d=>idxMap[d]!=null?idxMap[d]:null);
  const idxColor=seriesIdx==='SOI'?'#9b8cff':'#f0a202';

  const ctx=document.getElementById('chart-series').getContext('2d');
  if(chartSeries)chartSeries.destroy();
  chartSeries=new Chart(ctx,{data:{labels:ts.dates,datasets:[
    {type:'bar',label:`Anomalia (${unit})`,data:bars,yAxisID:'y',backgroundColor:barColors,borderWidth:0,order:2,categoryPercentage:1,barPercentage:1},
    {type:'line',label:seriesIdx,data:line,yAxisID:'y1',borderColor:idxColor,borderWidth:1.8,pointRadius:0,tension:.35,order:1,spanGaps:true}
  ]},options:baseOpts({plugins:{legend:{labels:{color:TICK,font:{family:FONT,size:10},boxWidth:12,boxHeight:2}},tooltip:tt()},
    scales:{x:{ticks:{color:'#4f5d78',font:{size:8},maxTicksLimit:10},grid:{color:GRID}},
      y:{position:'left',ticks:{color:TICK,font:{size:9}},grid:{color:GRID},title:{display:true,text:`Anomalia (${unit})`,color:'#4f5d78',font:{size:9}}},
      y1:{position:'right',ticks:{color:idxColor,font:{size:9}},grid:{display:false},title:{display:true,text:seriesIdx,color:idxColor,font:{size:9}},min:-3.2,max:3.2}}})});

  const comp=blk[seriesVar].composite;
  const dEl=comp['El Nino'].mean.toFixed(seriesVar==='precip'?0:2), dLa=comp['La Nina'].mean.toFixed(seriesVar==='precip'?0:2);
  document.getElementById('series-kpis').innerHTML=`
    <div class="kpi"><div class="v amber">${c.pearson_r>=0?'+':''}${c.pearson_r}</div><div class="l">Correlacao (lag ${c.lag}m)</div><div class="sub">Pearson · ${PRIMARY}</div></div>
    <div class="kpi"><div class="v">${c.n}</div><div class="l">Meses analisados</div><div class="sub">${RONI.dates[0]} – ${RONI.dates[RONI.dates.length-1]}</div></div>
    <div class="kpi"><div class="v neg">${dEl>=0?'+':''}${dEl}</div><div class="l">Anomalia media El Nino</div><div class="sub">${unit}</div></div>
    <div class="kpi"><div class="v pos">${dLa>=0?'+':''}${dLa}</div><div class="l">Anomalia media La Nina</div><div class="sub">${unit}</div></div>`;
}

/* ==================== CORRELACAO ==================== */
function renderCorr(){
  const blk=ANALYSIS[currentUf]; if(!blk)return; const data=blk[corrVar]; const unit=corrVar==='precip'?'mm':'°C';
  document.getElementById('corr-var-tag').textContent=corrVar==='precip'?'precipitacao':'temperatura';
  document.getElementById('cv-precip').classList.toggle('active',corrVar==='precip');
  document.getElementById('cv-temp').classList.toggle('active',corrVar==='temp');
  const best=data.correlation.best; const strong=Math.abs(best.pearson_r)>=0.3;
  const rColor=best.pearson_r<0?'var(--dry-2)':'var(--wet-2)';
  document.getElementById('corr-headline').innerHTML=`
    <div class="r" style="color:${rColor}">${best.pearson_r>=0?'+':''}${best.pearson_r}</div>
    <div class="meta">Pearson no lag otimo de <b>${best.lag} ${best.lag===1?'mes':'meses'}</b><br>
      Spearman <b>${best.spearman_r>=0?'+':''}${best.spearman_r}</b> &middot; p ${best.pearson_p<0.001?'< 0.001':'= '+best.pearson_p}<br>
      <span class="sig ${strong?'strong':'weak'}">${strong?'sinal relevante':'sinal fraco'}</span></div>`;
  const lags=data.correlation.per_lag; const maxAbs=Math.max(...lags.map(l=>Math.abs(l.pearson_r)),0.1);
  document.getElementById('lag-bars').innerHTML=lags.map(l=>{const w=(Math.abs(l.pearson_r)/maxAbs)*100;
    const col=l.pearson_r<0?'#bf812d':'#35978f';
    return `<div class="lag-bar ${l.lag===best.lag?'best':''}"><span class="lg">${l.lag}m</span>
      <div class="track"><div class="fill" style="width:${w}%;background:${col};${l.pearson_r<0?'right:50%':'left:50%'}"></div></div>
      <span class="rv">${l.pearson_r>=0?'+':''}${l.pearson_r}</span></div>`;}).join('');
  document.getElementById('scatter-lag-tag').textContent=`lag ${best.lag}m · ${unit}`;
  const sc=data.scatter; const line=[{x:sc.x_min,y:sc.slope*sc.x_min+sc.intercept},{x:sc.x_max,y:sc.slope*sc.x_max+sc.intercept}];
  const ptColor=sc.points.map(p=>p.x>=0.5?'rgba(209,98,43,.6)':(p.x<=-0.5?'rgba(47,156,149,.6)':'rgba(107,119,148,.5)'));
  const ctx=document.getElementById('chart-scatter').getContext('2d'); if(chartScatter)chartScatter.destroy();
  chartScatter=new Chart(ctx,{data:{datasets:[
    {type:'scatter',label:'Meses',data:sc.points,pointRadius:3.5,pointBackgroundColor:ptColor,pointBorderWidth:0},
    {type:'line',label:'Tendencia (OLS)',data:line,borderColor:'#f0a202',borderWidth:2,pointRadius:0,borderDash:[6,3]}]},
    options:baseOpts({plugins:{legend:{labels:{color:TICK,font:{family:FONT,size:10},boxWidth:12}},tooltip:tt()},
      scales:{x:{title:{display:true,text:`${PRIMARY} (defasado ${best.lag}m)`,color:'#4f5d78',font:{size:9}},ticks:{color:TICK,font:{size:9}},grid:{color:GRID}},
        y:{title:{display:true,text:`Anomalia (${unit})`,color:'#4f5d78',font:{size:9}},ticks:{color:TICK,font:{size:9}},grid:{color:GRID}}}})});
}

/* ==================== OCEANO x ATMOSFERA ==================== */
function renderMulti(){
  const rows=MULTI[currentUf]||[]; const box=document.getElementById('idx-rows');
  if(!rows.length){box.innerHTML='<div style="color:#4f5d78;font-size:11px">Sem dados suficientes.</div>';
    document.getElementById('idx-note').innerHTML=''; return;}
  const maxAbs=Math.max(...rows.map(r=>r.abs_r),0.1);
  box.innerHTML=rows.map((r,i)=>{const w=(r.abs_r/maxAbs)*100;
    const col=r.kind==='atmosferico'?'#f0a202':'#35978f';
    const badge=r.kind==='atmosferico'?'<span class="badge atm">atm</span>':'<span class="badge oce">oce</span>';
    return `<div class="idx-row ${i===0?'win':''}">
      <div class="nm">${r.index}${badge}<small>lag ${r.lag}m</small></div>
      <div class="track"><div class="fill" style="width:${w}%;background:${col}"></div></div>
      <div class="rv">${r.r>=0?'+':''}${r.r}</div></div>`;}).join('');
  const win=rows[0]; const kind=win.kind==='atmosferico'?'atmosferico (SOI)':'oceanico ('+win.index+')';
  document.getElementById('idx-note').innerHTML=
    `Para <b>${UF_NOME[currentUf]}</b>, o indice que melhor acompanha a chuva e o
     <b>${win.index}</b> (${kind}), |r| = <b>${win.abs_r}</b> no lag de <b>${win.lag}m</b>.
     Comparar oceano (RONI/ONI) e atmosfera (SOI) mostra os dois lados acoplados do ENSO;
     o SOI tem sinal oposto por convencao (SOI baixo = El Nino).`;
}

/* ==================== COMPOSICAO ==================== */
function renderComp(){
  const blk=ANALYSIS[currentUf]; if(!blk)return; const comp=blk[compVar].composite;
  const unit=compVar==='precip'?'mm':'°C'; const dec=compVar==='precip'?0:2;
  document.getElementById('comp-var-tag').textContent=compVar==='precip'?'precipitacao':'temperatura';
  document.getElementById('pv-precip').classList.toggle('active',compVar==='precip');
  document.getElementById('pv-temp').classList.toggle('active',compVar==='temp');
  const cls={'El Nino':'nino','La Nina':'nina','Neutro':'neutro'};
  document.getElementById('comp-grid').innerHTML=['El Nino','La Nina','Neutro'].map(ph=>{const o=comp[ph];
    return `<div class="comp ${cls[ph]}"><div class="ph">${ph}</div><div class="cv">${o.mean>=0?'+':''}${o.mean.toFixed(dec)}</div>
      <div class="cu">${unit}</div><div class="cn">n = ${o.n} meses</div></div>`;}).join('');
  const phases=['El Nino','La Nina','Neutro']; const vals=phases.map(p=>comp[p].mean);
  const errs=phases.map(p=>comp[p].std); const cols=['#d1622b','#2f9c95','#6b7794'];
  const ctx=document.getElementById('chart-comp').getContext('2d'); if(chartComp)chartComp.destroy();
  chartComp=new Chart(ctx,{type:'bar',data:{labels:phases,datasets:[{label:`Anomalia (${unit})`,data:vals,backgroundColor:cols,borderRadius:5,borderWidth:0}]},
    options:baseOpts({plugins:{legend:{display:false},tooltip:{...tt(),callbacks:{label:c=>`${c.raw>=0?'+':''}${c.raw.toFixed(dec)} ${unit} (±${errs[c.dataIndex].toFixed(dec)})`}}},
      scales:{x:{ticks:{color:TICK,font:{family:'Space Grotesk',size:11}},grid:{display:false}},
        y:{ticks:{color:TICK,font:{size:9}},grid:{color:GRID},title:{display:true,text:`Anomalia (${unit})`,color:'#4f5d78',font:{size:9}}}}})});
  renderEvent();
}
function renderEvent(){
  document.getElementById('event-title').textContent=`Eventos de referencia · ${UF_NOME[currentUf]}`;
  const el=document.getElementById('event-narrative'); el.className='narrative enso-nino';
  el.innerHTML=`<strong>El Nino Muito Forte ${EVENTO_EL_NINO}</strong> (pico 2015/16) e
    <span style="color:#80cdc1"><strong>La Nina Forte ${EVENTO_LA_NINA}</strong></span> (2010/11) sao os eventos-ancora
    do periodo. Selecione esses anos no seletor do mapa para ver a assinatura espacial de cada fase,
    ou o modo <strong>Teleconexao</strong> para o mapa de correlacao ${PRIMARY}&times;chuva por municipio.`;
}

/* ==================== INIT ==================== */
function hideLoading(msg){const el=document.getElementById('loading');
  if(msg){el.innerHTML=`<p style="max-width:340px;text-align:center;line-height:1.6">${msg}</p>`;return;}
  el.style.display='none';}
function boot(){
  if(typeof L==='undefined'||typeof Chart==='undefined'){
    hideLoading('Nao foi possivel carregar Leaflet/Chart.js (CDN). Verifique a conexao e recarregue — os dados ja estao embutidos neste arquivo.');return;}
  try{populateMuni();initMap();updateLegend();updateRuler(roniYearMean(currentYear));renderSeries();}
  catch(err){console.error('Falha na inicializacao:',err);}
  finally{hideLoading();}
}
window.addEventListener('load',boot);
setTimeout(()=>{const el=document.getElementById('loading');
  if(el&&el.style.display!=='none'&&el.querySelector('.spinner'))boot();},6000);
'''
