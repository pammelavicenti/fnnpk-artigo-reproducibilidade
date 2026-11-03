// Compara o agente de referência (SQLite) com a política E da simulação, passo a passo.
// A função policyE é lida do próprio script da simulação, sem executá-lo por inteiro.
// Uso: node equivalencia.js <caminho de simulacao_politicas.js>
const fs = require('fs');
const path = require('path');
const { Agente, CLASSES } = require('./agente');

const fonte = fs.readFileSync(process.argv[2], 'utf8');
const ini = fonte.indexOf('function policyE'), fim = fonte.indexOf('const POLICIES');
const FN = 3, INVALID = -1;
const policyE = new Function('FN', 'INVALID', fonte.slice(ini, fim) + '; return policyE;')(FN, INVALID);

const T0 = Date.UTC(2026, 0, 1);
const zDe = (y) => { const z = [0.02, 0.02, 0.02, 0.02]; z[y] = 0.94; return z; };
let idPlanta = 0;

function rodarAgente(a, obs) {
  idPlanta++;
  const planta = `s${idPlanta}`;
  return obs.map(({ t, y }, j) => {
    const p = { id_analise: `${planta}-${j}`, planta, t: new Date(T0 + t * 3600000).toISOString(), hash: `${planta}-h${j}`, modelo: 'm', valida: y !== INVALID };
    if (y !== INVALID) p.z = zDe(y);
    const r = a.processar(p);
    return r.acao === 'alerta' ? { tipo: 'alerta', classe: CLASSES.indexOf(r.classe) } : { tipo: r.acao };
  });
}
function iguais(s, ag) {
  return s.length === ag.length && s.every((x, i) => x.tipo === ag[i].tipo && (x.tipo !== 'alerta' || x.classe === ag[i].classe));
}
function mulberry32(seed) { let a = seed >>> 0; return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

const resultado = { grupos: [], exato: {} };
function grupo(nome, W, gerador) {
  const a = new Agente({ W_horas: W });
  let n = 0, passos = 0, div = 0, exemplo = null;
  for (const obs of gerador()) {
    const s = policyE(obs, W), ag = rodarAgente(a, obs);
    n++; passos += obs.length;
    if (!iguais(s, ag)) { div++; if (!exemplo) exemplo = { obs, s, ag }; }
  }
  a.fechar();
  resultado.grupos.push({ nome, W, sequencias: n, passos, divergencias: div, exemplo });
  console.log(`${nome}: ${n} sequências, ${passos} passos, ${div} divergências`);
}
const SIMB = [0, 1, 2, 3, INVALID];
function* todas(L, delta) {
  const total = SIMB.length ** L;
  for (let c = 0; c < total; c++) { let k = c; const obs = []; for (let j = 0; j < L; j++) { obs.push({ t: j * delta, y: SIMB[k % 5] }); k = Math.floor(k / 5); } yield obs; }
}
function* aleatorias(n, seed) {
  const r = mulberry32(seed);
  for (let i = 0; i < n; i++) {
    const L = 2 + Math.floor(r() * 19); let t = 0; const obs = [];
    for (let j = 0; j < L; j++) { obs.push({ t, y: SIMB[Math.floor(r() * 5)] }); t += 1 + Math.floor(r() * 40); }
    yield obs;
  }
}
grupo('Todas as sequências, L=5, a cada 6 h, W=24 h', 24, () => todas(5, 6));
grupo('Todas as sequências, L=5, a cada 24 h, W=24 h', 24, () => todas(5, 24));
grupo('Todas as sequências, L=5, a cada 24 h, W=48 h', 48, () => todas(5, 24));
grupo('Aleatórias, L=2 a 20, intervalos de 1 a 40 h, W=24 h', 24, () => aleatorias(10000, 20261102));

// cenário de matriz pontual, com o próprio agente e probabilidade exata de cada sequência
const CM = [[8, 0, 1, 1], [0, 8, 0, 1], [0, 0, 9, 1], [0, 0, 0, 2]];
{
  const a = new Agente(); let det = 0, errado = 0;
  for (let c = 0; c < 3; c++) {
    const soma = CM[c].reduce((x, y) => x + y, 0), linha = CM[c].map((x) => x / soma);
    for (let code = 0; code < 4 ** 5; code++) {
      let k = code, p = 1; const obs = [];
      for (let j = 0; j < 5; j++) { const y = k % 4; k = Math.floor(k / 4); obs.push({ t: j * 6, y }); p *= linha[y]; }
      if (p === 0) continue;
      const ac = rodarAgente(a, obs);
      if (ac.some((x) => x.tipo === 'alerta' && x.classe === c)) det += p / 3;
      if (ac.some((x) => x.tipo === 'alerta' && x.classe !== c)) errado += p / 3;
    }
  }
  a.fechar();
  resultado.exato = { alerta_correto_pct: +(100 * det).toFixed(2), episodio_alerta_incorreto_pct: +(100 * errado).toFixed(2) };
  console.log('Matriz pontual pelo agente:', resultado.exato);
}
resultado.node = process.version;
resultado.gerado_em = new Date().toISOString();
fs.writeFileSync(path.join(__dirname, 'equivalencia_resultados.json'), JSON.stringify(resultado, null, 2));
