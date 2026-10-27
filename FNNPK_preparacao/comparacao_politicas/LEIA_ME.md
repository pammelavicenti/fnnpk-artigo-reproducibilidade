# Comparação descritiva das políticas

Esta análise usa a sequência já executada por a autora, sem novas inferências. As cinco observações são quatro imagens distintas da validação (três def_k e uma def_n) e um arquivo inválido, associados a uma planta fictícia. Não são capturas longitudinais confirmadas de uma planta real.

## Reproduzir

Na pasta extraída, usando Python:

```bash
python comparar_politicas.py --entrada entrada_cenario.jsonl --saida comparacao_resultados.json
```

Não exige TensorFlow ou Redis: as percepções estão fixadas no arquivo. O módulo agente_visao.py contém a política original, usada em banco temporário em memória. A parte de percepção desse módulo não é chamada. O script verifica classe, ação e estado final de cada observação contra o registro original; divergências interrompem a execução.

## Protocolo

A política de referência emite um alerta para cada previsão válida de deficiência. Não mantém histórico e não suprime repetições. Para arquivo inválido, solicita nova captura. A política do agente exige concordância de duas observações com conteúdo distinto dentro de 24 horas, registra a persistência sem repetir alerta e gera decisão de revisão quando há divergência. A janela é um parâmetro operacional provisório.

Os dois métodos recebem as mesmas percepções, na ordem do arquivo. Os registros originais permanecem preservados. O JSON de resultados inclui o hash SHA-256 da entrada.

## Resultados

| Observação | Previsão | Referência imediata | Agente com estado |
|---|---|---|---|
| 1 | def_k | Alerta | Solicitar captura |
| 2 | def_k | Alerta | Alerta |
| 3 | def_k | Alerta | Registrar observação |
| 4 | def_n | Alerta | Revisão |
| 5 | Arquivo inválido | Solicitar captura | Solicitar captura |

| Indicador | Referência imediata | Agente com estado |
|---|---:|---:|
| Alertas | 4 | 1 |
| Solicitações de captura | 1 | 2 |
| Decisões de revisão | 0 | 1 |
| Registros sem alerta como ação principal | 0 | 1 |
| Observação do primeiro alerta | 1 | 2 |

Todas as observações são registradas pelo agente; a linha de registro sem alerta contabiliza somente a ação principal REGISTRAR_OBSERVACAO. Solicitações e revisões são decisões informacionais, sem câmera ou interface humana integradas.

## Texto para metodologia

Realizou-se uma comparação descritiva entre a política de decisão baseada em estado e uma referência que emite um alerta a cada previsão válida de deficiência, sem histórico ou supressão de repetições. Ambas receberam as mesmas percepções previamente registradas em uma sequência simulada de cinco observações. A sequência compreendeu quatro imagens do conjunto de validação associadas a um identificador fictício de planta e um arquivo inválido. As decisões do agente foram reexecutadas e verificadas contra os registros originais. Foram contabilizados alertas, solicitações de captura, decisões de revisão e a posição do primeiro alerta na sequência.

## Texto para resultados e discussão

A referência imediata gerou quatro alertas e uma solicitação de captura. A política baseada em estado gerou um alerta, duas solicitações de captura, uma decisão de revisão e um registro de persistência sem novo alerta. O primeiro alerta ocorreu na primeira observação para a referência e na segunda para o agente, em razão da exigência de concordância. A previsão divergente foi encaminhada informacionalmente para revisão pelo agente, enquanto a referência gerou um alerta adicional. As cinco decisões reexecutadas coincidiram com os registros originais. Esses resultados descrevem a diferença operacional entre as políticas na sequência examinada, sem demonstrar redução de falsos alertas ou superioridade agronômica.

## Limites da interpretação

- É uma única sequência construída para testes funcionais; não há repetições independentes ou inferência estatística.
- Não há condição nutricional longitudinal confirmada para a planta fictícia.
- Menor número de alertas não significa maior qualidade: pode adiar ou deixar de emitir um alerta relevante.
- A referência não suprime repetições; a comparação não isola a contribuição da confirmação da contribuição da supressão. Uma comparação adicional com alerta imediato e supressão seria necessária para esse fim.
- Não calcular taxa de falsos alertas, acurácia do agente ou ganho de sensibilidade com esses dados.
- Não interpretar os horários atribuídos como latência de captura ou de resposta no cultivo.
- A política não melhora os valores de saída do classificador.

O próximo estudo deve fixar cenários e métricas antes da execução e incluir sequências independentes. Uma avaliação temporal agronômica requer capturas da mesma planta, identidade rastreável e referência confiável da condição nutricional.
