# Verificação do suplemento em 03/11/2026

Ambiente: Windows, Node.js v24.15.0, sem dependências adicionais. Os nove comandos terminaram. Foram executados em uma cópia temporária fora do repositório; as saídas recebidas não foram sobrescritas. O ZIP e o artigo foram excluídos da publicação.

## Execuções reais

| Comando | Código de saída | Duração em segundos |
| --- | --- | --- |
| `node simulacao_politicas.js` | 0 | 61.414 |
| `node simulacao_sensibilidade_prior.js` | 0 | 13.878 |
| `node analise_pareada.js` | 0 | 10.501 |
| `node analise_variacao_intervalo.js` | 0 | 4.147 |
| `node intervalos_confianca.js` | 0 | 0.151 |
| `node --test testes.test.js` | 0 | 0.311 |
| `node equivalencia.js ../scripts/simulacao_politicas.js` | 0 | 736.802 |
| `node sensibilidade_do_teste.js ../scripts/simulacao_politicas.js` | 0 | 113.310 |
| `node verificar.js` | 0 | 0.116 |

Os cinco primeiros comandos foram executados em `scripts/`, os três seguintes em `agente_referencia/` e o último em `conferencia/`. Os logs completos de stdout e os códigos/durações estão em [execucao_2026-11-03/](execucao_2026-11-03/). Todos os stderr ficaram vazios.

## Resultados

- Testes: **21 aprovados, zero falhas**, sem cancelamentos ou testes omitidos.
- Equivalência: **19.375 sequências, 156.630 passos e zero divergências**, após a conclusão dos quatro grupos. O JSON de equivalência coincide com o recebido, exceto `gerado_em` e `node`.
- Sensibilidade do teste: sem alteração, zero divergências nos dois intervalos; as quatro alterações propositais foram detectadas em pelo menos um intervalo. Em 6 h: 672 (fn), 780 (inválida), 933 (três concordâncias), 0 (janela 48 h). Em 24 h: 0, 0, 933 e 612, respectivamente, sempre sobre 3.125 sequências. São resultados do teste de mutações, não falhas da regra original.
- Conferência exata do agente E: **96,01%** de alerta correto e **0,51%** de episódio com alerta incorreto. O log preserva o atraso, as demais políticas e a sequência funcional.
- Os **cinco JSON e dois CSV** de `resultados_originais/` coincidiram com as saídas geradas: CSV byte a byte; JSON sem tolerância numérica, excluindo apenas os campos de primeiro nível `gerado_em` e `node`. Nenhuma diferença numérica encontrada.

## Diferenças registradas, sem alterar os originais

Os logs não são todos idênticos em bytes. [diferencas_logs.txt](execucao_2026-11-03/diferencas_logs.txt) registra as diferenças linha a linha após decodificação. O log original de sensibilidade está em UTF-16; os demais logs recebidos estão em UTF-8 com BOM. Todos usam CRLF. Os novos stdout estão em UTF-8 com LF. Os materiais originais não foram convertidos.

Os dez tempos cumulativos impressos por simulação/sensibilidade e as durações dos 21 testes e do total mudaram com a execução. O aviso histórico `ExperimentalWarning` sobre SQLite, presente no log original dos testes, não foi emitido pelo Node.js instalado. Essas diferenças foram explicitamente registradas; não foram tratadas como datas de geração nem ocultadas. Os demais conteúdos dos sete logs comparáveis coincidem após considerar essas diferenças de representação, tempo e aviso. O pacote não fornece log original para `intervalos_confianca.js` ou `conferencia/verificar.js`; suas saídas reais estão anexadas.

O CSV da base contém 208 arquivos, dos quais 203 hashes são únicos; 87 arquivos com marca completa correspondem a 82 hashes únicos. Há cinco pares duplicados: `-K/k_56.png` e `k_70.png`, `k_57.png` e `k_69.png`, `k_58.png` e `k_68.png`, `k_63.png` e `k_66.png`, e `-N/n_17.png` e `n_23.png`. A formulação do guia recebido (82/203) conta imagens únicas; o guia revisado esclarece ambos os denominadores sem modificar o CSV.

## Inspeção, preservação e limites

Todos os arquivos selecionados foram inspecionados antes da execução: código JavaScript/PowerShell, textos, estruturas JSON/CSV, imagens e metadados. Não foram encontrados credenciais, dados pessoais desnecessários ou caminhos privados no material selecionado. Identificadores de plantas/hashes nos testes são exemplos de software. O artigo excluído não foi executado nem publicado.

Foram comparados com o ZIP os 32 arquivos recebidos publicados sem revisão, incluindo todos os arquivos de `resultados_originais/`, scripts, imagens, CSV e evidências históricas do agente: **identidade byte a byte**. Somente o guia recebido foi revisado. Foram acrescentados este relatório, logs desta conferência, comparador e arquivos de controle locais ao suplemento. `.gitattributes` impede conversão automática das quebras de linha dos materiais. `git diff --cached --check` reconhecendo CRLF (`core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol`) não apontou problemas; a verificação padrão interpreta os CR preservados como espaços finais. A licença do material não foi ampliada por suposição.

SHA-256 do ZIP de origem (não publicado): `423cb87342cbd824e38eede19e26509f0069167c36c3729a178da501fa20adf6`.

A licença das imagens foi conferida nos metadados públicos do [Kaggle](https://www.kaggle.com/datasets/baronn/lettuce-npk-dataset): Baronn — Lettuce NPK Dataset, `CC0: Public Domain`. Consulta: `https://www.kaggle.com/api/v1/datasets/list?search=lettuce-npk-dataset`, filtrando a referência `baronn/lettuce-npk-dataset`.

Não houve falha nos nove comandos solicitados. Os scripts opcionais `marca.ps1` e `folhas.ps1` não foram reexecutados: exigem a base completa e estão fora dos nove comandos solicitados. As imagens e o CSV recebidos foram inspecionados e preservados. Permanecem pendentes a validação da procedência das imagens e a validação agronômica; a marca é apenas um indício. Repetibilidade computacional não demonstra eficácia em cultivo real, e a comparação das regras não executa a rede neural nem um servidor Redis.

## Conectividade antes do commit

O primeiro `git fetch origin` com acesso à rede foi concluído e atualizou `origin/main` para `13cc016` (merge da documentação existente). A branch específica `suplemento/monte-carlo` foi criada a partir desse estado, sem alterações locais anteriores. As tentativas de atualizar novamente as referências ao final falharam com `Could not resolve host: github.com`; a consulta pelo conector GitHub também falhou no transporte HTTP. Essas falhas de conexão são separadas dos resultados científicos acima. Não houve force push, reset ou descarte de trabalho. O resultado da tentativa de push deve ser consultado na entrega desta tarefa, sem inferir publicação a partir deste relatório.
