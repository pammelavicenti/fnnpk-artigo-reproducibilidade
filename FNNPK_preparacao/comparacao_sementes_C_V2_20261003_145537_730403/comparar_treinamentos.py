import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["PYTHONHASHSEED"] = "321"

import json
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)

import treinar_alface as original

BASE = original.BASE
DADOS = original.DADOS
SAIDA = BASE / "comparacao_validacao_seed321"
CLASSES = original.CLASSES

EXPERIMENTOS = [
    ("A_pesos_atuais", 1.0, 2e-6),
    ("B_pesos_suavizados", 0.5, 2e-6),
    ("C_ajuste_maior", 0.5, 2e-5),
]


def salvar(caminho, dados):
    caminho.write_text(
        json.dumps(dados, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def relatorio(modelo, validacao):
    reais, probabilidades = [], []

    for imagens, rotulos in validacao:
        reais.extend(np.argmax(rotulos.numpy(), axis=1))
        probabilidades.extend(
            modelo(imagens, training=False).numpy()
        )

    reais = np.asarray(reais)
    probabilidades = np.asarray(probabilidades)
    previstas = probabilidades.argmax(axis=1)

    perda = float(np.mean(-np.log(np.clip(
        probabilidades[np.arange(len(reais)), reais],
        1e-7, 1,
    ))))

    return {
        "acuracia": float(np.mean(reais == previstas)),
        "macro_f1": float(f1_score(
            reais, previstas,
            labels=range(len(CLASSES)),
            average="macro",
            zero_division=0,
        )),
        "perda_sem_smoothing": perda,
        "matriz_confusao": confusion_matrix(
            reais, previstas,
            labels=range(len(CLASSES)),
        ).tolist(),
        "por_classe": classification_report(
            reais, previstas,
            labels=range(len(CLASSES)),
            target_names=CLASSES,
            output_dict=True,
            zero_division=0,
        ),
    }


class SelecaoValidacao(tf.keras.callbacks.Callback):
    def __init__(self, validacao):
        super().__init__()
        self.validacao = validacao
        self.melhor_chave = None
        self.melhores_pesos = None
        self.melhor_relatorio = None
        self.historico = []
        self.fase = "inicial"

    def on_epoch_end(self, epoch, logs=None):
        resultado = relatorio(self.model, self.validacao)
        chave = (
            resultado["macro_f1"],
            -resultado["perda_sem_smoothing"],
        )

        self.historico.append({
            "fase": self.fase,
            "epoca": epoch + 1,
            "macro_f1_validacao": resultado["macro_f1"],
            "perda_validacao_sem_smoothing":
                resultado["perda_sem_smoothing"],
            "metricas_fit": {
                nome: float(valor)
                for nome, valor in (logs or {}).items()
            },
        })

        if self.melhor_chave is None or chave > self.melhor_chave:
            self.melhor_chave = chave
            self.melhores_pesos = self.model.get_weights()
            self.melhor_relatorio = {
                **resultado,
                "fase_selecionada": self.fase,
                "epoca_selecionada": epoch + 1,
            }

        print(
            f"\nValidação: macro F1={resultado['macro_f1']:.4f}; "
            f"acurácia={resultado['acuracia']:.4f}"
        )


def construir_modelo():
    # Transformações mais moderadas que no primeiro treinamento.
    aumento = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal", seed=321),
        tf.keras.layers.RandomRotation(0.05, seed=322),
        tf.keras.layers.RandomZoom(0.10, seed=323),
        tf.keras.layers.RandomContrast(0.10, seed=324),
        tf.keras.layers.RandomBrightness(
            0.05, value_range=(0, 255), seed=325
        ),
    ], name="augmentation_moderado")

    base = tf.keras.applications.EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=(224, 224, 3),
    )
    base.trainable = False

    entrada = tf.keras.Input((224, 224, 3))
    x = aumento(entrada)
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.35, seed=326)(x)
    saida = tf.keras.layers.Dense(
        len(CLASSES), activation="softmax"
    )(x)

    return tf.keras.Model(entrada, saida), base


def compilar(modelo, taxa, regularizacao):
    modelo.compile(
        optimizer=tf.keras.optimizers.AdamW(
            learning_rate=taxa,
            weight_decay=regularizacao,
        ),
        loss=tf.keras.losses.CategoricalCrossentropy(
            label_smoothing=0.05
        ),
        metrics=["accuracy"],
        jit_compile=False,
    )


def callbacks(selecao, pasta, fase):
    return [
        selecao,
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=6 if fase == "inicial" else 5,
            restore_best_weights=False,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=2,
            verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(
            str(pasta / f"historico_{fase}.csv")
        ),
        tf.keras.callbacks.TerminateOnNaN(),
    ]


