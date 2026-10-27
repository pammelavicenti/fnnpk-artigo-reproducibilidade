# Relatório de verificação local

> **Registro histórico:** este documento descreve a preparação inicial da cópia
> pública. Para as verificações executadas após a reestruturação didática,
> consulte [`RELATORIO_FINAL.md`](RELATORIO_FINAL.md).

Data da preparação: 27 de outubro de 2026.

## Inventário da origem

- 1.987 arquivos encontrados, totalizando 5.517.246.615 bytes.
- Principais exclusões por volume: 1.777 PNG, 34 JPG, um ZIP de 2.516.615.524 bytes e 14 modelos Keras totalizando 382.262.542 bytes.
- Nenhum repositório `.git` foi encontrado na origem; portanto, não havia histórico Git local a reutilizar ou examinar.

## Informações sensíveis

- Varredura por chaves privadas, padrões de tokens, credenciais genéricas, e-mails e caminhos de usuário: nenhuma ocorrência sensível confirmada na cópia final.
- O único arquivo `.env*` é `.env.example`, com valores fictícios/locais.
- Caminhos absolutos com o nome do usuário foram removidos apenas da cópia de publicação.
- O commit local contém o nome e o e-mail do autor configurados no Git, como todo commit. Esses valores não são reproduzidos neste relatório e devem ser confirmados antes da publicação.
- A varredura é uma medida preventiva e não substitui revisão humana antes de tornar o repositório público.

## Verificações executadas

- Análise sintática de 26 arquivos Python com `ast.parse`: aprovada.
- Leitura estrutural de 65 arquivos JSON, 7 JSONL e 39 CSV: aprovada.
- `python -m unittest -v` em `FNNPK_preparacao/agente_visao_v1`: 12 testes aprovados.
- `comparar_politicas.py` executado com saída temporária: cinco observações processadas e decisões do agente conferidas com os registros.

## Não executado

- Treinamento ou ajuste fino.
- Avaliação/inferência dependente de modelos `.keras`.
- Redis real.
- Geração ou download de dataset, imagens sintéticas ou pesos.
- Simulações de Monte Carlo, análises de sensibilidade ou intervalos, pois os respectivos materiais não foram encontrados.

Os testes verificam comportamento de software e consistência estrutural. Eles não validam a acurácia nutricional, a independência biológica das partições nem o desempenho em cultivo real.
