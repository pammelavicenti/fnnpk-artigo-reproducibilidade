# Simulação Monte Carlo: material da versão 6

Material suplementar fornecido pelo orientador para reproduzir a simulação de Monte Carlo, as análises de sensibilidade e a implementação de referência das regras. O artigo em Word/PDF e o ZIP não são distribuídos nesta pasta. Scripts, comentários, atribuições e resultados recebidos foram preservados; este guia foi revisado para publicação.

## Papel da referência JavaScript

O projeto tem um único agente principal: o
[agente Python](../FNNPK_preparacao/agente_visao_v1/agente_visao.py), descrito em seu
[guia](../FNNPK_preparacao/agente_visao_v1/LEIA_ME.md). Ele integra percepção visual,
memória persistente em SQLite, decisão informacional e publicação opcional no Redis.
A continuidade do desenvolvimento e a integração com a hidroponia devem usar o Python.

A [referência JavaScript](agente_referencia/agente.js) é material de verificação:
recebe previsões prontas, não executa a rede neural e não conecta a um servidor Redis.
Ela não constitui um segundo agente operacional trabalhando junto com o Python.
Deve ser preservada porque sustenta as verificações relatadas no artigo.

Os testes de equivalência publicados em [equivalencia.js](agente_referencia/equivalencia.js)
comparam a política `policyE` da simulação com a referência JavaScript nos cenários
cobertos. Não demonstram automaticamente equivalência completa com o agente Python.
Uma comparação direta entre a simulação e o Python é uma possibilidade futura,
ainda não realizada neste trabalho. Testes funcionais e repetibilidade computacional
não constituem validação agronômica.

## Antes de começar

