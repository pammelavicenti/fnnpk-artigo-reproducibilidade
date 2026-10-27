import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["PYTHONHASHSEED"] = "321"

import argparse
import csv
import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

BASE = Path(os.environ.get("FNNPK_PREPARACAO", Path(__file__).resolve().parent.parent))
DADOS = BASE / "divisao_agrupada"
SAIDA = BASE / "resultado_divisao_agrupada_seed321"

CLASSES = ["def_k", "def_n", "def_p", "fn"]
SEMENTE = 321
TAMANHO = 224
LOTE = 8
EPOCAS_INICIAL = 14
EPOCAS_AJUSTE = 10


def salvar_json(caminho, conteudo):
    caminho.write_text(
        json.dumps(conteudo, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def verificar_base():
    manifesto = DADOS / "manifesto_divisao.csv"
    if not manifesto.is_file():
        raise FileNotFoundError(manifesto)

    with manifesto.open(encoding="utf-8-sig", newline="") as arquivo:
        registros = list(csv.DictReader(arquivo))

    grupos = {}
    hashes = set()
    esperados = set()

    for item in registros:
        caminho = DADOS / item["arquivo_divisao"]
        if not caminho.is_file():
            raise FileNotFoundError(caminho)

        digest = hashlib.sha256(caminho.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"Imagem alterada: {caminho}")
        if digest in hashes:
            raise ValueError(f"Cópia idêntica encontrada: {caminho}")

        hashes.add(digest)
        esperados.add(caminho.resolve())
        grupos.setdefault(item["grupo_id"], set()).add(item["particao"])

    if any(len(particoes) > 1 for particoes in grupos.values()):
        raise ValueError("Um grupo aparece em mais de uma partição.")

    encontrados = {
        caminho.resolve()
        for particao in ("train", "val", "test")
        for caminho in (DADOS / particao).rglob("*")
        if caminho.is_file()
        and caminho.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
    }

    if encontrados != esperados:
        raise ValueError("As imagens nas pastas não correspondem ao manifesto.")

    return hashlib.sha256(manifesto.read_bytes()).hexdigest()


def carregar(particao, treinamento=False):
    return tf.keras.utils.image_dataset_from_directory(
        DADOS / particao,
        class_names=CLASSES,
        label_mode="categorical",
        image_size=(TAMANHO, TAMANHO),
        batch_size=LOTE,
        shuffle=treinamento,
        seed=SEMENTE,
    ).prefetch(tf.data.AUTOTUNE)


def configurar_gpu():
    gpus = tf.config.list_physical_devices("GPU")
    if not gpus:
        raise RuntimeError("GPU não reconhecida neste ambiente.")

    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)

    # Confirma que uma operação de convolução executa na GPU.
    with tf.device("/GPU:0"):
        entrada = tf.ones((1, 32, 32, 3))
        filtro = tf.ones((3, 3, 3, 8))
        resultado = tf.nn.conv2d(
            entrada, filtro, strides=1, padding="SAME"
        )
        resultado.numpy()

    if "GPU" not in resultado.device.upper():
        raise RuntimeError("A operação de verificação executou fora da GPU.")

    print("GPU verificada:", resultado.device)


def construir_modelo():
    aumento = tf.keras.Sequential([
        tf.keras.layers.RandomFlip(
            "horizontal_and_vertical", seed=SEMENTE
        ),
        tf.keras.layers.RandomRotation(0.2, seed=SEMENTE + 1),
        tf.keras.layers.RandomZoom(0.2, seed=SEMENTE + 2),
        tf.keras.layers.RandomContrast(0.2, seed=SEMENTE + 3),
        tf.keras.layers.RandomBrightness(
            0.2, value_range=(0, 255), seed=SEMENTE + 4
        ),
    ], name="augmentation")

    base = tf.keras.applications.EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=(TAMANHO, TAMANHO, 3),
    )
    base.trainable = False

    entrada = tf.keras.Input((TAMANHO, TAMANHO, 3))
    x = aumento(entrada)
    # EfficientNet já contém o reescalonamento dos pixels.
    # BatchNormalization permanece em modo de inferência.
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.35, seed=SEMENTE + 5)(x)
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
        # Mesmo critério nas duas fases para comparar val_loss.
        loss=tf.keras.losses.CategoricalCrossentropy(
            label_smoothing=0.05
        ),
        metrics=["accuracy"],
        jit_compile=False,
    )


def callbacks(fase, paciencia, paciencia_lr):
    return [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=paciencia,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=paciencia_lr,
            verbose=1,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(SAIDA / f"melhor_{fase}.keras"),
            monitor="val_loss",
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(
            str(SAIDA / f"historico_{fase}.csv")
        ),
        tf.keras.callbacks.TerminateOnNaN(),
    ]


