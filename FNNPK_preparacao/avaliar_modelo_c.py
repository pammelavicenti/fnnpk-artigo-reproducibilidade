import json
import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

import treinar_alface as original

PASTA = (
    original.BASE
    / "comparacao_validacao_seed321"
    / "C_ajuste_maior"
)
SAIDA = PASTA / "avaliacao_exploratoria_teste"

if SAIDA.exists():
    raise FileExistsError(
        "A avaliação já existe. Nenhum resultado será sobrescrito."
    )

original.configurar_gpu()
digest = original.verificar_base()

configuracao = json.loads(
    (PASTA / "configuracao.json").read_text(encoding="utf-8")
)
if configuracao["sha256_manifesto"] != digest:
    raise ValueError("A divisão mudou após o treinamento.")

modelo = tf.keras.models.load_model(
    PASTA / "modelo_selecionado.keras", compile=False
)
teste = original.carregar("test")

reais, sem_tta, com_tta = [], [], []

for imagens, rotulos in teste:
    reais.extend(np.argmax(rotulos.numpy(), axis=1))
    sem_tta.extend(modelo(imagens, training=False).numpy())
    com_tta.extend(original.predizer_tta(modelo, imagens).numpy())

reais = np.asarray(reais)
resumo = {
    "modelo": "C_ajuste_maior",
    "natureza_avaliacao": "exploratoria_em_teste_previamente_consultado",
    "classes": original.CLASSES,
}

SAIDA.mkdir()

for nome, probabilidades in [
    ("sem_tta", sem_tta), ("com_tta", com_tta)
]:
    probabilidades = np.asarray(probabilidades)
    previstas = probabilidades.argmax(axis=1)

    precisao, recall, f1, _ = precision_recall_fscore_support(
        reais, previstas,
        labels=range(len(original.CLASSES)),
        average="macro", zero_division=0,
    )
    acertos = int(np.sum(reais == previstas))

    resumo[nome] = {
        "numero_imagens": len(reais),
        "acertos": acertos,
        "acuracia": float(np.mean(reais == previstas)),
        "macro_precisao": float(precisao),
        "macro_recall": float(recall),
        "macro_f1": float(f1),
        "perda_sem_label_smoothing": float(np.mean(-np.log(
            np.clip(
                probabilidades[np.arange(len(reais)), reais],
                1e-7, 1,
            )
        ))),
        "matriz_confusao": confusion_matrix(
            reais, previstas,
            labels=range(len(original.CLASSES)),
        ).tolist(),
        "por_classe": classification_report(
            reais, previstas,
            labels=range(len(original.CLASSES)),
            target_names=original.CLASSES,
            output_dict=True, zero_division=0,
        ),
    }

    np.savez(
        SAIDA / f"predicoes_{nome}.npz",
        rotulos=reais, probabilidades=probabilidades,
    )

    print(
        f"{nome}: {acertos}/{len(reais)} acertos; "
        f"acurácia={resumo[nome]['acuracia']:.4f}; "
        f"macro F1={f1:.4f}"
    )

original.salvar_json(SAIDA / "metricas_modelo_c.json", resumo)
print("Resultados:", SAIDA)