Instale o [Node.js 24](https://nodejs.org). Não há outras dependências. O aviso `ExperimentalWarning` sobre SQLite pode ser ignorado.

## O que há no pacote

| Pasta | Conteúdo |
|---|---|
| `scripts/` | Simulação, sensibilidade à priori, análise pareada, variação do intervalo e intervalos de confiança |
| `resultados_originais/` | Saídas usadas no artigo, para comparação |
| `agente_referencia/` | Implementação das regras do artigo, testes e comparação com a simulação |
| `conferencia/` | Cálculo exato, sem sorteio, feito com as regras reescritas à parte |
| `verificacao_base_kaggle/` | Inspeção da faixa colorida nas imagens da base |

## Como rodar

Na pasta `scripts`:

```
node simulacao_politicas.js
node simulacao_sensibilidade_prior.js
node analise_pareada.js
node analise_variacao_intervalo.js
node intervalos_confianca.js
```

Execute os comandos em uma **cópia temporária de toda a pasta do suplemento**, fora do repositório. As saídas são gravadas em `scripts/`; a equivalência também sobrescreve `agente_referencia/equivalencia_resultados.json` na cópia. Preserve a pasta versionada.

Exemplo em PowerShell, partindo da raiz do repositório:

```powershell
$copia = Join-Path ([System.IO.Path]::GetTempPath()) ("monte-carlo-" + [guid]::NewGuid())
Copy-Item -LiteralPath suplemento_monte_carlo -Destination $copia -Recurse
Set-Location (Join-Path $copia scripts)
```

Depois dos cinco comandos acima, use `Set-Location ../agente_referencia` e, por último, `Set-Location ../conferencia` para os comandos abaixo. Não é necessário instalar pacotes npm. SQLite é o módulo embutido no Node.js; não há servidor de banco externo.

Na pasta `agente_referencia`:

```
node --test testes.test.js
node equivalencia.js ../scripts/simulacao_politicas.js
node sensibilidade_do_teste.js ../scripts/simulacao_politicas.js
```

Resultado esperado: 21 testes aprovados e 0 divergência em 156.630 passos de 19.375 sequências. Em `sensibilidade_do_teste.js`, as regras alteradas de propósito devem divergir em ao menos um dos intervalos. A comparação pode levar alguns minutos.

Na pasta `conferencia`:

```
node verificar.js
```

Resultado esperado: agente com 96,01% de alerta correto e 0,51% de alerta incorreto. Na saída desse script, "Tabela 7" corresponde à Tabela 4 do artigo.

## Onde cada número aparece

| No artigo | Valor | Arquivo |
|---|---|---|
| Seção 4.3: alerta correto e alerta incorreto | 99,8% e 38,6%; 86,0% e 2,1% | `simulacao_log.txt`, S0_base |
| Seção 4.3: alertas por episódio | 4,40; 1,91; 0,95 | `simulacao_log.txt`, S0_base |
| Seção 4.3: revisões e novas capturas | 0,81 e 1,59 | `simulacao_log.txt`, S0_base |
| Seção 4.3: atraso nos mesmos episódios | 1,35 passo | `analise_pareada_log.txt`, S0_base |
| Seção 4.3: acionamentos | 1,91 em IS e 1,76 no agente | `analise_pareada_log.txt`, S0_base |
| Seção 4.3: capturas a cada 24 horas | 2,91 e 1,95; 2,68 novas capturas | `analise_pareada_log.txt` e `simulacao_log.txt`, S5_d24_W24 |
| Seção 4.3: sem variações da matriz | 100,0% e 96,0%; 13,7% e 0,5% | `analise_pareada_log.txt`, S1_plugin |
| Seção 4.3: outras prioris | 18,0% e 0,6%; 55,4% e 3,9% | `sensibilidade_prior_log.txt` |
| Seção 4.3: repetição de erros (ρ = 0,8) | 17,4% e 11,5%; 5,8 e 6,5 pontos; 32,8% | `analise_pareada_log.txt`, S3_rho0.8 |
| Seção 4.3: três fotos | 31,6 e 25,6 pontos | `analise_pareada_log.txt`, S7_L3 |
| Seção 4.3: três concordâncias | 63,9% | `simulacao_log.txt`, S0_base, E_k3 |
| Seção 4.3: deficiência persistente | 7 alertas em 14 fotos | `analise_pareada_log.txt`, última linha |
| Seção 4.4: variação do intervalo | 0,0%; 68,3%; 86,1% | `analise_variacao_intervalo_log.txt` |
| Seções 3.3 e 4.1: intervalos de confiança | Wilson e *bootstrap* | `intervalos_confianca.json` |

Os comentários internos de `simulacao_politicas.js` citam "Figura 3" para a matriz de confusão. Na versão 6, ela é a Figura 5.

## O que conferir

1. A matriz `CM` dos scripts corresponde à sua matriz de confusão?
2. As regras em `policyE` e em `agente_referencia/agente.js` correspondem ao agente que você implementou?
3. Os números do artigo batem com os arquivos gerados?

## Limites

- A simulação **não analisa imagens**: ela sorteia previsões a partir da matriz de confusão das 31 imagens. A nova captura é apenas contada.
- A implementação de referência **não é o agente original**: não roda a rede neural nem usa Redis. Ela mostra que a simulação segue as regras escritas.
- Reproduzir os números mostra que o cálculo é repetível, não que o agente funcione em plantas reais.
- O CSV de inspeção contém 208 arquivos (72 `-K`, 58 `-N`, 66 `-P`, 12 `FN`), com 203 hashes únicos. Há 87 arquivos com cinco blocos coloridos, equivalentes a 82 hashes únicos, inclusive todos os 12 arquivos `FN`. A marca colorida é um indício e **não comprova isoladamente origem sintética**. Veja `verificacao_base_kaggle/marca.csv`.
- Scripts e implementação de referência foram feitos com apoio de IA generativa, como consta na declaração do artigo.

## Sementes e parâmetros preservados

- Simulação: `20261023 + i`, para os oito cenários S0 a S7 (`i=0..7`).
- Sensibilidade à priori: `20261033` e `20261034` (alpha 0,1 e 1).
- Análise pareada: as mesmas sementes dos cenários selecionados (S0, S1, S3, S5, S7).
- Variação do intervalo: `20261102 + i`, para quatro cenários (`i=0..3`).
- Bootstrap: semente `20261023`, 10.000 reamostragens.
- Equivalência aleatória: `20261102`; folhas ilustrativas: `7`.

As simulações usam 1.000 réplicas e 1.000 episódios por classe por réplica. Os parâmetros completos estão nos scripts e nos JSON originais. A conferência exata enumera sequências, sem sorteio.

## Comparação das saídas

`resultados_originais/` é a referência recebida, preservada byte a byte, inclusive logs UTF-16. Os cinco scripts geram cinco JSON e dois CSV. Compare os CSV byte a byte e os JSON estruturalmente, sem tolerância numérica, retirando **somente** os campos de primeiro nível `gerado_em` e `node` quando presentes.

Há um comparador adicional em Python 3 (biblioteca padrão). Partindo da raiz do repositório e mantendo `$copia` do exemplo:

```powershell
python suplemento_monte_carlo/conferencia/comparar_saidas.py "$copia"
```

Ele termina com código zero apenas se os sete arquivos coincidirem. Não compara logs nem substitui os testes das regras. Compare também `agente_referencia/equivalencia_resultados.json` com o original do pacote, retirando os mesmos dois campos. Os logs devem ser conferidos separadamente: informe diferenças de duração, avisos e formato, além de qualquer diferença científica. Não trate tempos de execução como datas de geração.

O relatório da execução desta publicação está em [conferencia/VERIFICACAO.md](conferencia/VERIFICACAO.md). Os resultados esperados descritos anteriormente não substituem o resultado real desse relatório.

## Imagens, fonte e direitos

As quatro imagens documentais incluídas são recorte e folhas de inspeção da base **Baronn — Lettuce NPK Dataset**. Fonte: https://www.kaggle.com/datasets/baronn/lettuce-npk-dataset . A plataforma indica **CC0: Public Domain** (consulta aos metadados públicos em 03/11/2026). Essa é a fonte de download e a licença declarada pela plataforma; a procedência biológica das imagens e a validade dos rótulos continuam sem comprovação independente. A presença de marcas coloridas não comprova isoladamente origem sintética.

Os scripts `marca.ps1` e `folhas.ps1` recebem caminhos por parâmetros e exigem uma cópia da base completa e `System.Drawing` no Windows. Não são necessários para as simulações. As imagens anexadas e `marca.csv` foram preservados; o dataset completo não foi acrescentado ao repositório.

Não se atribui uma nova licença ao material fornecido nem se presume que a licença MIT do código original do repositório cubra todo este suplemento. Preservam-se os comentários e as atribuições recebidas. O pacote informa uso de IA generativa nos scripts e na implementação de referência, conforme a declaração do artigo; não são inferidos nomes ou contribuições adicionais.

## Referências internas do pacote

Os scripts preservam a numeração de figuras e tabelas usada durante a preparação: “Figura 3” corresponde à Figura 5 da versão 6, e “Tabela 7” na conferência corresponde à Tabela 4. O artigo não foi alterado nem houve novo treinamento.

O README principal e os guias atuais incorporam a publicação deste suplemento. Os relatórios históricos descrevem o estado anterior à sua inclusão e devem ser lidos com as notas contextuais; as evidências específicas de Monte Carlo estão nesta pasta. A matriz de confusão provém de avaliação exploratória de 31 imagens e não se torna uma avaliação independente com estas simulações.
