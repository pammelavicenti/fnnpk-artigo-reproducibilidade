"""Reproduz decisões sobre percepções fixas; não mede eficácia agronômica."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from agente_visao import Agente


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--entrada', default='entrada_cenario.jsonl')
    p.add_argument('--saida', default='comparacao_resultados.json')
    args = p.parse_args()
    fonte = Path(args.entrada)
    registros = [json.loads(linha) for linha in fonte.read_text(encoding='utf-8').splitlines() if linha.strip()]
    if not registros:
        raise ValueError('Entrada vazia')
    if len({r['analise_id'] for r in registros}) != len(registros):
        raise ValueError('Identificadores repetidos na entrada')
    if len({r['planta_id'] for r in registros}) != 1:
        raise ValueError('Este protocolo compara uma única sequência fictícia')
    agente = Agente(':memory:', janela_horas=24)
    linhas = []
    for passo, r in enumerate(registros, 1):
        observacao = {k: r[k] for k in ('analise_id', 'planta_id', 'captura_hash', 'data_hora', 'modelo', 'origem', 'imagem_valida')}
        for k in ('probabilidades', 'motivo_invalidade', 'imagem_uri'):
            if k in r:
                observacao[k] = r[k]
        obtido = agente.observar(observacao)
        for campo in ('classe_prevista', 'acao', 'estado_atual'):
            if obtido[campo] != r[campo]:
                raise ValueError(f'Decisão reexecutada difere do registro: {r["analise_id"]}, {campo}')
        classe = obtido['classe_prevista']
        if not r['imagem_valida']:
            imediata = 'SOLICITAR_NOVA_CAPTURA'
        elif classe is None:
            imediata = 'ENCAMINHAR_REVISAO'
        elif classe == 'fn':
            imediata = 'REGISTRAR_OBSERVACAO'
        else:
            imediata = 'EMITIR_ALERTA'
        linhas.append({'passo': passo, 'analise_id': r['analise_id'], 'classe_prevista': classe, 'alerta_imediato': imediata, 'agente_com_estado': obtido['acao']})
    agente.db.close()
    politicas = {}
    for nome in ('alerta_imediato', 'agente_com_estado'):
        contagens = Counter(l[nome] for l in linhas)
        politicas[nome] = {'acoes': dict(contagens), 'primeiro_alerta_no_passo': next((l['passo'] for l in linhas if l[nome] == 'EMITIR_ALERTA'), None)}
    resultado = {
        'tipo': 'comparacao_descritiva_em_sequencia_simulada',
        'sha256_entrada': hashlib.sha256(fonte.read_bytes()).hexdigest(),
        'numero_observacoes': len(linhas), 'decisoes_reproduzidas_conferidas': True,
        'baseline': 'Um alerta para cada previsão válida de deficiência, sem memória ou supressão. Entrada inválida solicita captura em ambas as políticas.',
        'politicas': politicas, 'por_observacao': linhas,
        'limites': ['Uma sequência fictícia com quatro imagens do conjunto de validação e um arquivo inválido.', 'Previsões fixas; nenhuma nova inferência ou treinamento.', 'Sem referência longitudinal agronômica; não mede falsos alertas, sensibilidade temporal ou benefício no cultivo.', 'Menos alertas pode incluir adiamento ou ausência de um alerta relevante.', 'Baseline não suprime repetições; não isola o benefício da confirmação do benefício da supressão.', 'Horários atribuídos não são tempos de captura de uma mesma planta; não usar como latência operacional.']
    }
    Path(args.saida).write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding='utf-8')
    for l in linhas:
        print(f'{l["passo"]}: {l["classe_prevista"] or "inválida"} | imediato={l["alerta_imediato"]} | agente={l["agente_com_estado"]}')
    print(json.dumps(politicas, indent=2, ensure_ascii=False))
    print('Decisões do agente reproduzidas e conferidas com os registros originais.')


if __name__ == '__main__':
    main()