if __name__ == "__main__":
    if SAIDA.exists():
        raise FileExistsError(
            f"A pasta já existe: {SAIDA}\n"
            "Nenhum resultado será sobrescrito."
        )

    original.configurar_gpu()
    digest = original.verificar_base()
    SAIDA.mkdir()

    contagens = {}
    for classe in CLASSES:
        contagens[classe] = sum(
            p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
            for p in (DADOS / "train" / classe).iterdir()
        )

    total = sum(contagens.values())
    pesos_originais = np.array([
        total / (len(CLASSES) * contagens[classe])
        for classe in CLASSES
    ])

    resumo = {}
    validacao = original.carregar("val")

    # Diagnóstico do modelo anterior somente na validação.
    caminho_anterior = original.SAIDA / "modelo_final.keras"
    if caminho_anterior.is_file():
        anterior = tf.keras.models.load_model(
            caminho_anterior, compile=False
        )
        diagnostico = relatorio(anterior, validacao)
        salvar(SAIDA / "validacao_modelo_anterior.json", diagnostico)
        resumo["modelo_anterior"] = diagnostico
        del anterior

    for nome, expoente, taxa_ajuste in EXPERIMENTOS:
        print(f"\n===== {nome} =====")

        tf.keras.backend.clear_session()
        tf.keras.utils.set_random_seed(321)

        pasta = SAIDA / nome
        pasta.mkdir()

        treino = original.carregar("train", treinamento=True)
        validacao = original.carregar("val")

        pesos = pesos_originais ** expoente
        # Mantém peso médio por imagem de treino igual a 1.
        frequencias = np.array([contagens[c] for c in CLASSES])
        pesos = pesos / (np.sum(pesos * frequencias) / total)
        pesos = {i: float(peso) for i, peso in enumerate(pesos)}

        salvar(pasta / "configuracao.json", {
            "semente": 321,
            "sha256_manifesto": digest,
            "classes": CLASSES,
            "batch_size": 8,
            "epocas_maximas_inicial": 30,
            "epocas_maximas_ajuste": 20,
            "taxa_inicial": 1e-3,
            "taxa_ajuste": taxa_ajuste,
            "weight_decay_inicial": 1e-4,
            "weight_decay_ajuste": 1e-5,
            "expoente_pesos": expoente,
            "pesos_classes": pesos,
            "dropout": 0.35,
            "label_smoothing": 0.05,
            "mixup": False,
            "augmentation": {
                "flip": "horizontal",
                "rotation": 0.05,
                "zoom": 0.10,
                "contrast": 0.10,
                "brightness": 0.05,
            },
            "criterio_selecao": "macro F1; desempate por perda",
            "tensorflow": tf.__version__,
        })

        modelo, base = construir_modelo()
        selecao = SelecaoValidacao(validacao)

        compilar(modelo, 1e-3, 1e-4)
        modelo.fit(
            treino,
            validation_data=validacao,
            epochs=30,
            class_weight=pesos,
            callbacks=callbacks(selecao, pasta, "inicial"),
            verbose=2,
        )

        # Inicia o ajuste fino a partir do melhor modelo da fase inicial.
        modelo.set_weights(selecao.melhores_pesos)
        base.trainable = True

        for indice, camada in enumerate(base.layers):
            camada.trainable = (
                indice >= 210
                and not isinstance(
                    camada, tf.keras.layers.BatchNormalization
                )
            )

        selecao.fase = "ajuste"
        compilar(modelo, taxa_ajuste, 1e-5)
        modelo.fit(
            treino,
            validation_data=validacao,
            epochs=20,
            class_weight=pesos,
            callbacks=callbacks(selecao, pasta, "ajuste"),
            verbose=2,
        )

        modelo.set_weights(selecao.melhores_pesos)
        modelo.save(pasta / "modelo_selecionado.keras")

        salvar(pasta / "validacao.json", selecao.melhor_relatorio)
        salvar(pasta / "historico_selecao.json", selecao.historico)
        resumo[nome] = selecao.melhor_relatorio

        # Salva após cada experimento.
        salvar(SAIDA / "resumo_validacao.json", resumo)
        del modelo, base, selecao

    vencedor = max(
        [nome for nome, _, _ in EXPERIMENTOS],
        key=lambda nome: (
            resumo[nome]["macro_f1"],
            -resumo[nome]["perda_sem_smoothing"],
        ),
    )
    salvar(SAIDA / "selecao_comparacao.json", {
        "melhor_novo_experimento": vencedor,
        "criterio": "macro F1 na validação; desempate por perda",
        "teste_avaliado": False,
    })

    print("\n===== RESUMO DA VALIDAÇÃO =====")
    for nome, resultado in resumo.items():
        print(
            f"{nome}: "
            f"acurácia={resultado['acuracia']:.4f}; "
            f"macro F1={resultado['macro_f1']:.4f}"
        )

    print("\nMelhor novo experimento:", vencedor)
    print("Resultados:", SAIDA)
    print("Nenhuma inferência foi realizada no conjunto de teste.")