// Medidas pareadas entre IS e E, com as mesmas sequências e sementes de simulacao_politicas.js.
// Reutiliza as funções daquele script, sem executá-lo por inteiro.
// Uso: node analise_pareada.js   (gera analise_pareada_resultados.json)
const fs = require('fs');
const path = require('path');
const fonte = fs.readFileSync(path.join(__dirname, 'simulacao_politicas.js'), 'utf8');
const ini = fonte.indexOf('const CLASSES'), fim = fonte.indexOf('// ---------- cenário');
const { CM, dirichlet, draw, policyIS, policyE, quantile, mulberry32, INVALID } = new Function('require', fonte.slice(ini, fim) + '; return { CM, dirichlet, draw, policyIS, policyE, quantile, mulberry32, INVALID };')(require);

const BASE = { L: 5, DELTA: 6, W: 24, RHO: 0, PINV: 0, ALPHA: 0.5, R: 1000, M: 1000, plugin: false };
const CEN = [
  { nome: 'S0_base', i: 0 }, { nome: 'S1_plugin', i: 1, plugin: true }, { nome: 'S3_rho0.8', i: 3, RHO: 0.8 },
  { nome: 'S5_d24_W24', i: 5, DELTA: 24 }, { nome: 'S7_L3', i: 7, L: 3 },
];
function resumo(arr) { return { mediana: quantile(arr, 0.5), p2_5: quantile(arr, 0.025), p97_5: quantile(arr, 0.975) }; }
function primeiroCorreto(ac, c) { const j = ac.findIndex((a) => a.tipo === 'alerta' && a.classe === c); return j < 0 ? null : j + 1; }

const saida = { gerado_em: new Date().toISOString(), node: process.version, cenarios: {} };
for (const c of CEN) {
  const sc = { ...BASE, ...c, seed: 20261023 + c.i };
  const rand = mulberry32(sc.seed);
  const k = { detE: [], detIS: [], incE: [], incIS: [], difInc: [], difDet: [], atraso: [], aciE: [], aciIS: [], silencioE: [], semCorretoRevisado: [], repeteE: [], alertasE: [] };
  for (let r = 0; r < sc.R; r++) {
    const rows = CM.map((row) => (sc.plugin ? row.map((x) => x / row.reduce((a, b) => a + b, 0)) : dirichlet(row.map((x) => x + sc.ALPHA), rand)));
    const A = { detE: 0, detIS: 0, incE: 0, incIS: 0, atrasoSoma: 0, atrasoN: 0, aciE: 0, aciIS: 0, silencio: 0, semCorreto: 0, semCorretoRev: 0, repete: 0, alertasE: 0 };
    for (let cl = 0; cl < 4; cl++) {
      for (let m = 0; m < sc.M; m++) {
        const obs = []; let prev = null;
        for (let j = 0; j < sc.L; j++) {
          const y = (prev !== null && rand() < sc.RHO) ? prev : draw(rows[cl], rand);
          prev = y;
          if (sc.PINV > 0) rand();
          obs.push({ t: j * sc.DELTA, y });
        }
        if (cl === 3) continue; // medidas apenas para plantas com deficiência
        const e = policyE(obs, sc.W), s = policyIS(obs, sc.W);
        const pE = primeiroCorreto(e, cl), pS = primeiroCorreto(s, cl);
        const alertasE = e.filter((a) => a.tipo === 'alerta');
        const revE = e.filter((a) => a.tipo === 'revisao').length;
        if (pE) A.detE++; if (pS) A.detIS++;
        if (alertasE.some((a) => a.classe !== cl)) A.incE++;
        if (s.some((a) => a.tipo === 'alerta' && a.classe !== cl)) A.incIS++;
        if (pE && pS) { A.atrasoSoma += pE - pS; A.atrasoN++; }
        A.aciE += alertasE.length + revE; A.aciIS += s.filter((a) => a.tipo === 'alerta').length;
        A.alertasE += alertasE.length;
        if (alertasE.length + revE === 0) A.silencio++;
        if (!pE) { A.semCorreto++; if (revE > 0) A.semCorretoRev++; }
        if (alertasE.filter((a) => a.classe === cl).length >= 2) A.repete++;
      }
    }
    const nd = 3 * sc.M;
    k.detE.push(A.detE / nd); k.detIS.push(A.detIS / nd); k.incE.push(A.incE / nd); k.incIS.push(A.incIS / nd);
    k.difInc.push((A.incIS - A.incE) / nd); k.difDet.push((A.detIS - A.detE) / nd);
    k.atraso.push(A.atrasoN ? A.atrasoSoma / A.atrasoN : NaN);
    k.aciE.push(A.aciE / nd); k.aciIS.push(A.aciIS / nd); k.silencioE.push(A.silencio / nd);
    k.semCorretoRevisado.push(A.semCorreto ? A.semCorretoRev / A.semCorreto : NaN);
    k.repeteE.push(A.repete / nd); k.alertasE.push(A.alertasE / nd);
  }
  saida.cenarios[c.nome] = Object.fromEntries(Object.entries(k).map(([n, v]) => [n, resumo(v)]));
  const f = (x, p = 100, d = 1) => `${(x.mediana * p).toFixed(d)} [${(x.p2_5 * p).toFixed(d)}; ${(x.p97_5 * p).toFixed(d)}]`;
  const o = saida.cenarios[c.nome];
  console.log(`\n== ${c.nome}`);
  console.log('Alerta correto IS/E:', f(o.detIS), '|', f(o.detE));
  console.log('Alerta incorreto IS/E:', f(o.incIS), '|', f(o.incE));
  console.log('Diferença pareada incorreto (IS-E):', f(o.difInc), '| detecção (IS-E):', f(o.difDet));
  console.log('Atraso pareado E-IS (passos):', f(o.atraso, 1, 2));
  console.log('Acionamentos por sequência IS/E:', f(o.aciIS, 1, 2), '|', f(o.aciE, 1, 2));
  console.log('Sem nenhum acionamento em E (%):', f(o.silencioE));
  console.log('Sem alerta correto, mas com revisão em E (%):', f(o.semCorretoRevisado));
  console.log('Dois ou mais alertas corretos em E (%):', f(o.repeteE));
}
// deficiência persistente, classificador sempre correto
const persist = {};
for (const [delta, L] of [[6, 20], [12, 14], [24, 14]]) {
  const obs = Array.from({ length: L }, (_, j) => ({ t: j * delta, y: 0 }));
  persist[`a cada ${delta} h, ${L} fotos`] = policyE(obs, 24).filter((a) => a.tipo === 'alerta').length;
}
saida.deficiencia_persistente_alertas = persist;
console.log('\nDeficiência persistente, alertas de E:', JSON.stringify(persist));
fs.writeFileSync(path.join(__dirname, 'analise_pareada_resultados.json'), JSON.stringify(saida, null, 2));