def plotar_historico(historicos):
    fig, eixos = plt.subplots(1, 2, figsize=(11, 4))
    limite = len(historicos[0]["loss"])

    for eixo, metrica, titulo in zip(
        eixos, ["accuracy", "loss"], ["Acurácia", "Perda"]
    ):
        treino = [
            valor for historia in historicos
            for valor in historia[metrica]
        ]
        validacao = [
            valor for historia in historicos
            for valor in historia[f"val_{metrica}"]
        ]
        epocas = np.arange(1, len(treino) + 1)
        eixo.plot(epocas, treino, label="Treino")
        eixo.plot(epocas, validacao, label="Validação")
        eixo.axvline(limite + 0.5, color="gray", linestyle="--")
        eixo.set(xlabel="Época", ylabel=titulo)
        eixo.legend()
        eixo.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(SAIDA / "curvas_treinamento.png", dpi=300)
    plt.close(fig)


def treinar(digest_manifesto):
    if SAIDA.exists():
        raise FileExistsError(
            f"A pasta de resultados já existe: {SAIDA}\n"
            "Nenhum treinamento será sobrescrito."
        )

    SAIDA.mkdir()
    treino = carregar("train", treinamento=True)
    validacao = carregar("val")

    contagens = {
        classe: sum(
            caminho.is_file()
            and caminho.suffix.lower() in {".png", ".jpg", ".jpeg"}
            for caminho in (DADOS / "train" / classe).iterdir()
        )
        for classe in CLASSES
    }
    if any(numero == 0 for numero in contagens.values()):
        raise ValueError("Existe classe sem imagens de treino.")

    total = sum(contagens.values())
    pesos = {
        indice: total / (len(CLASSES) * contagens[classe])
        for indice, classe in enumerate(CLASSES)
    }
    print("Imagens de treino:", contagens)
    print("Pesos por classe:", pesos)

    configuracao = {
        "semente_treinamento": SEMENTE,
        "sha256_manifesto": digest_manifesto,
        "classes": CLASSES,
        "tamanho_imagem": TAMANHO,
        "batch_size": LOTE,
        "modelo": "EfficientNetB0",
        "pesos_iniciais": "ImageNet",
        "dropout": 0.35,
        "mixup": False,
        "label_smoothing_ambas_fases": 0.05,
        "pesos_classes": pesos,
        "contagens_treino": contagens,
        "fase_inicial": {
            "epocas_maximas": EPOCAS_INICIAL,
            "learning_rate": 1e-3,
            "weight_decay": 1e-4,
            "early_stopping_patience": 4,
            "reduce_lr_patience": 2,
        },
        "ajuste_fino": {
            "epocas_maximas": EPOCAS_AJUSTE,
            "primeiras_camadas_congeladas": 210,
            "learning_rate": 2e-6,
            "weight_decay": 1e-5,
            "early_stopping_patience": 3,
            "reduce_lr_patience": 1,
        },
        "criterio_selecao": "menor val_loss entre as duas fases",
        "python": platform.python_version(),
        "tensorflow": tf.__version__,
        "keras": version("keras"),
        "numpy": np.__version__,
        "scikit_learn": version("scikit-learn"),
    }
    salvar_json(SAIDA / "configuracao.json", configuracao)

    modelo, base = construir_modelo()
    compilar(modelo, 1e-3, 1e-4)
    h1 = modelo.fit(
        treino,
        validation_data=validacao,
        epochs=EPOCAS_INICIAL,
        class_weight=pesos,
        callbacks=callbacks("inicial", 4, 2),
    )

    base.trainable = True
    for indice, camada in enumerate(base.layers):
        camada.trainable = (
            indice >= 210
            and not isinstance(camada, tf.keras.layers.BatchNormalization)
        )

    compilar(modelo, 2e-6, 1e-5)
    h2 = modelo.fit(
        treino,
        validation_data=validacao,
        epochs=EPOCAS_AJUSTE,
        class_weight=pesos,
        callbacks=callbacks("ajuste", 3, 1),
    )

    perdas = {
        "inicial": float(min(h1.history["val_loss"])),
        "ajuste": float(min(h2.history["val_loss"])),
    }
    fase = min(perdas, key=perdas.get)
    escolhido = tf.keras.models.load_model(
        SAIDA / f"melhor_{fase}.keras", compile=False
    )
    escolhido.save(SAIDA / "modelo_final.keras")

    historicos = [
        {chave: [float(v) for v in valores]
         for chave, valores in historia.history.items()}
        for historia in (h1, h2)
    ]
    salvar_json(SAIDA / "historicos.json", historicos)
    plotar_historico(historicos)
    salvar_json(SAIDA / "selecao_validacao.json", {
        "fase_escolhida": fase,
        "melhores_perdas_validacao": perdas,
        "epocas_executadas": [
            len(h1.history["loss"]), len(h2.history["loss"])
        ],
    })

    print("\nTreinamento concluído.")
    print("Modelo escolhido pela validação:", fase)
    print("Resultados:", SAIDA)
    print("O conjunto de teste ainda não foi avaliado.")


