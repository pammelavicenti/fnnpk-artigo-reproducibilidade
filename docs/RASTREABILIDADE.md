# Matriz de rastreabilidade científica

Esta matriz liga afirmações documentadas aos arquivos que as sustentam. A
classificação evita confundir desempenho de classificador, teste funcional e
simulação com validação agronômica.

| Afirmação ou experimento | Classificação | Arquivo de origem | Evidência disponível | Como verificar | Limitação |
| --- | --- | --- | --- | --- | --- |
| Base preparada com 203 imagens (`def_k`: 68, `def_n`: 57, `def_p`: 66, `fn`: 12) | Preparação | `FNNPK_preparacao/manifesto.csv` | nomes, classes e SHA-256 | contar linhas e classes | dataset, fonte e licença não distribuídos/comprovados |
| Cinco cópias exatas identificadas | Preparação | `FNNPK_preparacao/copias_identicas.csv` | pares mantido/removido e hashes | comparar SHA-256 registrados | não detecta imagens diferentes da mesma planta |
| Divisão com 141 imagens de treino, 31 de validação e 31 de teste | Preparação | `FNNPK_preparacao/divisao_agrupada/manifesto_divisao.csv` | partição, classe, grupo e hash | contar por `particao` e `classe` | grupos visuais não provam independência biológica |
| Treinamento EfficientNetB0, semente 321 | Treinamento | `FNNPK_preparacao/resultado_divisao_agrupada_seed321/configuracao.json`, `historico_*.csv` | hiperparâmetros, versões e curvas | inspecionar configuração e históricos | dados, pesos e modelo ausentes |
| Ajuste escolhido por `val_loss` 0,62554 contra 0,64963 | Validação/seleção | `FNNPK_preparacao/resultado_divisao_agrupada_seed321/selecao_validacao.json` | perdas e épocas executadas | ler o JSON | validação pequena e usada no desenvolvimento |
| Consulta inicial: 22/31 acertos sem TTA e 23/31 com TTA | Teste exploratório | `FNNPK_preparacao/resultado_divisao_agrupada_seed321/avaliacao_teste/metricas_teste.json` | métricas, matrizes e NPZ | ler JSON; NPZ preserva rótulos/probabilidades | teste reutilizado; não independente |
| Configuração C atingiu macro F1 0,9103 e acurácia 0,9355 na validação | Validação/seleção | `FNNPK_preparacao/comparacao_validacao_seed321/resumo_validacao.json` | comparação A/B/C | ler JSON | 31 amostras; orientou a escolha do modelo |
| Modelo C registrou 27/31 e macro F1 0,8254 no teste | Teste exploratório | `FNNPK_preparacao/comparacao_validacao_seed321/C_ajuste_maior/avaliacao_exploratoria_teste/metricas_modelo_c.json` | métricas sem/com TTA | ler JSON e NPZ | teste já consultado |
| Primeiro treino com 20 sintéticas registrou macro F1 0,9368 contra 0,9103 na validação | Validação exploratória | `FNNPK_preparacao/C_sinteticas_seed321_20261003_141443_299491/comparacao_validacao.json` | diferença registrada | ler JSON | sintéticas com revisão agronômica pendente |
| Segundo treino sintético registrou macro F1 0,9103, igual ao baseline | Validação exploratória | `FNNPK_preparacao/C_sinteticas_seed321_20261003_144154_562244/comparacao_validacao.json` | diferença igual a zero | ler JSON | mesma validação pequena |
| Comparação de sementes: macro F1 médio 0,9534 nas duas condições | Validação exploratória | `FNNPK_preparacao/comparacao_sementes_C_V2_20261003_145537_730403/resultados_sementes.csv`, `resumo_sementes.json` | seis execuções e estatísticas descritivas | recalcular a partir do CSV | somente três sementes; validação já usada |
| Modelo com sintéticas registrou 26/31 e macro F1 0,7960 | Teste exploratório | `FNNPK_preparacao/C_sinteticas_seed321_20261003_141443_299491/avaliacao_exploratoria_teste_20261003_142503_512736/metricas_teste_sinteticas.json` | métricas, matrizes, CSV e NPZ | ler arquivos estruturados | teste já consultado e sintéticas sem revisão concluída |
| Recorte com ISNet e fundo RGB 200 | Pré-processamento exploratório | `FNNPK_preparacao/recorte_*/protocolo.json`, `manifesto_recorte.csv` | versões, hash do script e manifestos | conferir os protocolos | imagens excluídas e revisão visual pendente |
| Doze testes cobrem o núcleo do agente | Teste funcional de software | `FNNPK_preparacao/agente_visao_v1/test_agente.py` | casos de estado, idempotência, erro e publicação simulada | `python scripts/verificar_reproducibilidade.py` | não testa modelo, Redis real ou validade agronômica |
| Simulação do agente produz decisões persistidas | Simulação funcional | `cenarios_demo.jsonl`, `resultados_demo.jsonl`, `agente_visao.py` | percepções e decisões por linha | executar com banco temporário | nenhuma inferência real |
| Referência imediata gera quatro alertas e agente gera um | Simulação descritiva | `FNNPK_preparacao/comparacao_politicas/entrada_cenario.jsonl`, `comparacao_resultados.json` | cinco decisões conferidas | executar verificador central | não mede falsos positivos, benefício ou latência real |
| Estado sobrevive a reinício e publicação pendente pode ser retomada | Teste funcional de software | `agente_visao.py`, `test_agente.py` | SQLite real e publicador simulado | executar testes | servidor Redis real não verificado |

## Observação sobre o hash da comparação

O `sha256_entrada` preservado em `comparacao_resultados.json` é
`54c4a63d441726f5a6bdab8897e76c5d0300501a01915f9451f170d1e8c39195`, mas a
cópia publicada de `entrada_cenario.jsonl` possui outro hash. A entrada passou
por sanitização de caminhos durante a preparação do repositório e o resultado
histórico não foi recalculado. A verificação automatizada confirma que todas as
decisões e os demais campos continuam idênticos, e registra a divergência como
atenção. O hash histórico foi preservado para não reescrever evidência.

## Riscos de interpretação

1. O teste de 31 imagens foi consultado mais de uma vez. Os arquivos de seleção
   declaram uso da validação, não seleção direta pelo teste; ainda assim, consultas
   repetidas podem influenciar decisões posteriores.
2. Hashes removem cópias exatas, mas não comprovam separação por planta.
3. Validação e teste têm apenas duas imagens `fn`; métricas dessa classe são
   particularmente instáveis.
4. Classes pretendidas das sintéticas não são diagnósticos agronômicos.
5. Menos alertas na simulação não significa menos falsos positivos.
6. Acurácia visual do classificador não é acurácia agronômica do sistema.
7. TTA e múltiplas consultas são análises exploratórias, não estimativas finais.
8. Não foram encontrados Monte Carlo, sensibilidade ou intervalos de confiança.
