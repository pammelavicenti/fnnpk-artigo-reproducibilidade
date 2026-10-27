"""Modelo C + piloto sintetico. Executar ao lado dos dois scripts originais."""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['PYTHONHASHSEED'] = '321'
import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

CLASSES = ['def_k', 'def_n', 'def_p', 'fn']
EXTENSOES = {'.png', '.jpg', '.jpeg'}

def imagens(pasta):
    return sorted(p for p in pasta.rglob('*') if p.is_file() and p.suffix.lower() in EXTENSOES)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def salvar(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def localizar_piloto(caminho):
    if (caminho / 'manifesto.csv').is_file() and (caminho / 'imagens').is_dir():
        return caminho
    encontrados = [p.parent for p in caminho.rglob('manifesto.csv') if (p.parent / 'imagens').is_dir()]
    if len(encontrados) != 1:
        raise FileNotFoundError(f'Nao encontrei um unico piloto com manifesto.csv e imagens em {caminho}')
    return encontrados[0]

def preparar(base, piloto, saida):
    dados = base / 'divisao_agrupada'
    for particao in ['train', 'val', 'test']:
        for classe in CLASSES:
            if not (dados / particao / classe).is_dir():
                raise FileNotFoundError(dados / particao / classe)
    fontes = {p: {c: imagens(dados / p / c) for c in CLASSES} for p in ['train', 'val', 'test']}
    hashes = {p: {sha(f) for files in fontes[p].values() for f in files} for p in fontes}
    for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]:
        if hashes[a] & hashes[b]:
            raise ValueError(f'Copias exatas entre {a} e {b}; treinamento interrompido.')
    piloto = localizar_piloto(piloto)
    with (piloto / 'manifesto.csv').open(encoding='utf-8-sig', newline='') as f:
        registros = list(csv.DictReader(f))
    treino_nomes = {f.name for files in fontes['train'].values() for f in files}
    aval_nomes = {f.name for p in ['val', 'test'] for files in fontes[p].values() for f in files}
    referencias = {n.strip() for r in registros for n in r['referencias'].split(';') if n.strip()}
    ausentes = referencias - treino_nomes
    conflito = referencias & aval_nomes
    if ausentes or conflito:
        raise ValueError('Referencias precisam estar exclusivamente no treino. '
                         f'Ausentes no treino: {sorted(ausentes)}. '
                         f'Presentes em val/test: {sorted(conflito)}. '
                         'Nao mova imagens entre particoes para resolver: confira a origem das referencias.')
    entradas = []
    usados = set()
    for r in registros:
        c = r['classe_pretendida']
        if c not in CLASSES:
            raise ValueError(f'Classe desconhecida: {c}')
        p = (piloto / r['arquivo']).resolve()
        if not p.is_relative_to(piloto.resolve()) or not p.is_file():
            raise ValueError(f'Caminho de imagem invalido: {p}')
        h = sha(p)
        if h != r['sha256']:
            raise ValueError(f'Imagem alterada desde o manifesto: {p.name}')
        if h in usados or any(h in v for v in hashes.values()):
            raise ValueError(f'Imagem sintetica duplicada: {p.name}')
        usados.add(h)
        entradas.append((p, c, r))
    if len(entradas) != 20 or any(sum(c == cl for _, c, _ in entradas) != 5 for cl in CLASSES):
        raise ValueError('Este experimento foi definido para 20 sinteticas, cinco por classe.')
    # Todos os controles acima sao executados antes de criar a nova pasta.
    saida.mkdir(parents=True, exist_ok=False)
    novo_treino = saida / 'treino_com_sinteticas'
    auditoria = []
    for c in CLASSES:
        (novo_treino / c).mkdir(parents=True)
        for p in fontes['train'][c]:
            destino = novo_treino / c / ('original_' + p.name)
            if destino.exists():
                raise ValueError(f'Nome de arquivo repetido no treino: {p.name}')
            shutil.copyfile(p, destino)
            auditoria.append({'arquivo': str(destino.relative_to(saida)), 'classe': c,
                             'origem': 'base_publica', 'sha256': sha(destino)})
    for p, c, r in entradas:
        destino = novo_treino / c / p.name
        if destino.exists():
            raise ValueError(f'Colisao de nome: {p.name}')
        shutil.copyfile(p, destino)
        auditoria.append({'arquivo': str(destino.relative_to(saida)), 'classe': c,
                         'origem': 'sintetica', 'sha256': sha(destino),
                         'referencias': r['referencias'], 'revisao_agronomica': r['revisao_agronomica']})
    contagens = {c: len(fontes['train'][c]) for c in CLASSES}
    salvar(saida / 'auditoria_dados.json', {
        'treino_base_publica': contagens,
        'treino_sinteticas': {c: 5 for c in CLASSES},
        'treino_total': {c: contagens[c] + 5 for c in CLASSES},
        'val': {c: len(fontes['val'][c]) for c in CLASSES},
        'test': {c: len(fontes['test'][c]) for c in CLASSES},
        'referencias_conferidas_no_treino_por_nome': sorted(referencias),
        'limite_auditoria': 'Nomes nao comprovam identidade de planta nem independencia biologica.',
        'hashes_val': sorted(hashes['val']), 'hashes_test': sorted(hashes['test']),
        'arquivos_treino': auditoria, 'carater': 'exploratorio; sinteticas sem revisao agronomica',
    })
    shutil.copyfile(piloto / 'manifesto.csv', saida / 'manifesto_sinteticas.csv')
    shutil.copyfile(Path(__file__), saida / 'script_executado.py')
    print('\nClasse    Base   Sinteticas   Treino final')
    for c in CLASSES:
        print(f'{c:8s} {contagens[c]:5d} {5:12d} {contagens[c]+5:14d}')
    print('Validacao e teste permanecem nos caminhos originais.')
    return dados, novo_treino, contagens

