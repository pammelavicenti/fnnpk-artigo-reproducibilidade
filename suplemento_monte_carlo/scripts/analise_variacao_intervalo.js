// Efeito de variar o intervalo entre capturas diárias sobre a política E.
// Reutiliza as funções de simulacao_politicas.js, com priori de Jeffreys e semente fixa.
// Uso: node analise_variacao_intervalo.js   (gera analise_variacao_intervalo_resultados.json)
const fs = require('fs');
const path = require('path');
const fonte = fs.readFileSync(path.join(__dirname, 'simulacao_politicas.js'), 'utf8');
const ini = fonte.indexOf('const CLASSES'), fim = fonte.indexOf('// ---------- cenário');
const { CM, dirichlet, draw, policyE, quantile, mulberry32 } = new Function('require', fonte.slice(ini, fim) + '; return { CM, dirichlet, draw, policyE, quantile, mulberry32 };')(require);

const L = 5, R = 1000, M = 1000, ALPHA = 0.5;
const CEN = [
  { nome: 'exatamente 24 h, W=24 h', W: 24, atraso: () => 0 },
  { nome: 'um minuto a mais em cada foto, W=24 h', W: 24, atraso: () => 1 / 60 },
  { nome: '24 h ± 1 h, W=24 h', W: 24, atraso: (r) => 2 * r() - 1 },
  { nome: '24 h ± 1 h, W=48 h', W: 48, atraso: (r) => 2 * r() - 1 },
];
const saida = { gerado_em: new Date().toISOString(), node: process.version, cenarios: {} };
CEN.forEach((c, i) => {
  const rand = mulberry32(20261102 + i);
  const det = [], sil = [];
  for (let k = 0; k < R; k++) {
    const rows = CM.map((row) => dirichlet(row.map((x) => x + ALPHA), rand));
    let d = 0, s = 0;
    for (let cl = 0; cl < 3; cl++) for (let m = 0; m < M; m++) {
      const obs = []; let t = 0;
      for (let j = 0; j < L; j++) { obs.push({ t, y: draw(rows[cl], rand) }); t += 24 + c.atraso(rand); }
      const ac = policyE(obs, c.W);
      if (ac.some((a) => a.tipo === 'alerta' && a.classe === cl)) d++;
      if (!ac.some((a) => a.tipo === 'alerta' || a.tipo === 'revisao')) s++;
    }
    det.push(d / (3 * M)); sil.push(s / (3 * M));
  }
  const r = (a) => ({ mediana: quantile(a, 0.5), p2_5: quantile(a, 0.025), p97_5: quantile(a, 0.975) });
  saida.cenarios[c.nome] = { alerta_correto: r(det), sem_acionamento: r(sil) };
  const f = (x) => `${(100 * x.mediana).toFixed(1)} [${(100 * x.p2_5).toFixed(1)}; ${(100 * x.p97_5).toFixed(1)}]`;
  console.log(`${c.nome}: alerta correto ${f(r(det))} | sem acionamento ${f(r(sil))}`);
});
fs.writeFileSync(path.join(__dirname, 'analise_variacao_intervalo_resultados.json'), JSON.stringify(saida, null, 2));
