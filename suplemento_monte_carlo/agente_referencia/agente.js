// Implementação de referência do agente de visão com estado (Seções 2.2 a 2.5 do artigo).
// Recebe a percepção pronta (saídas softmax): não executa a rede neural.
// A publicação é uma função injetada; em produção, seria a escrita no Redis.
const { DatabaseSync } = require('node:sqlite');

const CLASSES = ['def_k', 'def_n', 'def_p', 'fn'];
const FN = 'fn';
const ACOES = { CAPTURA: 'captura', ALERTA: 'alerta', REGISTRO: 'registro', REVISAO: 'revisao', IGNORAR: 'ignorar' };
const HORA = 3600 * 1000;

const VAZIO = { q: null, t0: null, m_s: null, a: null, t_u: null };

class ErroConflito extends Error {}
class ErroPedido extends Error {}

function validar(p) {
  for (const c of ['id_analise', 'planta', 't', 'hash', 'modelo']) {
    if (typeof p[c] !== 'string' || !p[c]) throw new ErroPedido(`Campo inválido: ${c}`);
  }
  if (typeof p.valida !== 'boolean') throw new ErroPedido('Campo inválido: valida');
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(p.t) || Number.isNaN(Date.parse(p.t))) throw new ErroPedido('Data sem fuso horário ou inválida');
  if (!p.valida) return;
  const z = p.z;
  if (!Array.isArray(z) || z.length !== CLASSES.length || !z.every((v) => Number.isFinite(v) && v >= 0 && v <= 1)) throw new ErroPedido('Saídas softmax inválidas');
  if (Math.abs(z.reduce((a, b) => a + b, 0) - 1) > 1e-6) throw new ErroPedido('Saídas softmax não somam 1');
}

// Quadro 2, na ordem apresentada. Recebe a percepção e o estado; devolve a ação e o novo estado.
function decidir(p, estado, tms) {
  const limpar = (s) => ({ ...s, q: null, t0: null, a: null, m_s: null });
  if (!p.valida) return { acao: ACOES.CAPTURA, motivo: 'imagem inválida', classe: null, novo: limpar(estado) };
  const max = Math.max(...p.z);
  if (p.z.filter((v) => v === max).length > 1) return { acao: ACOES.REVISAO, motivo: 'empate na maior saída', classe: null, novo: limpar(estado) };
  const y = CLASSES[p.z.indexOf(max)];
  if (y === FN) {
    if (estado.q === null) return { acao: ACOES.REGISTRO, motivo: 'sem deficiência, sem suspeita', classe: y, novo: estado };
    return { acao: ACOES.REVISAO, motivo: 'sem deficiência, com suspeita', classe: y, novo: limpar(estado) };
  }
  if (estado.q === null) return { acao: ACOES.CAPTURA, motivo: 'primeira suspeita', classe: y, novo: { ...estado, q: y, t0: tms, m_s: p.modelo, a: null } };
  if (y !== estado.q) return { acao: ACOES.REVISAO, motivo: 'divergência', classe: y, novo: limpar(estado) };
  if (estado.a !== null) return { acao: ACOES.REGISTRO, motivo: 'alerta já emitido', classe: y, novo: estado };
  return { acao: ACOES.ALERTA, motivo: 'concordância', classe: y, novo: { ...estado, a: y } };
}

