# Guia de reprodução progressiva

O grau de reprodução depende dos materiais disponíveis. “Aprovado” abaixo
significa que o comando foi executado e conferido; não significa validação
agronômica.

## Nível 1 — sem dataset e sem modelos treinados

### Requisitos

- Python 3.10 ou superior;
- cópia deste repositório;
- sem TensorFlow, GPU, Redis ou acesso à rede.

### Verificação central

Na raiz do repositório:

```powershell
python scripts/verificar_reproducibilidade.py
```

A rotina executa os doze testes do agente, uma simulação funcional, a comparação
de políticas em diretório temporário, valida arquivos estruturados e compara a
saída determinística com a referência versionada. Sucesso: código de saída zero
e resumo final `APROVADO`.

### Demonstração manual do agente

Windows/PowerShell:

```powershell
$pasta = 'FNNPK_preparacao/agente_visao_v1'
python "$pasta/agente_visao.py" --banco "$env:TEMP/agente_demo.sqlite" simular `
  --entrada "$pasta/cenarios_demo.jsonl" `
  --saida "$env:TEMP/resultados_demo.jsonl"
```

Linux:

```bash
python FNNPK_preparacao/agente_visao_v1/agente_visao.py \
  --banco /tmp/agente_demo.sqlite simular \
  --entrada FNNPK_preparacao/agente_visao_v1/cenarios_demo.jsonl \
  --saida /tmp/resultados_demo.jsonl
```

Saída esperada: sete decisões e a mensagem de que a simulação não mede acurácia
nutricional. Use um banco novo ou temporário; reusar um banco mantém o estado.

### Comparação manual das políticas

```powershell
cd FNNPK_preparacao/comparacao_politicas
python comparar_politicas.py --entrada entrada_cenario.jsonl `
  --saida "$env:TEMP/comparacao_resultados.json"
cd ../..
```

Critério de sucesso: cinco decisões conferidas; a política imediata produz quatro
alertas, enquanto o agente com estado produz um alerta nesse cenário. Isso é uma
simulação funcional, não uma taxa de falsos positivos.

## Nível 2 — com o dataset original

### Materiais necessários

- quatro diretórios de classe: `-K`, `-N`, `-P` e `FN`;
- confirmação externa da fonte, versão e licença do dataset;
- espaço para a cópia preparada.

A URL e os termos exatos do dataset não foram encontrados. Não use o repositório
como prova de autorização para obtê-lo ou redistribuí-lo.

Defina os caminhos e execute:

```powershell
$env:FNNPK_ORIGEM = 'C:\dados\FNNPK'
$env:FNNPK_PREPARACAO = 'C:\trabalho\FNNPK_preparacao'
python scripts/preparar_base.py
python scripts/conferir_imagens.py
python scripts/dividir_base.py
```

Entradas: imagens nas quatro classes. Saídas: nomes normalizados, `manifesto.csv`,
painéis de conferência e `divisao_agrupada/manifesto_divisao.csv`. Os scripts
recusam certas inconsistências e registram hashes de arquivos. O agrupamento
visual é provisório e não comprova independência entre plantas.

O treinamento principal existe em `FNNPK_preparacao/treinar_alface.py`, mas exige
ambiente compatível, dataset dividido, GPU detectável e acesso aos pesos ImageNet.
Ele grava na pasta histórica `resultado_divisao_agrupada_seed321`; portanto,
execute somente em uma cópia de trabalho para não colidir com artefatos preservados.

## Nível 3 — com dataset e modelos treinados

### Avaliação histórica

São necessários a divisão exata correspondente ao manifesto e os modelos Keras
exatos que foram excluídos da publicação. Os scripts `avaliar_modelo_c.py` e
`avaliar_sinteticas.py` verificam parte da configuração antes de avaliar.

As pastas de saída são denominadas `avaliacao_exploratoria_teste*` porque o teste
já havia sido consultado. Reexecutar esses scripts não transforma a avaliação em
teste independente.

### Inferência do agente

1. Copie e revise `config_modelo.exemplo.json`.
2. Aponte `modelo_path` para o modelo real.
3. Confirme a ordem das quatro saídas antes de marcar
   `ordem_classes_confirmada` como `true`.
4. Prepare um pedido com imagem existente, identificador de planta, horário com
   fuso e `analise_id` único.
5. Execute sem Redis primeiro.

```powershell
cd FNNPK_preparacao/agente_visao_v1
python agente_visao.py --banco agente_real.sqlite analisar `
  --config config_modelo.json --pedido pedido.json
```

Sucesso técnico significa que o modelo foi carregado, a imagem foi processada e
uma decisão foi persistida. Não significa diagnóstico nutricional confirmado.

## O que não é reproduzível integralmente

- identificação exata e licença do dataset;
- modelos `.keras` históricos;
- independência biológica das partições;
- avaliação final em dados nunca consultados;
- Monte Carlo, sensibilidade e intervalos de confiança mencionados, pois os
  respectivos materiais não foram encontrados;
- validação longitudinal e agronômica da política do agente.
