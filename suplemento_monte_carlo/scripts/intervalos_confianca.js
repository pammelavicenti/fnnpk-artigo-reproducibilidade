// Intervalos de confiança para as métricas do teste exploratório (modelo C)
// Entrada: matriz de confusão publicada na Figura 3 (31 imagens).
// Linhas = referência da base; colunas = previsão; ordem def_k, def_n, def_p, fn.
// Saída: intervalos_confianca.json (mesma pasta).
// Uso: node intervalos_confianca.js
const fs = require('fs');
const path = require('path');

const CLASSES = ['def_k', 'def_n', 'def_p', 'fn'];
const CM = [
  [8, 0, 1, 1],
  [0, 8, 0, 1],
  [0, 0, 9, 1],
  [0, 0, 0, 2],
];
const Z = 1.959963984540054; // quantil 97,5% da normal padrão

function wilson(x, n, z = Z) {
  if (n === 0) return [NaN, NaN];
  const p = x / n, z2 = z * z;
  const den = 1 + z2 / n;
  const centre = (p + z2 / (2 * n)) / den;
  const half = (z * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / den;
  return [Math.max(0, centre - half), Math.min(1, centre + half)];
}

function metrics(cm) {
  const K = cm.length;
  let correct = 0, total = 0;
  const per = [];
  for (let c = 0; c < K; c++) {
    const tp = cm[c][c];
    const rowSum = cm[c].reduce((a, b) => a + b, 0);
    let colSum = 0; for (let r = 0; r < K; r++) colSum += cm[r][c];
    correct += tp; total += rowSum;
    const P = colSum ? tp / colSum : 0;
    const R = rowSum ? tp / rowSum : 0;
    const F1 = P + R ? 2 * P * R / (P + R) : 0;
    per.push({ tp, rowSum, colSum, P, R, F1 });
  }
  const mean = (k) => per.reduce((a, b) => a + b[k], 0) / K;
  return { acc: correct / total, correct, total, per, macroP: mean('P'), macroR: mean('R'), macroF1: mean('F1') };
}

// gerador pseudoaleatório reprodutível (mulberry32)
function rng(seed) {
  let a = seed >>> 0;
  return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// bootstrap não paramétrico das 31 imagens (pares referência/previsão)
function bootstrap(cm, B, seed) {
  const pairs = [];
  cm.forEach((row, r) => row.forEach((n, c) => { for (let i = 0; i < n; i++) pairs.push([r, c]); }));
  const rand = rng(seed);
  const f1 = [], acc = [], mp = [], mr = [];
  for (let b = 0; b < B; b++) {
    const m = cm.map((row) => row.map(() => 0));
    for (let i = 0; i < pairs.length; i++) { const [r, c] = pairs[Math.floor(rand() * pairs.length)]; m[r][c]++; }
    const s = metrics(m);
    f1.push(s.macroF1); acc.push(s.acc); mp.push(s.macroP); mr.push(s.macroR);
  }
  const q = (arr, p) => { const a = [...arr].sort((x, y) => x - y); const i = (a.length - 1) * p; const lo = Math.floor(i), hi = Math.ceil(i); return a[lo] + (a[hi] - a[lo]) * (i - lo); };
  const ci = (arr) => [q(arr, 0.025), q(arr, 0.975)];
  return { B, seed, macroF1: ci(f1), accuracy: ci(acc), macroP: ci(mp), macroR: ci(mr),
    nota: 'Classes ausentes numa reamostragem recebem P=R=F1=0 (convenção conservadora).' };
}

const m = metrics(CM);
const out = {
  descricao: 'IC 95% de Wilson para proporções e bootstrap percentil (B=10000) para métricas macro; teste exploratório, 31 imagens, modelo C.',
  matriz: { classes: CLASSES, linhas_referencia_colunas_previsao: CM },
  acuracia: { x: m.correct, n: m.total, p: m.acc, wilson95: wilson(m.correct, m.total) },
  por_classe: CLASSES.map((c, i) => ({
    classe: c,
    precisao: { x: m.per[i].tp, n: m.per[i].colSum, p: m.per[i].P, wilson95: wilson(m.per[i].tp, m.per[i].colSum) },
    revocacao: { x: m.per[i].tp, n: m.per[i].rowSum, p: m.per[i].R, wilson95: wilson(m.per[i].tp, m.per[i].rowSum) },
    f1: m.per[i].F1,
  })),
  macro: { P: m.macroP, R: m.macroR, F1: m.macroF1 },
  bootstrap: bootstrap(CM, 10000, 20261023),
  validacao: {
    A_B: { x: 28, n: 31, p: 28 / 31, wilson95: wilson(28, 31) },
    C: { x: 29, n: 31, p: 29 / 31, wilson95: wilson(29, 31) },
  },
  erro_para_fn_entre_deficiencias: { x: 3, n: 29, p: 3 / 29, wilson95: wilson(3, 29) },
};

// pesos de classe da Equação 3 (n_c do treino; N = 141; K = 4)
const nTrain = { def_k: 48, def_n: 39, def_p: 46, fn: 8 };
function weights(gamma) {
  const N = 141, K = 4;
  const q = Object.fromEntries(Object.entries(nTrain).map(([c, n]) => [c, Math.pow(N / (K * n), gamma)]));
  const den = Object.entries(nTrain).reduce((a, [c, n]) => a + n * q[c], 0) / N;
  return Object.fromEntries(Object.keys(q).map((c) => [c, q[c] / den]));
}
out.pesos_classe = { n_treino: nTrain, gamma_1_0: weights(1), gamma_0_5: weights(0.5) };

const file = path.join(__dirname, 'intervalos_confianca.json');
fs.writeFileSync(file, JSON.stringify(out, null, 2));
const pct = (x) => (100 * x).toFixed(1);
console.log('Acurácia', pct(out.acuracia.p), out.acuracia.wilson95.map(pct));
out.por_classe.forEach((c) => console.log(c.classe, 'P', pct(c.precisao.p), c.precisao.wilson95.map(pct), 'R', pct(c.revocacao.p), c.revocacao.wilson95.map(pct)));
console.log('F1 macro', pct(out.macro.F1), 'bootstrap', out.bootstrap.macroF1.map(pct));
console.log('Validação A/B', out.validacao.A_B.wilson95.map(pct), 'C', out.validacao.C.wilson95.map(pct));
console.log('def->fn', out.erro_para_fn_entre_deficiencias.wilson95.map(pct));
console.log('pesos', JSON.stringify(out.pesos_classe));
