import tempfile
import unittest
from pathlib import Path
from agente_visao import Agente


def obs(n, classe="def_n", planta="p1", **extras):
    probs = {c: 0.02 for c in ["def_k", "def_n", "def_p", "fn"]}
    probs[classe] = 0.94
    return dict(analise_id=f"a{n}", planta_id=planta, captura_hash=f"hash{n}",
                data_hora=f"2026-10-03T{10+n:02}:00:00+00:00",
                modelo="modelo-teste", probabilidades=probs, origem="percepcao_simulada", **extras)


class TestAgente(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "agente.sqlite"
        self.a = Agente(self.path)

    def tearDown(self):
        self.a.close()
        self.tmp.cleanup()

    def test_confirmacao_persistencia_e_supressao(self):
        self.assertEqual(self.a.observar(obs(1))["acao"], "SOLICITAR_NOVA_CAPTURA")
        self.a.close()
        self.a = Agente(self.path)
        self.assertEqual(self.a.observar(obs(2))["acao"], "EMITIR_ALERTA")
        self.assertEqual(self.a.observar(obs(3))["acao"], "REGISTRAR_OBSERVACAO")

    def test_mesma_analise_nao_avanca_estado(self):
        x = obs(1)
        self.a.observar(x)
        self.assertTrue(self.a.observar(x)["repetida"])
        self.assertEqual(self.a.db.execute("SELECT COUNT(*) FROM analises").fetchone()[0], 1)

    def test_id_conflitante_rejeitado(self):
        self.a.observar(obs(1))
        with self.assertRaises(ValueError):
            self.a.observar(obs(1, "def_k"))
        self.assertEqual(self.a.observar(obs(2))["acao"], "EMITIR_ALERTA")

    def test_mesmos_bytes_nao_confirmam(self):
        self.a.observar(obs(1))
        x = obs(2); x["captura_hash"] = "hash1"
        self.assertEqual(self.a.observar(x)["acao"], "IGNORAR_OBSERVACAO")
        self.assertEqual(self.a.observar(obs(3))["acao"], "EMITIR_ALERTA")

    def test_divergencia_deficiencias_e_fn(self):
        for classe in ["def_k", "fn"]:
            x = obs(1, planta=classe); x["analise_id"] += classe
            y = obs(2, classe, planta=classe); y["analise_id"] += classe
            self.a.observar(x)
            self.assertEqual(self.a.observar(y)["acao"], "ENCAMINHAR_REVISAO")

    def test_plantas_independentes(self):
        self.a.observar(obs(1))
        self.assertEqual(self.a.observar(obs(2, planta="p2"))["acao"], "SOLICITAR_NOVA_CAPTURA")

    def test_invalidade_quebra_sequencia(self):
        self.a.observar(obs(1))
        self.a.observar(obs(2, imagem_valida=False))
        self.assertEqual(self.a.observar(obs(3))["acao"], "SOLICITAR_NOVA_CAPTURA")

    def test_observacao_atrasada_nao_altera_estado(self):
        self.a.observar(obs(2))
        self.assertEqual(self.a.observar(obs(1, "fn"))["acao"], "IGNORAR_OBSERVACAO")
        self.assertEqual(self.a.observar(obs(3))["acao"], "EMITIR_ALERTA")

    def test_expiracao_e_troca_modelo(self):
        self.a.observar(obs(1))
        x = obs(2); x["data_hora"] = "2026-10-05T12:00:00+00:00"
        self.assertEqual(self.a.observar(x)["acao"], "SOLICITAR_NOVA_CAPTURA")
        y = obs(3); y.update(data_hora="2026-10-05T13:00:00+00:00", modelo="novo-modelo")
        self.assertEqual(self.a.observar(y)["acao"], "SOLICITAR_NOVA_CAPTURA")

    def test_falha_publicacao_e_reenvio_estavel(self):
        self.a.observar(obs(1))
        destino = {}
        def falha_apos_gravar(i, r):
            destino[i] = r
            raise ConnectionError("Resposta perdida")
        self.assertEqual(self.a.publicar_pendentes(falha_apos_gravar)["pendentes"], 1)
        self.a.close(); self.a = Agente(self.path)
        self.assertEqual(self.a.publicar_pendentes(lambda i, r: destino.__setitem__(i, r))["pendentes"], 0)
        self.assertEqual(len(destino), 1)
        self.assertEqual(self.a.publicar_pendentes(lambda i, r: self.fail("Reenvio indevido"))["enviados"], 0)

    def test_probabilidades_invalidas_nao_alteram_banco(self):
        x = obs(1); x["probabilidades"]["fn"] = float("nan")
        with self.assertRaises(ValueError):
            self.a.observar(x)
        self.assertEqual(self.a.db.execute("SELECT COUNT(*) FROM analises").fetchone()[0], 0)

    def test_empate_vai_para_revisao(self):
        x = obs(1); x["probabilidades"] = dict(def_k=0.4, def_n=0.4, def_p=0.1, fn=0.1)
        self.assertEqual(self.a.observar(x)["acao"], "ENCAMINHAR_REVISAO")


if __name__ == "__main__":
    unittest.main()
