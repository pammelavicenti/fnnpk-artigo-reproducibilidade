# Agente de visão com memória para acompanhamento nutricional de alface

Materiais de apoio a um artigo científico sobre classificação visual de possíveis deficiências de N, P e K em alface e uma política de decisão com estado persistente. O agente registra decisões em SQLite e pode publicar eventos no Redis. Este repositório preserva código, configurações, manifestos e resultados pequenos encontrados no arquivo de trabalho.

## Escopo e interpretação

Os arquivos registram etapas de preparação, treinamento, validação, consultas exploratórias ao teste, testes funcionais do agente e uma comparação descritiva de políticas. As saídas do agente são **suspeitas visuais**, não diagnósticos agronômicos confirmados.

A comparação de políticas usa cinco observações simuladas e previsões já registradas. A redução de alertas nesse cenário não é evidência de redução de falsos alertas nem de benefício em cultivo real. O conjunto chamado de teste foi consultado durante o desenvolvimento em parte dos experimentos e, portanto, seus resultados devem ser tratados como exploratórios, não como avaliação independente final.

## Comece aqui

1. Leia as [limitações de reprodução](docs/PENDENCIAS_REPRODUCAO.md).
2. Execute os [testes do agente](#agente-testes-e-simulação-funcional).
3. Consulte os [resultados disponíveis](#resultados-disponíveis) conforme a
   pergunta que deseja verificar.
4. Use o [inventário de artefatos](docs/INVENTARIO_ARTEFATOS.csv) para conferir
   finalidade, origem e eventuais ajustes de cada arquivo.

## Estrutura do repositório

| Caminho | Conteúdo |
| --- | --- |
| `scripts/` | Preparação, conferência visual e divisão dos dados. |
| `FNNPK_preparacao/agente_visao_v1/` | Agente, testes e cenários funcionais. |
| `FNNPK_preparacao/comparacao_politicas/` | Comparação descritiva simulada. |
| `FNNPK_preparacao/comparacao_validacao_seed321/` | Seleção em validação e consulta exploratória ao teste. |
| `FNNPK_preparacao/comparacao_sementes_C_V2_*/` | Comparação exploratória entre sementes. |
| `FNNPK_preparacao/C_sinteticas_*/` | Experimentos com imagens sintéticas. |
| `FNNPK_sintetico_piloto/` e `FNNPK_sintetico_v2/` | Metadados dos lotes sintéticos. |
| `docs/` | Verificação, pendências e inventários da publicação. |

As pastas de experimentos mantêm os nomes originais, inclusive datas e sementes,
para preservar a ligação entre configurações e resultados registrados.

## Dados

O conjunto de imagens original não é redistribuído aqui. A origem pública, URL, versão e termos de redistribuição do dataset não estavam documentados nos materiais encontrados; obtenha esses dados junto aos autores ou à fonte citada no artigo e confirme a licença antes do uso.

Depois de colocar as classes originais em `FNNPK/` (`-K`, `-N`, `-P` e `FN`), os caminhos podem ser configurados em PowerShell:

```powershell
$env:FNNPK_ORIGEM = 'C:\caminho\para\FNNPK'
$env:FNNPK_PREPARACAO = 'C:\caminho\para\FNNPK_preparacao'
python scripts/preparar_base.py
python scripts/conferir_imagens.py
python scripts/dividir_base.py
```

Os scripts originais continham caminhos absolutos locais. Somente na cópia de publicação eles foram substituídos por variáveis de ambiente com valores relativos como padrão. Os manifestos mantêm nomes, hashes e divisões registrados, mas os prefixos absolutos locais foram removidos.

`scripts/dividir_base.py` documenta grupos visuais provisórios e usa hashes para
cópias exatas. Isso **não comprova** agrupamento por planta ou por sequência de
captura. Não use o manifesto como evidência de independência biológica entre as
partições sem documentação adicional.

## Dependências confirmadas

O registro `FNNPK_preparacao/resultado_divisao_agrupada_seed321/configuracao.json` informa Python 3.11.17, TensorFlow 2.17.1, Keras 3.15.1, NumPy 1.26.4 e scikit-learn 1.9.1 para esse treinamento. Os protocolos de recorte registram Pillow 12.3.0 e NumPy 2.4.6 em uma etapa distinta. A versão de Matplotlib não foi registrada.

Para os testes funcionais e a simulação do agente, TensorFlow não é necessário. Consulte `FNNPK_preparacao/agente_visao_v1/requirements.txt`. Para reproduzir treinamento, crie um ambiente compatível com as versões registradas e instale também Matplotlib; não foi criado um único arquivo de dependências porque os protocolos encontrados registram ambientes diferentes.

## Treinamento e avaliação

Os comandos abaixo são instruções de reprodução e **não foram executados durante a preparação deste repositório**:

```powershell
python FNNPK_preparacao/treinar_alface.py --ajuda
python FNNPK_preparacao/comparar_treinamentos.py --help
python FNNPK_preparacao/comparar_sementes.py --help
python FNNPK_preparacao/avaliar_modelo_c.py
python FNNPK_preparacao/avaliar_sinteticas.py --help
```

Alguns scripts dependem das imagens e de arquivos `.keras` excluídos. Verifique
os argumentos e [as pendências](docs/PENDENCIAS_REPRODUCAO.md) antes de executar.
Não trate os resultados em `avaliacao_exploratoria_teste*` como teste independente.

## Agente, testes e simulação funcional

```powershell
cd FNNPK_preparacao/agente_visao_v1
python -m unittest -v
python agente_visao.py --banco demo.sqlite simular --entrada cenarios_demo.jsonl --saida resultados_simulados.jsonl
```

Para Redis, defina `REDIS_URL` apenas no ambiente. O arquivo `.env.example` contém um exemplo local sem credenciais. Os bancos SQLite operacionais não são versionados.

```powershell
$env:REDIS_URL = 'redis://localhost:6379/0'
python agente_visao.py --banco agente_local.sqlite publicar
```

A comparação de políticas pode ser reexecutada sem TensorFlow nem Redis:

```powershell
cd FNNPK_preparacao/comparacao_politicas
python comparar_politicas.py
```

## Resultados disponíveis

- **Treino:** históricos CSV e configurações nas pastas `resultado_*`, `C_sinteticas_*`, `comparacao_validacao_*` e `comparacao_sementes_*`.
- **Validação usada no desenvolvimento:** `comparacao_validacao_seed321/resumo_validacao.json` e a comparação de sementes. Esses números orientaram escolhas de modelo.
- **Teste exploratório já consultado:** pastas `avaliacao_teste` e `avaliacao_exploratoria_teste*`; não constituem avaliação independente final.
- **Simulação funcional do agente:** JSONL em `agente_visao_v1/`; verificam decisões, persistência e recuperação, não acurácia nutricional.
- **Comparação descritiva simulada:** `comparacao_politicas/comparacao_resultados.json`; não é experimento de campo.

## Citação

Os metadados de citação estão em `CITATION.cff`. Ao usar este software, cite a
versão arquivada correspondente. O DOI será acrescentado após o depósito de uma
release em um repositório de preservação, como o Zenodo.

## Limitações e licença

Não foram encontrados notebooks, scripts de Monte Carlo, análises de sensibilidade
ou cálculo de intervalos. Dataset, modelos e parte das entradas necessárias à
reprodução completa também não estão no repositório. Veja
[`docs/PENDENCIAS_REPRODUCAO.md`](docs/PENDENCIAS_REPRODUCAO.md).

O código original deste repositório é distribuído sob a licença MIT; consulte
`LICENSE`. Essa licença não concede direitos sobre o dataset original, imagens,
pesos ImageNet, modelos ou outros materiais de terceiros. Confirme separadamente
os termos aplicáveis antes de obter, redistribuir ou reutilizar esses materiais.

