"""Seis execucoes predefinidas do modelo C. Comparacao exploratoria na validacao."""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import argparse
import csv
import hashlib
import json
import shutil
import statistics
from datetime import datetime
from pathlib import Path

SEMENTES = [123, 321, 456]
CONDICOES = ['C_original', 'C_V2']

def salvar(p, dados):
    p.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding='utf-8')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def construir_modelo(tf, classes, semente):
    aumento = tf.keras.Sequential([
        tf.keras.layers.RandomFlip('horizontal', seed=semente),
        tf.keras.layers.RandomRotation(0.05, seed=semente + 1),
        tf.keras.layers.RandomZoom(0.10, seed=semente + 2),
        tf.keras.layers.RandomContrast(0.10, seed=semente + 3),
        tf.keras.layers.RandomBrightness(0.05, value_range=(0, 255), seed=semente + 4),
    ], name='augmentation_moderado')
    rede = tf.keras.applications.EfficientNetB0(
        include_top=False, weights='imagenet', input_shape=(224, 224, 3))
    rede.trainable = False
    entrada = tf.keras.Input((224, 224, 3))
    x = aumento(entrada)
    x = rede(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.35, seed=semente + 5)(x)
    saida = tf.keras.layers.Dense(len(classes), activation='softmax')(x)
    return tf.keras.Model(entrada, saida), rede

