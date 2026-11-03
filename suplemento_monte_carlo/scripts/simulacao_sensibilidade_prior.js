// Simulação Monte Carlo das políticas I, IS e E (e variantes simuladas)
// a partir da matriz de confusão do teste exploratório (Figura 3 do artigo).
//
// Desenho
//  - Episódio: uma planta com condição verdadeira fixa c (def_k, def_n, def_p ou fn),
//    observada L vezes em instantes t_j = j * DELTA (horas), j = 0..L-1.
//  - Previsões: em cada réplica r, as linhas da matriz são sorteadas de
//    Dirichlet(contagens + ALPHA) (propaga a incerteza do n pequeno);
//    dentro da réplica, cada previsão é sorteada da linha da classe verdadeira.
//  - Correlação entre erros sucessivos (RHO): com probabilidade RHO a previsão do
//    passo j repete a do passo j-1; caso contrário é sorteada de novo da linha.
//    A distribuição marginal de cada previsão continua igual à linha da matriz.
//  - Imagens inválidas (PINV): cada observação é inválida com probabilidade PINV,
//    de forma independente da previsão.
//  - Todas as políticas recebem exatamente as mesmas sequências.
//
// Políticas (conforme o artigo, Seções 2.2, 2.3 e 2.8)
//  I   : alerta para toda previsão válida de deficiência; fn -> registro; inválida -> captura.
//  IS  : alerta na 1a previsão de deficiência; mesma classe na janela -> registro;
//        classe diferente -> novo episódio com alerta; inválida/fn/expiração encerram o episódio.
//  E   : política da Tabela 2 (concordância de 2, supressão, divergência -> revisão,
//        fn com suspeita -> revisão e limpeza, inválida -> captura e limpeza, expiração W).
//  Variantes SIMULADAS (não implementadas no agente):
//  E_k3   : exige 3 observações concordantes.
//  E_inv  : imagem inválida solicita captura, mas preserva o episódio.
//  E_fn   : fn com suspeita encaminha revisão, mas preserva o episódio.
//  E_tol  : E_inv + E_fn.
//
// Uso: node simulacao_politicas.js   (gera sensibilidade_prior_resultados.json e sensibilidade_prior_resumo.csv)
const fs = require('fs');
const path = require('path');

const CLASSES = ['def_k', 'def_n', 'def_p', 'fn'];
const FN = 3;
const CM = [
  [8, 0, 1, 1],
  [0, 8, 0, 1],
  [0, 0, 9, 1],
  [0, 0, 0, 2],
];
const INVALID = -1;

