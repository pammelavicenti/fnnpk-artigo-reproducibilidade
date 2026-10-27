# Relatório final da reestruturação didática

Data: 27 de outubro de 2026.

## Resultado geral

O repositório passou a oferecer uma rota reproduzível sem dataset, GPU, modelo
ou Redis; documentação progressiva; rastreabilidade entre afirmações e arquivos;
e integração contínua limitada ao que pode ser honestamente executado. Nenhum
resultado numérico histórico, hiperparâmetro, semente ou regra da política foi
alterado.

## Arquivos criados

- `.github/workflows/verificacao.yml` — CI leve em Python 3.11;
- `scripts/verificar_reproducibilidade.py` — comando central;
- `docs/DIAGNOSTICO_INICIAL.md` — problemas observados antes das correções;
- `docs/INSTALACAO.md` — ambientes mínimo, treinamento e recorte;
- `docs/REPRODUCAO.md` — roteiro em três níveis;
- `docs/METODOLOGIA.md` — método, arquitetura e formatos;
- `docs/RASTREABILIDADE.md` — ligação entre afirmações e evidências;
- `docs/HISTORICO_MELHORIAS.md` — mudanças por categoria;
- `docs/RELATORIO_FINAL.md` — este relatório;
- `requirements/treinamento-historico.txt` e
  `requirements/recorte-historico.txt` — versões comprovadas por ambiente.

## Arquivos modificados

- `README.md` — nova página inicial didática e navegável;
- `.env.example` — namespace opcional de Redis documentado;
- `docs/PENDENCIAS_REPRODUCAO.md` — riscos técnicos e científicos atualizados;
- `docs/ARQUIVOS_PUBLICACAO.txt` e `docs/INVENTARIO_ARTEFATOS.csv` — lista e
  metadados sincronizados com a publicação.

## Problemas corrigidos

- comandos básicos antes espalhados passaram a ter uma entrada única;
- treino, validação, teste exploratório, teste funcional e simulação foram
  separados conceitualmente;
- ambientes incompatíveis deixaram de parecer um único ambiente instalável;
- exigência de GPU do treinamento atual foi explicitada;
- scripts históricos repetidos foram classificados como snapshots de proveniência;
- resultados passaram a apontar para arquivos-fonte verificáveis;
- comandos e saídas temporárias deixaram de sugerir sobrescrita dos históricos;
- CI foi limitada a testes leves, sem dados, modelos, GPU ou Redis;
- divergência entre o hash histórico e a entrada pública sanitizada foi registrada
  sem reescrever o resultado preservado.

## Comandos efetivamente executados

```text
python scripts/verificar_reproducibilidade.py
python -m unittest discover -s FNNPK_preparacao/agente_visao_v1 -v
python FNNPK_preparacao/agente_visao_v1/agente_visao.py ... simular ...
python FNNPK_preparacao/comparacao_politicas/comparar_politicas.py ...
python (validação sintática e de links relativos)
git diff --check
```

A simulação e a comparação foram chamadas pela rotina central com bancos e saídas
em diretórios temporários.

## Verificações

| Estado | Verificação | Resultado |
| --- | --- | --- |
| APROVADO | testes do agente | 12 testes |
| APROVADO | simulação funcional | 7 decisões idênticas à referência após remover horário de processamento |
| APROVADO | comparação de políticas | 5 observações; duas execuções determinísticas; decisões iguais à referência |
| APROVADO | arquivos estruturados | 65 JSON, 7 JSONL, 39 CSV e 5 NPZ legíveis |
| APROVADO | sintaxe Python alterada/publicada | analisada sem erro |
| APROVADO | links relativos e inventários | destinos, lista de arquivos e tamanhos conferidos |
| APROVADO | preservação histórica | nenhum arquivo dentro das pastas de resultados foi alterado |
| ATENÇÃO | hash histórico da comparação | difere da entrada pública sanitizada; demais campos coincidem |
| NÃO EXECUTADO | treinamento e ajuste fino | exigem dataset, GPU e ambiente pesado |
| NÃO EXECUTADO | avaliação/inferência real | modelos `.keras` ausentes |
| NÃO EXECUTADO | Redis real | serviço externo não necessário à verificação básica |
| NÃO REPRODUZÍVEL INTEGRALMENTE | resultados históricos completos | faltam dataset, modelos e parte da proveniência |

## Riscos científicos identificados

- o conjunto chamado teste foi consultado repetidamente e não é independente;
- não há identificação por planta que comprove independência biológica;
- validação e teste possuem somente duas imagens `fn`;
- sintéticas têm revisão agronômica pendente;
- acurácia visual não equivale a acurácia agronômica;
- a sequência de políticas não possui referência longitudinal;
- não há materiais de Monte Carlo, sensibilidade ou intervalos de confiança;
- versões de ambientes distintos não podem ser combinadas sem validação.

## Pendências restantes

- documentar fonte, versão, licença e rótulos do dataset;
- obter autorização para disponibilizar ou fornecer instruções verificáveis de
  obtenção dos modelos e dados;
- documentar identidade por planta e sequência de captura;
- executar avaliação independente em dados não usados no desenvolvimento;
- concluir revisão agronômica das imagens sintéticas;
- testar integração com Redis real, se ela fizer parte do uso pretendido;
- criar uma GitHub Release e arquivá-la para obter DOI, sem inventá-lo.

## Próximos passos recomendados

1. revisar esta branch por pull request e confirmar a renderização dos diagramas;
2. publicar a CI e conferir sua primeira execução no GitHub;
3. criar a release somente após essa revisão;
4. acrescentar DOI ao `CITATION.cff` apenas depois do depósito real;
5. planejar um conjunto final independente e um protocolo longitudinal por planta.
