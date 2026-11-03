// Conferência independente: regras reescritas a partir da Tabela de política do artigo,
// comparadas com a sequência publicada e com enumeração exata da matriz pontual.
const CM = [[8,0,1,1],[0,8,0,1],[0,0,9,1],[0,0,0,2]];
const FN = 3, INV = -1;

function E(seq, clearFn = true) {
  let s = null, alerted = false, n = 0; const acts = [];
  for (const y of seq) {
    if (y === INV) { acts.push('captura'); s = null; alerted = false; n = 0; continue; }
    if (y === FN) {
      if (s === null) acts.push('registro');
      else { acts.push('revisao'); if (clearFn) { s = null; alerted = false; n = 0; } }
      continue;
    }
    if (s === null) { s = y; n = 1; acts.push('captura'); continue; }
    if (y !== s) { acts.push('revisao'); s = null; alerted = false; n = 0; continue; }
    n++;
    if (alerted) acts.push('registro');
    else { alerted = true; acts.push('alerta:' + y); }
  }
  return acts;
}
function IS(seq) {
  let s = null; const acts = [];
  for (const y of seq) {
    if (y === INV) { acts.push('captura'); s = null; continue; }
    if (y === FN) { acts.push('registro'); s = null; continue; }
    if (y === s) { acts.push('registro'); continue; }
    s = y; acts.push('alerta:' + y);
  }
  return acts;
}
const I = (seq) => seq.map((y) => (y === INV ? 'captura' : y === FN ? 'registro' : 'alerta:' + y));

const pub = [0, 0, 0, 1, INV];
console.log('Tabela 7 I :', I(pub).join(' '));
console.log('Tabela 7 IS:', IS(pub).join(' '));
console.log('Tabela 7 E :', E(pub).join(' '));

// enumeração exata com a matriz pontual, L = 5, independência
function exact(policy) {
  const L = 5; let det = 0, wrong = 0, atrasoSoma = 0, atrasoPeso = 0;
  for (let c = 0; c < 3; c++) {
    const row = CM[c].map((x) => x / CM[c].reduce((a, b) => a + b, 0));
    let total = Math.pow(4, L);
    for (let code = 0; code < total; code++) {
      let k = code, p = 1; const seq = [];
      for (let j = 0; j < L; j++) { const y = k % 4; k = Math.floor(k / 4); seq.push(y); p *= row[y]; }
      if (p === 0) continue;
      const acts = policy(seq);
      const firstOk = acts.findIndex((a) => a === 'alerta:' + c);
      if (firstOk >= 0) { det += p; atrasoSoma += p * (firstOk + 1); atrasoPeso += p; }
      if (acts.some((a) => a.startsWith('alerta:') && a !== 'alerta:' + c)) wrong += p;
    }
  }
  return { det: (100 * det / 3).toFixed(2), epIncorreto: (100 * wrong / 3).toFixed(2), atraso: (atrasoSoma / atrasoPeso).toFixed(3) };
}
console.log('Exato I   :', exact(I));
console.log('Exato IS  :', exact(IS));
console.log('Exato E   :', exact((s) => E(s)));
console.log('Exato E_fn:', exact((s) => E(s, false)));