def treinar(base, dados, novo_treino, contagens, saida):
    import numpy as np
    import tensorflow as tf
    import comparar_treinamentos as c
    import treinar_alface as original
    if list(original.CLASSES) != CLASSES:
        raise ValueError(f'Ordem de classes divergente: {original.CLASSES}')
    if Path(original.DADOS).resolve() != dados.resolve():
        raise ValueError(f'O script original usa outra divisao: {original.DADOS}')
    original.configurar_gpu()
    digest = original.verificar_base()
    # Usa os mesmos carregadores dos treinamentos anteriores.
    validacao = original.carregar('val')
    baseline = base / 'comparacao_validacao_seed321' / 'C_ajuste_maior'
    anterior = tf.keras.models.load_model(baseline / 'modelo_selecionado.keras', compile=False)
    resultado_base = c.relatorio(anterior, validacao)
    resultado_registrado = json.loads((baseline / 'validacao.json').read_text(encoding='utf-8'))
    for metrica in ['acuracia', 'macro_f1', 'perda_sem_smoothing']:
        if not np.isclose(resultado_base[metrica], resultado_registrado[metrica], atol=1e-5, rtol=1e-4):
            raise ValueError(f'Validacao do modelo C nao reproduziu {metrica}; confira dados/modelo antes de comparar.')
    salvar(saida / 'validacao_baseline_C.json', resultado_base)
    del anterior
    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(321)
    # Redireciona somente a leitura do treino, temporariamente.
    # val/test continuam com os caminhos usados pelo script original.
    caminho_original = original.DADOS
    try:
        original.DADOS = novo_treino.parent / '_carregamento_treino'
        original.DADOS.mkdir()
        (original.DADOS / 'train').symlink_to(novo_treino, target_is_directory=True)
        treino = original.carregar('train', treinamento=True)
        lotes = int(tf.data.experimental.cardinality(treino).numpy())
        esperados = (sum(contagens.values()) + 20 + 7) // 8
        if lotes != esperados:
            raise ValueError(f'Carregamento do treino nao confirmou batch 8 e as sinteticas: '
                             f'{lotes} lotes encontrados; {esperados} esperados.')
    finally:
        original.DADOS = caminho_original
    total = sum(contagens.values())
    frequencias = np.array([contagens[k] for k in CLASSES])
    pesos = (total / (len(CLASSES) * frequencias)) ** 0.5
    pesos /= np.sum(pesos * frequencias) / total
    pesos = {i: float(w) for i, w in enumerate(pesos)}
    config = {
        'experimento': 'C_com_20_sinteticas', 'carater': 'exploratorio',
        'semente': 321, 'sha256_manifesto_original': digest, 'classes': CLASSES,
        'epocas_maximas_inicial': 30, 'epocas_maximas_ajuste': 20,
        'taxa_inicial': 1e-3, 'taxa_ajuste': 2e-5,
        'weight_decay_inicial': 1e-4, 'weight_decay_ajuste': 1e-5,
        'expoente_pesos': 0.5, 'pesos_classes': pesos,
        'politica_pesos': 'fixos, calculados sobre contagens do treino da base publica, iguais a C',
        'dropout': 0.35, 'label_smoothing': 0.05, 'mixup': False,
        'batch_size': 8, 'lotes_treino': lotes,
        'tensorflow': tf.__version__, 'criterio_selecao': 'macro F1; desempate por perda sem smoothing',
        'teste_avaliado': False, 'revisao_agronomica_sinteticas': 'pendente',
    }
    salvar(saida / 'configuracao.json', config)
    for nome in ['comparar_treinamentos.py', 'treinar_alface.py']:
        shutil.copyfile(base / nome, saida / nome)
    modelo, rede = c.construir_modelo()
    selecao = c.SelecaoValidacao(validacao)
    c.compilar(modelo, 1e-3, 1e-4)
    modelo.fit(treino, validation_data=validacao, epochs=30, class_weight=pesos,
               callbacks=c.callbacks(selecao, saida, 'inicial'), verbose=2)
    if selecao.melhores_pesos is None:
        raise RuntimeError('Nenhuma epoca valida foi selecionada na fase inicial.')
    modelo.set_weights(selecao.melhores_pesos)
    rede.trainable = True
    for indice, camada in enumerate(rede.layers):
        camada.trainable = indice >= 210 and not isinstance(camada, tf.keras.layers.BatchNormalization)
    selecao.fase = 'ajuste'
    c.compilar(modelo, 2e-5, 1e-5)
    modelo.fit(treino, validation_data=validacao, epochs=20, class_weight=pesos,
               callbacks=c.callbacks(selecao, saida, 'ajuste'), verbose=2)
    modelo.set_weights(selecao.melhores_pesos)
    modelo.save(saida / 'modelo_selecionado.keras')
    salvar(saida / 'validacao.json', selecao.melhor_relatorio)
    salvar(saida / 'historico_selecao.json', selecao.historico)
    salvar(saida / 'comparacao_validacao.json', {
        'baseline_C': resultado_base, 'C_com_sinteticas': selecao.melhor_relatorio,
        'diferenca_macro_f1': selecao.melhor_relatorio['macro_f1'] - resultado_base['macro_f1'],
        'teste_avaliado': False, 'conclusao': 'Comparacao exploratoria em validacao pequena.',
    })
    for nome, r in [('C original', resultado_base), ('C + sinteticas', selecao.melhor_relatorio)]:
        print(f"{nome}: acuracia={r['acuracia']:.4f}; macro F1={r['macro_f1']:.4f}")
    print('Resultados:', saida)
    print('Nenhuma inferencia foi realizada no conjunto de teste.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--sinteticas', type=Path)
    parser.add_argument('--preparar-apenas', action='store_true')
    args = parser.parse_args()
    base = args.base.resolve()
    piloto = args.sinteticas or base.parent / 'FNNPK_sintetico_piloto'
    saida = base / ('C_sinteticas_seed321_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    dados, treino, contagens = preparar(base, piloto.resolve(), saida)
    if args.preparar_apenas:
        print('Preparacao concluida, sem treinamento. Pasta:', saida)
    else:
        treinar(base, dados, treino, contagens, saida)
