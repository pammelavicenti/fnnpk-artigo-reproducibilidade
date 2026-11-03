// Testes do agente de referência. Uso: node --test testes.test.js
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { Agente, ErroConflito, ErroPedido } = require('./agente');

const Z = { def_k: [0.9, 0.04, 0.04, 0.02], def_n: [0.04, 0.9, 0.04, 0.02], def_p: [0.04, 0.04, 0.9, 0.02], fn: [0.02, 0.04, 0.04, 0.9] };
let cont = 0;
function pedido(classe, horas, extra = {}) {
  cont++;
  const t = new Date(Date.UTC(2026, 0, 1) + horas * 3600000).toISOString();
  const base = { id_analise: `a${cont}`, planta: 'p1', t, hash: `h${cont}`, modelo: 'm1', valida: classe !== 'invalida' };
  if (classe !== 'invalida') base.z = Z[classe];
  return { ...base, ...extra };
}

test('Quadro 2: primeira suspeita pede nova captura', () => {
  const a = new Agente();
  const r = a.processar(pedido('def_k', 0));
  assert.equal(r.acao, 'captura'); assert.equal(r.depois.q, 'def_k'); assert.equal(r.depois.a, null);
});
test('Quadro 2: concordância emite alerta', () => {
  const a = new Agente(); a.processar(pedido('def_k', 0));
  const r = a.processar(pedido('def_k', 6));
  assert.equal(r.acao, 'alerta'); assert.equal(r.depois.a, 'def_k');
});
test('Quadro 2: alerta já emitido é registrado sem repetir', () => {
  const a = new Agente(); a.processar(pedido('def_k', 0)); a.processar(pedido('def_k', 6));
  const r = a.processar(pedido('def_k', 12));
  assert.equal(r.acao, 'registro'); assert.equal(r.depois.a, 'def_k');
});
test('Quadro 2: divergência vai para revisão e limpa', () => {
  const a = new Agente(); a.processar(pedido('def_k', 0));
  const r = a.processar(pedido('def_n', 6));
  assert.equal(r.acao, 'revisao'); assert.equal(r.depois.q, null); assert.equal(r.depois.a, null);
});
test('Quadro 2: fn sem suspeita é registrada', () => {
  const a = new Agente(); const r = a.processar(pedido('fn', 0));
  assert.equal(r.acao, 'registro'); assert.equal(r.depois.q, null);
});
test('Quadro 2: fn com suspeita vai para revisão e limpa', () => {
  const a = new Agente(); a.processar(pedido('def_p', 0));
  const r = a.processar(pedido('fn', 6));
  assert.equal(r.acao, 'revisao'); assert.equal(r.depois.q, null);
});
test('Quadro 2: imagem inválida pede captura e limpa', () => {
  const a = new Agente(); a.processar(pedido('def_k', 0));
  const r = a.processar(pedido('invalida', 6));
  assert.equal(r.acao, 'captura'); assert.equal(r.depois.q, null);
});
test('Quadro 2: empate vai para revisão e limpa', () => {
  const a = new Agente(); a.processar(pedido('def_k', 0));
  const r = a.processar(pedido('def_k', 6, { z: [0.4, 0.4, 0.1, 0.1] }));
  assert.equal(r.acao, 'revisao'); assert.equal(r.depois.q, null);
});
test('Tabela 4: sequência de verificação funcional', () => {
  const a = new Agente();
  const acoes = [['def_k', 0], ['def_k', 6], ['def_k', 12], ['def_n', 18], ['invalida', 24]].map(([c, h]) => a.processar(pedido(c, h)).acao);
  assert.deepEqual(acoes, ['captura', 'alerta', 'registro', 'revisao', 'captura']);
});
test('Elegibilidade: pedido idêntico retorna o resultado anterior sem avançar o estado', () => {
  const a = new Agente(); const p = pedido('def_k', 0); const r1 = a.processar(p); const e1 = a.lerEstado('p1');
  const r2 = a.processar(p);
  assert.equal(r2.repetido, true); assert.equal(r2.acao, r1.acao); assert.deepEqual(a.lerEstado('p1'), e1);
});
test('Elegibilidade: mesmo identificador com outro conteúdo é rejeitado', () => {
  const a = new Agente(); const p = pedido('def_k', 0); a.processar(p);
  assert.throws(() => a.processar({ ...p, hash: 'outro' }), ErroConflito);
});
test('Elegibilidade: observação fora de ordem é ignorada', () => {
  const a = new Agente(); a.processar(pedido('def_k', 6)); const e = a.lerEstado('p1');
  const r = a.processar(pedido('def_k', 6));
  assert.equal(r.acao, 'ignorar'); assert.deepEqual(a.lerEstado('p1'), e);
  assert.equal(a.processar(pedido('def_k', 1)).acao, 'ignorar');
});
test('Elegibilidade: imagem repetida é ignorada', () => {
  const a = new Agente(); a.processar(pedido('def_k', 0, { hash: 'x' })); const e = a.lerEstado('p1');
  const r = a.processar(pedido('def_k', 6, { hash: 'x' }));
  assert.equal(r.acao, 'ignorar'); assert.deepEqual(a.lerEstado('p1'), e);
});
test('Expiração: depois de W a suspeita recomeça; exatamente em W ainda vale', () => {
  const a = new Agente(); a.processar(pedido('def_k', 0));
  assert.equal(a.processar(pedido('def_k', 25)).acao, 'captura');
  const b = new Agente(); b.processar(pedido('def_k', 0));
  assert.equal(b.processar(pedido('def_k', 24)).acao, 'alerta');
});
test('Expiração: suspeita persistente volta a gerar alerta depois de W', () => {
  const a = new Agente();
  const acoes = [0, 6, 12, 18, 24, 30, 36].map((h) => a.processar(pedido('def_k', h)).acao);
  assert.deepEqual(acoes, ['captura', 'alerta', 'registro', 'registro', 'registro', 'captura', 'alerta']);
});
test('Troca de modelo reinicia o episódio', () => {
  const a = new Agente(); a.processar(pedido('def_k', 0));
  assert.equal(a.processar(pedido('def_k', 6, { modelo: 'm2' })).acao, 'captura');
});
test('Plantas diferentes têm estados independentes', () => {
  const a = new Agente(); a.processar(pedido('def_k', 0));
  assert.equal(a.processar(pedido('def_k', 6, { planta: 'p2' })).acao, 'captura');
  assert.equal(a.processar(pedido('def_k', 7)).acao, 'alerta');
});
test('Persistência: o estado sobrevive ao fechamento do banco', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'agente-'));
  const arq = path.join(dir, 'a.db');
  let a = new Agente({ caminho: arq }); a.processar(pedido('def_k', 0)); a.fechar();
  a = new Agente({ caminho: arq });
  assert.equal(a.processar(pedido('def_k', 6)).acao, 'alerta'); a.fechar();
  fs.rmSync(dir, { recursive: true, force: true });
});
test('Publicação: falha preserva a pendência e o reenvio após reabrir conclui', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'agente-'));
  const arq = path.join(dir, 'b.db');
  let a = new Agente({ caminho: arq, publicador: () => { throw new Error('sem conexão'); } });
  const r = a.processar(pedido('def_k', 0));
  assert.equal(r.acao, 'captura'); assert.equal(a.contarPendentes(), 1); a.fechar();
  const destino = new Map();
  a = new Agente({ caminho: arq, publicador: (k, v) => destino.set(k, v) });
  assert.deepEqual(a.publicarPendentes(), { enviados: 1, pendentes: 0 });
  assert.equal(destino.size, 1); a.fechar();
  fs.rmSync(dir, { recursive: true, force: true });
});
test('Publicação: reenvio do mesmo pedido não duplica a chave', () => {
  const destino = new Map(); const a = new Agente({ publicador: (k, v) => destino.set(k, v) });
  const p = pedido('def_k', 0); a.processar(p); a.processar(p);
  assert.equal(destino.size, 1);
});
test('Entradas inválidas são rejeitadas', () => {
  const a = new Agente();
  assert.throws(() => a.processar(pedido('def_k', 0, { z: [0.5, 0.2, 0.2, 0.2] })), ErroPedido);
  assert.throws(() => a.processar(pedido('def_k', 0, { z: [1.2, -0.2, 0, 0] })), ErroPedido);
  assert.throws(() => a.processar(pedido('def_k', 0, { t: '2026-01-01T00:00:00' })), ErroPedido);
  assert.equal(a.lerEstado('p1').q, null);
});