def resumir(raiz, linhas):
    resumo = {}
    for condicao in CONDICOES:
        grupo = [r for r in linhas if r['condicao'] == condicao]
        r = {'execucoes_concluidas': len(grupo)}
        for metrica in ['acuracia', 'macro_f1', 'perda_sem_smoothing']:
            valores = [x[metrica] for x in grupo]
            r[metrica + '_media'] = statistics.mean(valores) if valores else None
            r[metrica + '_desvio_padrao_amostral'] = statistics.stdev(valores) if len(valores) > 1 else None
        resumo[condicao] = r
    pares = []
    for s in SEMENTES:
        g = {r['condicao']: r for r in linhas if r['semente'] == s}
        if len(g) == 2:
            pares.append({'semente': s, 'diferenca_macro_f1_V2_menos_original':
                          g['C_V2']['macro_f1'] - g['C_original']['macro_f1']})
    valores = [p['diferenca_macro_f1_V2_menos_original'] for p in pares]
    resumo['diferencas_pareadas'] = pares
    resumo['diferenca_macro_f1_media'] = statistics.mean(valores) if valores else None
    resumo['carater'] = 'exploratorio; validacao pequena e ja usada no desenvolvimento'
    resumo['teste_avaliado'] = False
    salvar(raiz / 'resumo_sementes.json', resumo)
    with (raiz / 'resultados_sementes.csv').open('w', encoding='utf-8-sig', newline='') as f:
        campos = ['condicao', 'semente', 'acuracia', 'macro_f1', 'perda_sem_smoothing',
                  'fase_selecionada', 'epoca_selecionada']
        w = csv.DictWriter(f, campos, extrasaction='ignore'); w.writeheader(); w.writerows(linhas)
    return resumo

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sinteticas', type=Path)
    parser.add_argument('--retomar', type=Path, help='Pasta desta comparacao interrompida; repete execucao parcial do inicio')
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    import treinar_com_sinteticas as preparo
    piloto = preparo.localizar_piloto((args.sinteticas or base.parent / 'FNNPK_sintetico_v2').resolve())
    import numpy as np
    import tensorflow as tf
    import comparar_treinamentos as c
    import treinar_alface as original
    classes = list(original.CLASSES)
    if classes != preparo.CLASSES:
        raise ValueError('Ordem das classes divergente.')
    if Path(original.DADOS).resolve() != (base / 'divisao_agrupada').resolve():
        raise ValueError('A divisao original aponta para outra pasta.')
    original.configurar_gpu()
    digest = original.verificar_base()
    protocolo = {
        'sementes': SEMENTES, 'condicoes': CONDICOES, 'classes': classes,
        'sha256_manifesto_original': digest, 'sha256_manifesto_V2': sha(piloto / 'manifesto.csv'),
        'fontes_sha256': {nome: sha(base / nome) for nome in
                         ['comparar_sementes.py', 'comparar_treinamentos.py', 'treinar_alface.py', 'treinar_com_sinteticas.py']},
        'tensorflow': tf.__version__, 'semente_particionamento': 123,
        'criterio_selecao': 'maior macro F1 na validacao; desempate por menor perda sem smoothing',
        'epocas_maximas_inicial': 30, 'epocas_maximas_ajuste': 20,
        'taxa_inicial': 1e-3, 'taxa_ajuste': 2e-5,
        'weight_decay_inicial': 1e-4, 'weight_decay_ajuste': 1e-5,
        'pesos': 'mesmos nas duas condicoes, calculados sobre o treino da base publica; expoente 0.5',
        'escopo_sementes': 'inicializacao, RNG global do treinamento e camadas de augmentation/dropout',
        'carregamento': 'mesmo original.carregar; parametros internos de embaralhamento preservados',
        'teste_avaliado': False, 'revisao_agronomica_sinteticas': 'pendente',
    }
    if args.retomar:
        raiz = args.retomar.resolve()
        anterior = json.loads((raiz / 'protocolo.json').read_text(encoding='utf-8'))
        if anterior != protocolo:
            raise ValueError('Dados, ambiente ou scripts mudaram; nao e possivel retomar a mesma comparacao.')
        dados = base / 'divisao_agrupada'
        novo_treino = raiz / 'treino_com_sinteticas'
        audit = json.loads((raiz / 'auditoria_dados.json').read_text(encoding='utf-8'))
        contagens = audit['treino_base_publica']
        for registro in audit['arquivos_treino']:
            if sha(raiz / registro['arquivo']) != registro['sha256']:
                raise ValueError('A copia do treino foi alterada.')
    else:
        raiz = base / ('comparacao_sementes_C_V2_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        dados, novo_treino, contagens = preparo.preparar(base, piloto, raiz)
        salvar(raiz / 'protocolo.json', protocolo)
        for nome in protocolo['fontes_sha256']:
            shutil.copyfile(base / nome, raiz / nome)
    total = sum(contagens.values())
    frequencias = np.array([contagens[k] for k in classes])
    pesos = (total / (len(classes) * frequencias)) ** 0.5
    pesos /= np.sum(pesos * frequencias) / total
    pesos = {i: float(w) for i, w in enumerate(pesos)}
    print('Comparacao:', raiz, flush=True)
    print('Seis execucoes: 3 sementes x 2 condicoes. Sem avaliacao do teste.', flush=True)
    linhas = []
    for semente in SEMENTES:
        for condicao in CONDICOES:
            pasta = raiz / f'{condicao}_seed{semente}'
            conclusao = pasta / 'validacao.json'
            if conclusao.is_file() and (pasta / 'modelo_selecionado.keras').is_file():
                resultado = json.loads(conclusao.read_text(encoding='utf-8'))
                print(f'Reutilizando execucao concluida: {pasta.name}', flush=True)
            else:
                pasta.mkdir(exist_ok=True)
                tf.keras.backend.clear_session()
                tf.keras.utils.set_random_seed(semente)
                validacao = original.carregar('val')
                if condicao == 'C_original':
                    treino = original.carregar('train', treinamento=True)
                    quantidade = total
                else:
                    caminho_original = original.DADOS
                    temporario = raiz / '_carregamento_treino'
                    temporario.mkdir(exist_ok=True)
                    link = temporario / 'train'
                    if not link.exists(): link.symlink_to(novo_treino, target_is_directory=True)
                    try:
                        original.DADOS = temporario
                        treino = original.carregar('train', treinamento=True)
                    finally:
                        original.DADOS = caminho_original
                    quantidade = total + 20
                lotes = int(tf.data.experimental.cardinality(treino).numpy())
                if lotes != (quantidade + 7) // 8:
                    raise ValueError('Contagem de lotes nao corresponde a batch 8 e ao treino esperado.')
                salvar(pasta / 'configuracao.json', {'condicao': condicao, 'semente': semente,
                       'imagens_treino': quantidade, 'pesos_classes': pesos, 'batch_size': 8, **protocolo})
                print(f'\n=== {condicao}, semente {semente} ===', flush=True)
                modelo, rede = construir_modelo(tf, classes, semente)
                selecao = c.SelecaoValidacao(validacao)
                c.compilar(modelo, 1e-3, 1e-4)
                modelo.fit(treino, validation_data=validacao, epochs=30, class_weight=pesos,
                           callbacks=c.callbacks(selecao, pasta, 'inicial'), verbose=2)
                if selecao.melhores_pesos is None:
                    raise RuntimeError('Nenhuma epoca valida foi selecionada.')
                modelo.set_weights(selecao.melhores_pesos)
                rede.trainable = True
                for indice, camada in enumerate(rede.layers):
                    camada.trainable = indice >= 210 and not isinstance(camada, tf.keras.layers.BatchNormalization)
                selecao.fase = 'ajuste'
                c.compilar(modelo, 2e-5, 1e-5)
                modelo.fit(treino, validation_data=validacao, epochs=20, class_weight=pesos,
                           callbacks=c.callbacks(selecao, pasta, 'ajuste'), verbose=2)
                modelo.set_weights(selecao.melhores_pesos)
                modelo.save(pasta / 'modelo_selecionado.keras')
                resultado = selecao.melhor_relatorio
                salvar(pasta / 'historico_selecao.json', selecao.historico)
                salvar(conclusao, resultado)
                del modelo, rede, selecao
            linhas.append({'condicao': condicao, 'semente': semente, **resultado})
            resumo = resumir(raiz, linhas)
    print('\n=== MEDIA E DESVIO PADRAO NA VALIDACAO ===')
    for condicao in CONDICOES:
        r = resumo[condicao]
        print(f"{condicao}: macro F1={r['macro_f1_media']:.4f} +/- "
              f"{r['macro_f1_desvio_padrao_amostral']:.4f}; "
              f"acuracia={r['acuracia_media']:.4f} +/- {r['acuracia_desvio_padrao_amostral']:.4f}")
    print('Diferenca media de macro F1 (V2 - original):', resumo['diferenca_macro_f1_media'])
    print('Resumo:', raiz / 'resumo_sementes.json')
    print('Nenhum modelo foi escolhido pelo resultado no teste.')

if __name__ == '__main__':
    main()
