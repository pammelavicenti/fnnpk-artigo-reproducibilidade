# Diagnóstico inicial do repositório

Diagnóstico registrado em 27 de outubro de 2026, antes da reestruturação
didática. Os achados abaixo descrevem os arquivos efetivamente encontrados; não
pressupõem materiais externos nem execuções que não estejam documentadas.

## Escopo examinado

Foram inspecionados recursivamente o código Python, os testes, os arquivos JSON,
JSONL, CSV e NPZ, a documentação, os manifestos, as configurações de treinamento,
os metadados de citação, a licença, o `.gitignore` e o `.env.example`.

## Achados e resposta planejada

| ID | Achado verificável | Evidência principal | Resposta |
| --- | --- | --- | --- |
| D01 | Há código para preparar, dividir, treinar, avaliar e comparar modelos. | `scripts/` e `FNNPK_preparacao/*.py` | Criar guias separados de instalação, método e reprodução. |
| D02 | Dataset e modelos Keras não são distribuídos. | `.gitignore`, inventário e configurações que referenciam `.keras` | Organizar a reprodução em três níveis e não prometer execução integral. |
| D03 | O núcleo do agente pode ser testado sem TensorFlow, Redis, dataset ou GPU. | `agente_visao_v1/test_agente.py` | Oferecer um comando central para testes e demonstrações. |
| D04 | A comparação de políticas usa cinco percepções fixas de uma sequência fictícia. | `comparacao_politicas/entrada_cenario.jsonl` e `comparacao_resultados.json` | Reexecutar em diretório temporário e comparar com a referência versionada. |
| D05 | Resultados de treino, validação e teste exploratório aparecem em muitas pastas com nomes históricos. | Pastas `resultado_*`, `comparacao_*` e `C_sinteticas_*` | Preservar nomes e criar uma matriz de rastreabilidade. |
| D06 | Scripts históricos são repetidos dentro de pastas de resultados. | Cópias de `treinar_alface.py`, `comparar_treinamentos.py` e `script_executado.py` | Tratar como captura de proveniência; não consolidar sem prova de equivalência. |
| D07 | O conjunto chamado teste foi consultado durante o desenvolvimento. | Nomes `avaliacao_exploratoria_teste*` e campos `natureza_avaliacao`/`carater` | Classificar esses números apenas como teste exploratório. |
| D08 | A divisão usa grupos visuais provisórios e hashes, mas não identifica planta ou sequência de captura. | `scripts/dividir_base.py`, `manifesto_divisao.csv` | Manter explícito o risco de dependência biológica entre partições. |
| D09 | Há ambientes históricos diferentes. | Configuração de treino e protocolos de recorte | Não criar um único conjunto de versões como se cobrisse todas as etapas. |
| D10 | Os comandos estavam espalhados entre o README principal e documentos internos. | `README.md` e arquivos `LEIA_ME.md` | Criar uma página inicial curta e guias progressivos em `docs/`. |
| D11 | Não foram encontrados materiais de Monte Carlo, sensibilidade ou intervalos de confiança. | Inventário e busca recursiva | Registrar como ausente, sem reconstruir resultados. |
| D12 | Não há avaliação independente final comprovada. | Histórico de seleção e consultas ao teste | Separar acurácia de classificação de validade agronômica do sistema. |

## O que pode ser verificado localmente

- sintaxe e estrutura dos arquivos publicados;
- doze testes do núcleo de decisão;
- simulação funcional do agente com percepções controladas;
- comparação descritiva das duas políticas;
- igualdade entre a comparação reexecutada e a referência versionada;
- integridade estrutural de JSON, JSONL, CSV e dos inventários.

## O que depende de materiais externos

- preparação integral e nova divisão: dataset original e seus direitos de uso;
- treinamento: dataset, TensorFlow/Keras compatíveis e pesos ImageNet;
- avaliação histórica: dataset na divisão registrada e modelos `.keras` exatos;
- inferência real do agente: modelo treinado, ordem de classes confirmada e imagem;
- publicação real: servidor Redis configurado;
- validação agronômica: identidade de plantas, sequência temporal real e referência
  independente da condição nutricional.

## Regra de preservação

Arquivos históricos de resultados e cópias de scripts executados não serão
reescritos. Melhorias de documentação e automação serão adicionadas ao redor
deles. Qualquer verificação gerada durante os testes usará diretório temporário.