class Agente {
  constructor({ caminho = ':memory:', publicador = null, W_horas = 24 } = {}) {
    this.db = new DatabaseSync(caminho);
    this.publicador = publicador;
    this.W = W_horas * HORA;
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS estado (planta TEXT PRIMARY KEY, q TEXT, t0 INTEGER, m_s TEXT, a TEXT, t_u INTEGER);
      CREATE TABLE IF NOT EXISTS analise (id_analise TEXT PRIMARY KEY, planta TEXT, conteudo TEXT, resultado TEXT, pendente INTEGER, tentativas INTEGER DEFAULT 0);
      CREATE TABLE IF NOT EXISTS captura (planta TEXT, hash TEXT, PRIMARY KEY (planta, hash));
    `);
  }

  fechar() { this.db.close(); }

  lerEstado(planta) {
    const r = this.db.prepare('SELECT q, t0, m_s, a, t_u FROM estado WHERE planta = ?').get(planta);
    return r ? { q: r.q, t0: r.t0, m_s: r.m_s, a: r.a, t_u: r.t_u } : { ...VAZIO };
  }

  processar(p) {
    validar(p);
    const conteudo = JSON.stringify({ id_analise: p.id_analise, planta: p.planta, t: p.t, hash: p.hash, modelo: p.modelo, valida: p.valida, z: p.z ?? null });
    const anterior = this.db.prepare('SELECT conteudo, resultado FROM analise WHERE id_analise = ?').get(p.id_analise);
    if (anterior) {
      if (anterior.conteudo !== conteudo) throw new ErroConflito(`Identificador repetido com outro conteúdo: ${p.id_analise}`);
      return { ...JSON.parse(anterior.resultado), repetido: true };
    }
    const tms = Date.parse(p.t);
    const antes = this.lerEstado(p.planta);
    let saida;
    const hashUsado = this.db.prepare('SELECT 1 AS x FROM captura WHERE planta = ? AND hash = ?').get(p.planta, p.hash);
    if (antes.t_u !== null && tms <= antes.t_u) {
      saida = { acao: ACOES.IGNORAR, motivo: 'fora de ordem', classe: null, novo: antes };
    } else if (hashUsado) {
      saida = { acao: ACOES.IGNORAR, motivo: 'imagem repetida', classe: null, novo: antes };
    } else {
      let base = { ...antes, t_u: tms };
      if (base.q !== null && (base.m_s !== p.modelo || tms - base.t0 > this.W)) base = { ...base, q: null, t0: null, m_s: null, a: null };
      saida = decidir(p, base, tms);
    }
    const resultado = { id_analise: p.id_analise, planta: p.planta, acao: saida.acao, motivo: saida.motivo, classe: saida.classe, antes, depois: saida.novo, repetido: false };
    this.db.exec('BEGIN');
    try {
      this.db.prepare('INSERT INTO analise (id_analise, planta, conteudo, resultado, pendente) VALUES (?, ?, ?, ?, 1)').run(p.id_analise, p.planta, conteudo, JSON.stringify(resultado));
      if (saida.acao !== ACOES.IGNORAR) {
        const n = saida.novo;
        this.db.prepare('INSERT INTO estado (planta, q, t0, m_s, a, t_u) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(planta) DO UPDATE SET q=excluded.q, t0=excluded.t0, m_s=excluded.m_s, a=excluded.a, t_u=excluded.t_u').run(p.planta, n.q, n.t0, n.m_s, n.a, n.t_u);
        this.db.prepare('INSERT INTO captura (planta, hash) VALUES (?, ?)').run(p.planta, p.hash);
      }
      this.db.exec('COMMIT');
    } catch (e) { this.db.exec('ROLLBACK'); throw e; }
    this.publicarPendentes();
    return resultado;
  }

  // Tenta publicar o que está pendente; uma falha preserva a pendência para nova tentativa.
  publicarPendentes() {
    if (!this.publicador) return { enviados: 0, pendentes: this.contarPendentes() };
    const linhas = this.db.prepare('SELECT id_analise, resultado FROM analise WHERE pendente = 1').all();
    let enviados = 0;
    for (const l of linhas) {
      this.db.prepare('UPDATE analise SET tentativas = tentativas + 1 WHERE id_analise = ?').run(l.id_analise);
      try {
        this.publicador(`agente:${l.id_analise}`, l.resultado);
        this.db.prepare('UPDATE analise SET pendente = 0 WHERE id_analise = ?').run(l.id_analise);
        enviados++;
      } catch { /* mantém pendente */ }
    }
    return { enviados, pendentes: this.contarPendentes() };
  }

  contarPendentes() { return this.db.prepare('SELECT COUNT(*) AS n FROM analise WHERE pendente = 1').get().n; }
}

module.exports = { Agente, ErroConflito, ErroPedido, CLASSES, ACOES };
