// Confere se a comparação detecta erro: altera de propósito a política da simulação e conta as divergências.
// Uso: node sensibilidade_do_teste.js <caminho de simulacao_politicas.js>
const fs = require('fs');
const { Agente, CLASSES } = require('./agente');
const fonte = fs.readFileSync(process.argv[2], 'utf8');
const trecho = fonte.slice(fonte.indexOf('function policyE'), fonte.indexOf('const POLICIES'));
const INVALID = -1;
const politica = new Function('FN', 'INVALID', trecho + '; return policyE;')(3, INVALID);
const SIMB = [0, 1, 2, 3, INVALID], T0 = Date.UTC(2026, 0, 1);
const zDe = (y) => { const z = [0.02, 0.02, 0.02, 0.02]; z[y] = 0.94; return z; };
const variantes = {
  'sem alteração': (o, W) => politica(o, W),
  'fn não limpa a suspeita': (o, W) => politica(o, W, { clearOnFn: false }),
  'imagem inválida não limpa a suspeita': (o, W) => politica(o, W, { clearOnInvalid: false }),
  'exige três concordâncias': (o, W) => politica(o, W, { k: 3 }),
  'janela de 48 h em vez de 24 h': (o) => politica(o, 48),
};
for (const delta of [6, 24]) for (const [nome, pol] of Object.entries(variantes)) {
  const a = new Agente(); let div = 0, n = 0;
  for (let c = 0; c < 5 ** 5; c++) {
    let k = c; const obs = [];
    for (let j = 0; j < 5; j++) { obs.push({ t: j * delta, y: SIMB[k % 5] }); k = Math.floor(k / 5); }
    const ag = obs.map(({ t, y }, j) => {
      const p = { id_analise: `${delta}-${nome}-${c}-${j}`, planta: `${delta}-${nome}-${c}`, t: new Date(T0 + t * 3600000).toISOString(), hash: `${c}-${j}`, modelo: 'm', valida: y !== INVALID };
      if (y !== INVALID) p.z = zDe(y);
      const r = a.processar(p);
      return r.acao === 'alerta' ? `alerta${CLASSES.indexOf(r.classe)}` : r.acao;
    });
    const s = pol(obs, 24).map((x) => (x.tipo === 'alerta' ? `alerta${x.classe}` : x.tipo));
    n++; if (JSON.stringify(s) !== JSON.stringify(ag)) div++;
  }
  a.fechar();
  console.log(`Intervalo de ${delta} h | ${nome}: ${div} de ${n} sequências divergentes`);
}