// ---------- RNG reprodutível
function mulberry32(seed) {
  let a = seed >>> 0;
  return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function normal(rand) { let u = 0, v = 0; while (u === 0) u = rand(); v = rand(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
function gamma(shape, rand) { // Marsaglia & Tsang (2000)
  if (shape < 1) return gamma(shape + 1, rand) * Math.pow(rand(), 1 / shape);
  const d = shape - 1 / 3, c = 1 / Math.sqrt(9 * d);
  for (;;) {
    let x, v; do { x = normal(rand); v = 1 + c * x; } while (v <= 0);
    v = v * v * v; const u = rand();
    if (u < 1 - 0.0331 * x * x * x * x) return d * v;
    if (Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v;
  }
}
function dirichlet(alpha, rand) { const g = alpha.map((a) => gamma(a, rand)); const s = g.reduce((a, b) => a + b, 0); return g.map((x) => x / s); }
function draw(p, rand) { const u = rand(); let acc = 0; for (let i = 0; i < p.length; i++) { acc += p[i]; if (u < acc) return i; } return p.length - 1; }

// ---------- políticas: recebem [{t, y}] (y = classe prevista ou INVALID) e devolvem ações
// ação: {tipo: 'alerta'|'captura'|'revisao'|'registro', classe}
function policyI(obs) {
  return obs.map(({ y }) => (y === INVALID ? { tipo: 'captura' } : y === FN ? { tipo: 'registro' } : { tipo: 'alerta', classe: y }));
}
function policyIS(obs, W) {
  let q = null, t0 = null; const out = [];
  for (const { t, y } of obs) {
    if (q !== null && t - t0 > W) { q = null; t0 = null; }
    if (y === INVALID) { out.push({ tipo: 'captura' }); q = null; t0 = null; continue; }
    if (y === FN) { out.push({ tipo: 'registro' }); q = null; t0 = null; continue; }
    if (q === y) { out.push({ tipo: 'registro' }); continue; }
    q = y; t0 = t; out.push({ tipo: 'alerta', classe: y });
  }
  return out;
}
function policyE(obs, W, { k = 2, clearOnInvalid = true, clearOnFn = true } = {}) {
  let q = null, t0 = null, a = null, n = 0; const out = [];
  const clear = () => { q = null; t0 = null; a = null; n = 0; };
  for (const { t, y } of obs) {
    if (q !== null && t - t0 > W) clear();
    if (y === INVALID) { out.push({ tipo: 'captura' }); if (clearOnInvalid) clear(); continue; }
    if (y === FN) {
      if (q === null) out.push({ tipo: 'registro' });
      else { out.push({ tipo: 'revisao' }); if (clearOnFn) clear(); }
      continue;
    }
    if (q === null) { q = y; t0 = t; n = 1; a = null; if (n >= k) { a = y; out.push({ tipo: 'alerta', classe: y }); } else out.push({ tipo: 'captura' }); continue; }
    if (y !== q) { out.push({ tipo: 'revisao' }); clear(); continue; }
    n += 1;
    if (a !== null) out.push({ tipo: 'registro' });
    else if (n >= k) { a = y; out.push({ tipo: 'alerta', classe: y }); }
    else out.push({ tipo: 'captura' });
  }
  return out;
}
const POLICIES = {
  I: (o, W) => policyI(o),
  IS: (o, W) => policyIS(o, W),
  E: (o, W) => policyE(o, W),
  E_k3: (o, W) => policyE(o, W, { k: 3 }),
  E_inv: (o, W) => policyE(o, W, { clearOnInvalid: false }),
  E_fn: (o, W) => policyE(o, W, { clearOnFn: false }),
  E_tol: (o, W) => policyE(o, W, { clearOnInvalid: false, clearOnFn: false }),
};
const PNAMES = Object.keys(POLICIES);

// ---------- métricas de um episódio
function episodeMetrics(actions, c) {
  let alerts = 0, correct = 0, wrong = 0, reviews = 0, captures = 0, first = null;
  actions.forEach((a, j) => {
    if (a.tipo === 'alerta') { alerts++; if (a.classe === c) { correct++; if (first === null) first = j + 1; } else wrong++; }
    else if (a.tipo === 'revisao') reviews++;
    else if (a.tipo === 'captura') captures++;
  });
  return { alerts, correct, wrong, reviews, captures, first };
}

function quantile(arr, p) { const a = arr.filter((x) => Number.isFinite(x)).sort((x, y) => x - y); if (!a.length) return NaN; const i = (a.length - 1) * p; const lo = Math.floor(i), hi = Math.ceil(i); return a[lo] + (a[hi] - a[lo]) * (i - lo); }

// ---------- cenário
function runScenario(sc) {
  const { nome, L, DELTA, W, RHO, PINV, ALPHA, R, M, seed, plugin } = sc;
  const rand = mulberry32(seed);
  const rep = {}; // rep[policy][metric] = array over replicates
  const keys = ['det', 'semAlertaCorreto', 'semNenhumAlerta', 'alertasCorretosEp', 'alertasIncorretosEp', 'epComAlertaIncorreto', 'alertasEp', 'revisoesEp', 'capturasEp', 'atraso',
    'det_def_k', 'det_def_n', 'det_def_p', 'fn_epComAlerta', 'fn_alertasEp', 'fn_revisoesEp'];
  PNAMES.forEach((p) => { rep[p] = {}; keys.forEach((k) => (rep[p][k] = [])); });

  for (let r = 0; r < R; r++) {
    const rows = CM.map((row) => (plugin ? row.map((x) => x / row.reduce((a, b) => a + b, 0)) : dirichlet(row.map((x) => x + ALPHA), rand)));
    const acc = {}; PNAMES.forEach((p) => (acc[p] = { det: 0, none: 0, corr: 0, wrong: 0, epWrong: 0, alerts: 0, rev: 0, cap: 0, delaySum: 0, delayN: 0, detc: [0, 0, 0], fnEp: 0, fnAl: 0, fnRev: 0 }));
    for (let c = 0; c < 4; c++) {
      for (let m = 0; m < M; m++) {
        const obs = []; let prev = null;
        for (let j = 0; j < L; j++) {
          let y = (prev !== null && rand() < RHO) ? prev : draw(rows[c], rand);
          prev = y;
          const inval = PINV > 0 && rand() < PINV;
          obs.push({ t: j * DELTA, y: inval ? INVALID : y });
        }
        for (const p of PNAMES) {
          const e = episodeMetrics(POLICIES[p](obs, W), c);
          const A = acc[p];
          if (c === FN) { A.fnAl += e.alerts; if (e.alerts > 0) A.fnEp++; A.fnRev += e.reviews; continue; }
          if (e.correct > 0) { A.det++; A.detc[c]++; A.delaySum += e.first; A.delayN++; }
          if (e.alerts === 0) A.none++;
          A.corr += e.correct; A.wrong += e.wrong; if (e.wrong > 0) A.epWrong++;
          A.alerts += e.alerts; A.rev += e.reviews; A.cap += e.captures;
        }
      }
    }
    const nd = 3 * M;
    for (const p of PNAMES) {
      const A = acc[p], o = rep[p];
      o.det.push(A.det / nd); o.semAlertaCorreto.push(1 - A.det / nd); o.semNenhumAlerta.push(A.none / nd);
      o.alertasCorretosEp.push(A.corr / nd); o.alertasIncorretosEp.push(A.wrong / nd); o.epComAlertaIncorreto.push(A.epWrong / nd);
      o.alertasEp.push(A.alerts / nd); o.revisoesEp.push(A.rev / nd); o.capturasEp.push(A.cap / nd);
      o.atraso.push(A.delayN ? A.delaySum / A.delayN : NaN);
      o.det_def_k.push(A.detc[0] / M); o.det_def_n.push(A.detc[1] / M); o.det_def_p.push(A.detc[2] / M);
      o.fn_epComAlerta.push(A.fnEp / M); o.fn_alertasEp.push(A.fnAl / M); o.fn_revisoesEp.push(A.fnRev / M);
    }
  }
  const summary = {};
  for (const p of PNAMES) {
    summary[p] = {};
    for (const k of keys) {
      const arr = rep[p][k];
      summary[p][k] = { mediana: quantile(arr, 0.5), p2_5: quantile(arr, 0.025), p97_5: quantile(arr, 0.975), media: arr.reduce((a, b) => a + b, 0) / arr.length };
    }
  }
  return { cenario: sc, resumo: summary };
}

// ---------- cenários
const BASE = { L: 5, DELTA: 6, W: 24, RHO: 0, PINV: 0, ALPHA: 0.5, R: 1000, M: 1000, plugin: false };
const SCENARIOS = [0.1, 1].map((alpha, i) => ({ ...BASE, nome: 'prior_alpha_' + alpha, descricao: 'Sensibilidade a priori Dirichlet simetrica alpha=' + alpha, ALPHA: alpha, seed: 20261033 + i }));

const t0 = Date.now();
const results = SCENARIOS.map((sc) => { const r = runScenario(sc); console.log('ok', sc.nome, ((Date.now() - t0) / 1000).toFixed(1) + 's'); return r; });

// verificação analítica simples (matriz pontual, independência): P(2 primeiras previsões corretas)
const analitico = CLASSES.slice(0, 3).map((c, i) => { const p = CM[i][i] / CM[i].reduce((a, b) => a + b, 0); return { classe: c, p_correta: p, p_duas_primeiras_corretas: p * p }; });

const outDir = __dirname;
fs.writeFileSync(path.join(outDir, 'sensibilidade_prior_resultados.json'), JSON.stringify({
  gerado_em: new Date().toISOString(), node: process.version, matriz: { classes: CLASSES, linhas_referencia_colunas_previsao: CM },
  politicas: PNAMES, analitico, resultados: results,
}, null, 2));

const lines = ['cenario,politica,metrica,mediana,p2_5,p97_5,media'];
for (const r of results) for (const p of PNAMES) for (const [k, v] of Object.entries(r.resumo[p])) lines.push([r.cenario.nome, p, k, v.mediana, v.p2_5, v.p97_5, v.media].map((x) => (typeof x === 'number' ? x.toFixed(4) : x)).join(','));
fs.writeFileSync(path.join(outDir, 'sensibilidade_prior_resumo.csv'), lines.join('\n'));

// impressão resumida
const f = (v, pct = true) => pct ? `${(100 * v.mediana).toFixed(1)} [${(100 * v.p2_5).toFixed(1)}; ${(100 * v.p97_5).toFixed(1)}]` : `${v.mediana.toFixed(2)} [${v.p2_5.toFixed(2)}; ${v.p97_5.toFixed(2)}]`;
for (const r of results) {
  console.log('\n==', r.cenario.nome, '-', r.cenario.descricao);
  for (const p of PNAMES) {
    const s = r.resumo[p];
    console.log(p.padEnd(6), 'det%', f(s.det), '| incorr/ep', f(s.alertasIncorretosEp, false), '| epIncorr%', f(s.epComAlertaIncorreto), '| alertas/ep', f(s.alertasEp, false), '| atraso', f(s.atraso, false), '| rev/ep', f(s.revisoesEp, false), '| capt/ep', f(s.capturasEp, false), '| fn epAlerta%', f(s.fn_epComAlerta), '| fn alert/ep', f(s.fn_alertasEp, false));
  }
}
console.log('\nanalitico', JSON.stringify(analitico));
