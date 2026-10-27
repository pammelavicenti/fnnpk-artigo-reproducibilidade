"""Agente experimental de visão nutricional. Python >=3.10.

As decisões são informacionais; nenhuma saída aciona equipamentos.
"""
import argparse
import hashlib
import json
import math
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

CLASSES = {"def_k", "def_n", "def_p", "fn"}
POLITICA = "duas_capturas_distintas_v1"


def agora():
    return datetime.now(timezone.utc).isoformat()


def instante(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("data_hora deve incluir fuso horário")
    return dt.astimezone(timezone.utc)


class Agente:
    def __init__(self, banco, janela_horas=24):
        if not math.isfinite(janela_horas) or janela_horas <= 0:
            raise ValueError("janela_horas deve ser positiva")
        self.janela = janela_horas * 3600
        self.db = sqlite3.connect(str(banco), timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS plantas (
          planta_id TEXT PRIMARY KEY, estado TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS analises (
          analise_id TEXT PRIMARY KEY, assinatura TEXT NOT NULL,
          planta_id TEXT NOT NULL, captura_hash TEXT NOT NULL,
          resultado TEXT NOT NULL, publicado INTEGER DEFAULT 0,
          tentativas INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS capturas (
          planta_id TEXT NOT NULL, captura_hash TEXT NOT NULL,
          PRIMARY KEY(planta_id, captura_hash));
        """)
        self.db.commit()

    def close(self):
        self.db.close()

    def observar(self, observacao):
        o = dict(observacao)
        for campo in ["analise_id", "planta_id", "captura_hash", "data_hora", "modelo"]:
            if not isinstance(o.get(campo), str) or not o[campo].strip():
                raise ValueError(f"Campo obrigatório: {campo}")
        data = instante(o["data_hora"])
        valida = o.get("imagem_valida", True)
        if not isinstance(valida, bool):
            raise ValueError("imagem_valida deve ser booleano")
        if valida:
            probs = o.get("probabilidades")
            if not isinstance(probs, dict) or set(probs) != CLASSES:
                raise ValueError("probabilidades deve conter def_k, def_n, def_p, fn")
            for v in probs.values():
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1:
                    raise ValueError("Probabilidades inválidas")
            if abs(sum(probs.values()) - 1) > 1e-3:
                raise ValueError("Probabilidades não somam 1")
            classe = max(sorted(CLASSES), key=lambda c: probs[c])
            empate = sum(abs(probs[c] - probs[classe]) < 1e-9 for c in CLASSES) > 1
        else:
            classe, empate = None, False
        assinatura = hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            anterior = self.db.execute("SELECT * FROM analises WHERE analise_id=?", (o["analise_id"],)).fetchone()
            if anterior:
                if anterior["assinatura"] != assinatura:
                    raise ValueError("analise_id reutilizado com conteúdo diferente")
                self.db.commit()
                return dict(json.loads(anterior["resultado"]), repetida=True)
            row = self.db.execute("SELECT estado FROM plantas WHERE planta_id=?", (o["planta_id"],)).fetchone()
            estado = json.loads(row["estado"]) if row else {"candidata": None, "instante": None, "modelo": None, "alertada": None, "ultima": None}
            antes = dict(estado)
            repetida = self.db.execute("SELECT 1 FROM capturas WHERE planta_id=? AND captura_hash=?", (o["planta_id"], o["captura_hash"])).fetchone()
            if estado["ultima"] and data <= instante(estado["ultima"]):
                acao, motivo = "IGNORAR_OBSERVACAO", "Captura anterior ou simultânea à última observação"
            elif repetida:
                acao, motivo = "IGNORAR_OBSERVACAO", "Mesmos bytes de imagem já utilizados para esta planta"
            else:
                estado["ultima"] = o["data_hora"]
                expirou = estado["instante"] and (data - instante(estado["instante"])).total_seconds() > self.janela
                mudou_modelo = estado["modelo"] != o["modelo"]
                if expirou or mudou_modelo:
                    estado.update(candidata=None, instante=None, alertada=None)
                estado["modelo"] = o["modelo"]
                if not valida:
                    acao, motivo = "SOLICITAR_NOVA_CAPTURA", o.get("motivo_invalidade", "Imagem inválida")
                    estado.update(candidata=None, instante=None, alertada=None)
                elif empate:
                    acao, motivo = "ENCAMINHAR_REVISAO", "Empate na maior probabilidade"
                    estado.update(candidata=None, instante=None, alertada=None)
                elif classe == "fn":
                    if estado["candidata"]:
                        acao, motivo = "ENCAMINHAR_REVISAO", "Nutrição completa estimada após suspeita de deficiência"
                    else:
                        acao, motivo = "REGISTRAR_OBSERVACAO", "Nutrição completa estimada; não confirma ausência de deficiência"
                    estado.update(candidata=None, instante=None, alertada=None)
                elif estado["candidata"] is None:
                    acao, motivo = "SOLICITAR_NOVA_CAPTURA", "Primeira suspeita de deficiência"
                    estado.update(candidata=classe, instante=o["data_hora"], alertada=None)
                elif estado["candidata"] != classe:
                    acao, motivo = "ENCAMINHAR_REVISAO", "Classes nutricionais divergentes entre capturas"
                    estado.update(candidata=None, instante=None, alertada=None)
                elif estado["alertada"] == classe:
                    acao, motivo = "REGISTRAR_OBSERVACAO", "Suspeita persiste; alerta já emitido neste episódio"
                else:
                    acao, motivo = "EMITIR_ALERTA", "Duas capturas distintas concordam na suspeita"
                    estado["alertada"] = classe
                self.db.execute("INSERT INTO capturas VALUES (?,?)", (o["planta_id"], o["captura_hash"]))
                self.db.execute("INSERT OR REPLACE INTO plantas VALUES (?,?)", (o["planta_id"], json.dumps(estado)))
            resultado = {
                **o, "classe_prevista": classe, "acao": acao, "motivo": motivo,
                "estado_anterior": antes, "estado_atual": estado,
                "politica": POLITICA, "janela_horas": self.janela / 3600,
                "processado_em": agora(), "diagnostico_confirmado": False,
                "origem": o.get("origem", "nao_informada"),
            }
            self.db.execute("INSERT INTO analises(analise_id,assinatura,planta_id,captura_hash,resultado) VALUES (?,?,?,?,?)",
                            (o["analise_id"], assinatura, o["planta_id"], o["captura_hash"], json.dumps(resultado, ensure_ascii=False)))
            self.db.commit()
            return dict(resultado, repetida=False)
        except Exception:
            self.db.rollback()
            raise

    def publicar_pendentes(self, publicar):
        """publicar(id, resultado) deve armazenar sob uma chave estável por id.

        Nova tentativa pode ocorrer após falha: entrega é pelo menos uma vez.
        Não se promete exatamente uma vez a consumidores de alertas.
        """
        enviados = 0
        for row in self.db.execute("SELECT * FROM analises WHERE publicado=0 ORDER BY rowid").fetchall():
            with self.db:
                self.db.execute("UPDATE analises SET tentativas=tentativas+1 WHERE analise_id=?", (row["analise_id"],))
            try:
                publicar(row["analise_id"], json.loads(row["resultado"]))
            except Exception:
                # Retém a fila sem expor credenciais ou conteúdo da conexão no erro.
                break
            with self.db:
                self.db.execute("UPDATE analises SET publicado=1 WHERE analise_id=?", (row["analise_id"],))
            enviados += 1
        return {"enviados": enviados, "pendentes": self.db.execute("SELECT COUNT(*) FROM analises WHERE publicado=0").fetchone()[0]}

    def exportar(self, caminho):
        with open(caminho, "w", encoding="utf-8") as f:
            for row in self.db.execute("SELECT * FROM analises ORDER BY rowid"):
                item = json.loads(row["resultado"])
                item.update(publicado=bool(row["publicado"]), tentativas_publicacao=row["tentativas"])
                f.write(json.dumps(item, ensure_ascii=False) + "\n")


class ModeloKeras:
    def __init__(self, config):
        self.config = config
        classes = config.get("classes")
        if not isinstance(classes, list) or len(classes) != 4 or set(classes) != CLASSES:
            raise ValueError("Configure a ordem exata das quatro classes do treinamento")
        if not config.get("ordem_classes_confirmada", False):
            raise ValueError("Confirme a ordem das classes antes de habilitar o modelo")
        import tensorflow as tf
        self.tf = tf
        self.model = tf.keras.models.load_model(config["modelo_path"], compile=False)
        self.identidade = hashlib.sha256(Path(config["modelo_path"]).read_bytes()).hexdigest()

    def perceber(self, pedido):
        o = {k: pedido[k] for k in ["analise_id", "planta_id", "imagem_uri", "data_hora"]}
        o.update(modelo=self.identidade, origem="modelo_keras", imagem_valida=True)
        path = Path(o["imagem_uri"])
        if not path.is_file():
            # Erro de submissão: pode ser corrigido e reenviado com o mesmo id.
            raise ValueError("imagem_uri não é um arquivo existente")
        o["captura_hash"] = hashlib.sha256(path.read_bytes()).hexdigest()
        from PIL import Image, ImageOps, UnidentifiedImageError
        import numpy as np
        try:
            with Image.open(path) as im:
                im.load()
                im = ImageOps.exif_transpose(im).convert("RGB")
                if min(im.size) < self.config.get("min_dimensao", 32):
                    o.update(imagem_valida=False, motivo_invalidade="Dimensões abaixo do mínimo operacional")
                    return o
                size = self.config.get("img_size", 224)
                pixels = self.tf.io.decode_image(
                    self.tf.io.read_file(str(path)),
                    channels=3,
                    expand_animations=False,
                )
                arr = self.tf.image.resize(
                    pixels, (size, size), method="bilinear"
                ).numpy()
        except (UnidentifiedImageError, OSError, self.tf.errors.InvalidArgumentError):
            o.update(imagem_valida=False, motivo_invalidade="Arquivo não decodificável como imagem")
            return o
        # EfficientNet padrão inclui Rescaling: entrada RGB float32 em 0..255.
        # Não segmenta a folha: somente usar imagens compatíveis com o treino.
        saida = np.asarray(self.model(arr[None], training=False))
        if saida.shape != (1, 4):
            raise ValueError("Modelo deve produzir uma saída softmax de formato (1,4)")
        o["probabilidades"] = dict(zip(self.config["classes"], map(float, saida[0])))
        return o


def publicador_redis():
    import redis
    client = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=3, socket_timeout=3)
    namespace = os.environ.get("VISAO_NAMESPACE", "visao_experimental:v1")
    def publicar(identificador, resultado):
        # Chave por análise: não sobrescreve hash de sensores ou dados existentes.
        key = namespace + ":analise:" + hashlib.sha256(identificador.encode()).hexdigest()
        client.set(key, json.dumps(resultado, ensure_ascii=False))
    return publicar


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--banco", default="agente_visao.sqlite")
    p.add_argument("--janela-horas", type=float, default=24)
    sub = p.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("simular", help="Percepções controladas, sem modelo nem Redis")
    s.add_argument("--entrada", required=True)
    s.add_argument("--saida", default="resultados_simulados.jsonl")
    a = sub.add_parser("analisar", help="Processar um pedido usando modelo real")
    a.add_argument("--pedido", required=True)
    a.add_argument("--config", required=True)
    a.add_argument("--redis", action="store_true")
    sub.add_parser("publicar", help="Tentar publicar registros pendentes no Redis")
    e = sub.add_parser("exportar")
    e.add_argument("--saida", default="resultados.jsonl")
    w = sub.add_parser("executar", help="Observar pasta de pedidos JSON automaticamente")
    w.add_argument("--entrada", required=True)
    w.add_argument("--config", required=True)
    w.add_argument("--redis", action="store_true")
    w.add_argument("--intervalo", type=float, default=2)
    args = p.parse_args()
    agente = Agente(args.banco, args.janela_horas)
    try:
        if args.comando == "simular":
            with open(args.entrada, encoding="utf-8") as f:
                for linha in f:
                    if linha.strip():
                        o = json.loads(linha)
                        o["origem"] = "percepcao_simulada"
                        r = agente.observar(o)
                        print(r["analise_id"], r["acao"], r["motivo"])
            agente.exportar(args.saida)
            print("Simulação concluída. Não mede acurácia nutricional.")
        elif args.comando == "exportar":
            agente.exportar(args.saida)
        elif args.comando == "publicar":
            print(agente.publicar_pendentes(publicador_redis()))
        else:
            config = json.loads(Path(args.config).read_text(encoding="utf-8"))
            modelo = ModeloKeras(config)
            publicar = publicador_redis() if args.redis else None
            if args.comando == "analisar":
                pedido = json.loads(Path(args.pedido).read_text(encoding="utf-8"))
                print(json.dumps(agente.observar(modelo.perceber(pedido)), ensure_ascii=False, indent=2))
                if publicar:
                    print(agente.publicar_pendentes(publicar))
            else:
                if not math.isfinite(args.intervalo) or args.intervalo <= 0:
                    raise ValueError("intervalo deve ser positivo")
                pasta = Path(args.entrada)
                pasta.mkdir(parents=True, exist_ok=True)
                print("Aguardando pedidos JSON; Ctrl+C encerra.")
                while True:
                    # Enviar arquivos por renomeação atômica (.tmp -> .json).
                    for arquivo in sorted(pasta.glob("*.json")):
                        try:
                            pedido = json.loads(arquivo.read_text(encoding="utf-8"))
                            r = agente.observar(modelo.perceber(pedido))
                            print(r["analise_id"], r["acao"], flush=True)
                            arquivo.rename(arquivo.with_suffix(".concluido"))
                        except Exception as exc:
                            print(arquivo.name, "falhou:", type(exc).__name__, flush=True)
                            arquivo.rename(arquivo.with_suffix(".erro"))
                    if publicar:
                        status = agente.publicar_pendentes(publicar)
                        if status["pendentes"]:
                            print("Publicações pendentes:", status["pendentes"], flush=True)
                    time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("Agente encerrado; histórico preservado.")
    finally:
        agente.close()


if __name__ == "__main__":
    main()