def predizer_tta(modelo, imagens):
    # As imagens estão na escala 0–255.
    variantes = [
        imagens,
        tf.image.flip_left_right(imagens),
        tf.image.flip_up_down(imagens),
        tf.clip_by_value(
            tf.image.adjust_brightness(imagens, 0.08 * 255), 0, 255
        ),
        tf.clip_by_value(
            tf.image.adjust_contrast(imagens, 1.1), 0, 255
        ),
    ]
    probabilidades = [
        modelo(variante, training=False) for variante in variantes
    ]
    return tf.reduce_mean(tf.stack(probabilidades), axis=0)


def avaliar(digest_manifesto):
    if not (SAIDA / "modelo_final.keras").is_file():
        raise FileNotFoundError("Execute primeiro o treinamento.")

    destino = SAIDA / "avaliacao_teste"
    if destino.exists():
        raise FileExistsError(
            "A avaliação já existe. Nenhum resultado será sobrescrito."
        )

    configuracao = json.loads(
        (SAIDA / "configuracao.json").read_text(encoding="utf-8")
    )
    if configuracao["sha256_manifesto"] != digest_manifesto:
        raise ValueError("A divisão foi alterada após o treinamento.")

    modelo = tf.keras.models.load_model(
        SAIDA / "modelo_final.keras", compile=False
    )
    teste = carregar("test")
    verdade, simples, aumentado = [], [], []

    for imagens, rotulos in teste:
        verdade.extend(np.argmax(rotulos.numpy(), axis=1))
        simples.extend(modelo(imagens, training=False).numpy())
        aumentado.extend(predizer_tta(modelo, imagens).numpy())

    verdade = np.asarray(verdade)
    destino.mkdir()
    resumo = {}

    for nome, probabilidades in [
        ("sem_tta", simples), ("com_tta", aumentado)
    ]:
        probabilidades = np.asarray(probabilidades)
        previsoes = probabilidades.argmax(axis=1)
        precisao, recall, f1, _ = precision_recall_fscore_support(
            verdade, previsoes,
            labels=range(len(CLASSES)),
            average="macro", zero_division=0,
        )
        matriz = confusion_matrix(
            verdade, previsoes, labels=range(len(CLASSES))
        )
        perda = float(np.mean(
            -np.log(np.clip(
                probabilidades[np.arange(len(verdade)), verdade],
                1e-7, 1,
            ))
        ))

        resumo[nome] = {
            "numero_imagens": len(verdade),
            "acertos": int(np.sum(verdade == previsoes)),
            "acuracia": float(accuracy_score(verdade, previsoes)),
            "macro_precisao": float(precisao),
            "macro_recall": float(recall),
            "macro_f1": float(f1),
            "perda_sem_label_smoothing": perda,
            "matriz_confusao": matriz.tolist(),
            "por_classe": classification_report(
                verdade, previsoes,
                labels=range(len(CLASSES)),
                target_names=CLASSES,
                output_dict=True, zero_division=0,
            ),
        }

        np.savez(
            destino / f"predicoes_{nome}.npz",
            rotulos=verdade, probabilidades=probabilidades,
        )

        fig, eixo = plt.subplots(figsize=(6, 5))
        imagem = eixo.imshow(matriz, cmap="Blues")
        fig.colorbar(imagem, ax=eixo)
        eixo.set(
            xticks=range(len(CLASSES)), yticks=range(len(CLASSES)),
            xticklabels=CLASSES, yticklabels=CLASSES,
            xlabel="Classe prevista", ylabel="Classe real",
            title=f"Matriz de confusão — {nome.replace('_', ' ')}",
        )
        for i in range(len(CLASSES)):
            for j in range(len(CLASSES)):
                eixo.text(
                    j, i, str(matriz[i, j]),
                    ha="center", va="center",
                    color="white" if matriz[i, j] > matriz.max() / 2
                    else "black",
                )
        fig.tight_layout()
        fig.savefig(destino / f"matriz_{nome}.png", dpi=300)
        plt.close(fig)

        print(
            f"{nome}: acurácia={resumo[nome]['acuracia']:.4f}; "
            f"macro F1={f1:.4f}"
        )

    salvar_json(destino / "metricas_teste.json", resumo)
    print("Avaliação salva em:", destino)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--avaliar", action="store_true")
    argumentos = parser.parse_args()

    tf.keras.utils.set_random_seed(SEMENTE)
    configurar_gpu()
    digest = verificar_base()

    if argumentos.avaliar:
        avaliar(digest)
    else:
        treinar(digest)
