"""Avalia o modelo C + sinteticas no teste ja consultado: avaliacao exploratoria."""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['PYTHONHASHSEED'] = '321'
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix
import treinar_alface as original


def salvar(p, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')


def metricas(reais, probs, classes):
    previstas = probs.argmax(axis=1)
    rel = classification_report(reais, previstas, labels=list(range(len(classes))),
                                target_names=classes, output_dict=True, zero_division=0)
    perda = float(np.mean(-np.log(np.clip(probs[np.arange(len(reais)), reais], 1e-7, 1))))
    return {'acertos': int(np.sum(reais == previstas)), 'total': len(reais),
            'acuracia': float(np.mean(reais == previstas)),
            'macro_precisao': float(rel['macro avg']['precision']),
            'macro_revocacao': float(rel['macro avg']['recall']),
            'macro_f1': float(rel['macro avg']['f1-score']),
            'perda_sem_smoothing': perda,
            'matriz_confusao': confusion_matrix(reais, previstas, labels=list(range(len(classes)))).tolist(),
            'por_classe': rel}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pasta', type=Path, help='Pasta do treinamento C com sinteticas')
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    if args.pasta:
        pasta = args.pasta.resolve()
    else:
        completas = sorted(p for p in base.glob('C_sinteticas_seed321_*')
                           if (p / 'comparacao_validacao.json').is_file()
                           and (p / 'modelo_selecionado.keras').is_file())
        if not completas:
            raise FileNotFoundError('Nao encontrei treinamento concluido. Informe --pasta.')
        pasta = completas[-1]
    modelo_path = pasta / 'modelo_selecionado.keras'
    if not modelo_path.is_file():
        raise FileNotFoundError(modelo_path)
    classes = list(original.CLASSES)
    config = json.loads((pasta / 'configuracao.json').read_text(encoding='utf-8'))
    if config['classes'] != classes:
        raise ValueError('Ordem de classes diferente daquela usada no treinamento.')
    original.configurar_gpu()
    original.verificar_base()
    tf.keras.utils.set_random_seed(321)
    teste = original.carregar('test')
    modelo = tf.keras.models.load_model(modelo_path, compile=False)
    print('Modelo avaliado:', modelo_path)
    reais, sem, com = [], [], []
    for imagens, rotulos in teste:
        imagens = tf.cast(imagens, tf.float32)
        p0 = modelo(imagens, training=False).numpy()
        # Cinco versoes: original, flip horizontal, flip vertical,
        # brilho +0,08*255 e contraste 1,1. Media das probabilidades.
        variacoes = [tf.image.flip_left_right(imagens),
                     tf.image.flip_up_down(imagens),
                     tf.clip_by_value(imagens + 0.08 * 255.0, 0.0, 255.0),
                     tf.clip_by_value(tf.image.adjust_contrast(imagens, 1.1), 0.0, 255.0)]
        probabilidades = [p0] + [modelo(v, training=False).numpy() for v in variacoes]
        reais.extend(np.argmax(rotulos.numpy(), axis=1).tolist())
        sem.extend(p0)
        com.extend(np.mean(probabilidades, axis=0))
    reais = np.asarray(reais, dtype=int)
    sem, com = np.asarray(sem), np.asarray(com)
    if len(reais) != 31:
        raise ValueError(f'O teste esperado tem 31 imagens; foram encontradas {len(reais)}.')
    for probs in [sem, com]:
        if not np.isfinite(probs).all() or not np.allclose(probs.sum(axis=1), 1.0, atol=1e-4):
            raise ValueError('Probabilidades invalidas.')
    resultados = {'sem_tta': metricas(reais, sem, classes),
                  'com_tta': metricas(reais, com, classes)}
    saida = pasta / ('avaliacao_exploratoria_teste_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    saida.mkdir(exist_ok=False)
    salvar(saida / 'metricas_teste_sinteticas.json', {
        'modelo': str(modelo_path), 'classes': classes,
        'carater': 'exploratorio: conjunto de teste consultado anteriormente',
        'origem_treino': '141 imagens da base publica e 20 sinteticas com revisao agronomica pendente',
        'tta': {'numero_versoes': 5, 'agregacao': 'media das probabilidades',
                'versoes': ['original', 'flip_horizontal', 'flip_vertical', 'brilho_mais_20.4', 'contraste_1.1']},
        **resultados,
    })
    # Indices identificam a ordem de iteracao; nao representam IDs de plantas.
    with (saida / 'predicoes.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['indice_iteracao', 'classe_base', 'previsao_sem_tta', 'previsao_com_tta']
                   + ['prob_sem_' + c for c in classes] + ['prob_tta_' + c for c in classes])
        for i, y in enumerate(reais):
            w.writerow([i, classes[y], classes[sem[i].argmax()], classes[com[i].argmax()]]
                       + sem[i].tolist() + com[i].tolist())
    np.savez_compressed(saida / 'probabilidades.npz', classes=np.asarray(classes),
                        rotulos=reais, sem_tta=sem, com_tta=com)
    for modo, r in resultados.items():
        with (saida / f'matriz_confusao_{modo}.csv').open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f); w.writerow(['real / prevista'] + classes)
            for c, linha in zip(classes, r['matriz_confusao']): w.writerow([c] + linha)
        print(f"{modo}: {r['acertos']}/{r['total']} acertos; "
              f"acuracia={r['acuracia']:.4f}; macro F1={r['macro_f1']:.4f}")
        print('Matriz (linhas reais, colunas previstas):', r['matriz_confusao'])
    print('Resultados:', saida)
    print('Avaliacao exploratoria; o modelo nao foi retreinado nem selecionado por estes resultados.')


if __name__ == '__main__':
    main()
