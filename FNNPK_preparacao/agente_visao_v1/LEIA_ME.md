# Agente de visão nutricional — versão experimental 1

O agente usa o classificador existente como percepção e decide uma ação informacional
com base no histórico por planta. Não aciona bombas ou dosadores.

## Começar pela demonstração (sem instalar pacotes)

Extraia esta pasta dentro de FNNPK_preparacao. No terminal do seu ambiente `alface`:

```bash
cd "FNNPK_preparacao/agente_visao_v1"
python -m unittest -v
python agente_visao.py --banco demo.sqlite simular --entrada cenarios_demo.jsonl --saida resultados_demo.jsonl
```

As linhas mostram suspeita, alerta após concordância, divergência, imagem inválida
e observação de nutrição completa. Reexecutar o mesmo arquivo não cria novas análises.
Os resultados da simulação são identificados como `percepcao_simulada`.

## Política e hipóteses

- Primeira deficiência estimada: registrar suspeita e solicitar outra captura.
- Segunda captura com bytes diferentes, mesma classe e mesmo modelo, dentro da janela:
  emitir alerta de **possível** deficiência.
- Captura seguinte com mesma classe: registrar, evitando repetir o alerta no episódio.
- Deficiências divergentes, ou `fn` após suspeita: encaminhar para revisão e limpar a candidata.
- `fn` sem suspeita: registrar estimativa; não emitir atestado de planta saudável.
- Imagem indecodificável ou menor que o mínimo operacional: pedir nova captura e
  interromper a sequência. Não avalia desfoque, iluminação ou presença de alface.
- Empate na maior probabilidade: revisão.
- Modelo diferente ou suspeita fora da janela: iniciar uma nova sequência.
- Capturas fora de ordem ou com bytes já usados nessa planta não alteram seu estado.
- Mesmo id com conteúdo diferente é rejeitado. Mesmo id e conteúdo devolve o resultado anterior.

A janela padrão de 24 h é um parâmetro de engenharia provisório, **não agronômico**.
Pode ser configurada com `--janela-horas` antes do subcomando. Não há limiar de
"confiança": softmax não é tratado como confiança calibrada. Imagens distintas em
bytes podem continuar altamente correlacionadas. A política pode atrasar ou suprimir
alertas úteis; seu benefício não foi demonstrado por estes testes.

## Usar o modelo real

1. Copie `config_modelo.exemplo.json` para `config_modelo.json`.
2. Preencha `modelo_path` com o caminho absoluto do arquivo `.keras` ou `.h5`.
3. Verifique a ordem das saídas no treinamento, usando o arquivo de classes original.
   A lista fornecida é um exemplo, não uma descoberta do seu modelo.
4. Somente após verificar, altere `ordem_classes_confirmada` para `true`.
5. Copie `pedido.exemplo.json` para `pedido.json`; configure imagem, planta, id único
   e horário da captura com fuso. Fotografias da mesma planta usam o mesmo `planta_id`.

```bash
python -m pip install -r requirements.txt
python agente_visao.py --banco agente_real.sqlite analisar --config config_modelo.json --pedido pedido.json
```

Use seu TensorFlow já instalado; não atualize o ambiente de treinamento automaticamente.
Se o modelo tiver camadas personalizadas, sua definição precisa ser adicionada ao adaptador.
O adaptador assume EfficientNet padrão com entrada RGB float32 0..255, redimensionamento
bilinear para 224 e saída softmax. **Não faz TTA nem segmentação.** Verifique o
pré-processamento usado no seu treinamento antes de interpretar suas predições.
Um modelo treinado com fundo original não foi validado para imagens segmentadas.
O hash do arquivo do modelo identifica a versão que produziu a observação.

Mantenha um banco separado para demonstração e execução real: evita que percepções
simuladas contaminem histórico e publicações reais. Não altere a janela durante um
experimento sem iniciar outro banco; mantenha relógios sincronizados.

## Redis e execução contínua

```bash
export REDIS_URL='redis://localhost:6379/0'
export VISAO_NAMESPACE='visao_experimental:v1'
python agente_visao.py --banco agente_real.sqlite analisar --config config_modelo.json --pedido pedido.json --redis
python agente_visao.py --banco agente_real.sqlite publicar
```

A URL pode ser configurada para seu servidor; nunca coloque senha em arquivos do artigo.
O agente guarda a decisão e a publicação pendente no SQLite. Se Redis falhar, `publicar`
retoma. Cada análise usa uma chave estável de prefixo `visao_experimental:v1:analise:`.
Não altera o hash `sensores`, a API `/dicionario` ou o dashboard atual. O consumidor
deve consultar essas chaves e deduplicar ações por `analise_id`; SET idempotente não
garante execução única de notificações. Não usa Pub/Sub nem promete entrega exatamente uma vez.

```bash
python agente_visao.py --banco agente_real.sqlite executar --config config_modelo.json --entrada pedidos --redis
```

Para enviar uma observação, escreva seu JSON como `.tmp` e renomeie para `.json`
apenas quando completo. Use caminhos absolutos para imagens. O agente verifica a
pasta a cada 2 s, processa os pedidos e tenta publicar pendências automaticamente.
Sucesso renomeia o pedido para `.concluido`; falhas para `.erro`, sem encerrar o ciclo.
Revise o erro, corrija e renomeie para `.json` para tentar novamente. `Ctrl+C` encerra.
Execute uma única instância por pasta; este protótipo não coordena múltiplos leitores.

```bash
python agente_visao.py --banco agente_real.sqlite exportar --saida resultados_reais.jsonl
```

## O que foi verificado neste pacote

Doze testes automatizados do núcleo: concordância, persistência após reinício,
supressão de alertas repetidos, idempotência, conflitos de ids, reuso da imagem,
divergências, isolamento por planta, entrada inválida, ordem temporal, expiração,
mudança do modelo, probabilidades inválidas, empate e retomada de publicação.
A publicação é testada com destino simulado e falha após gravação.
O modelo Keras e um servidor Redis real não estão incluídos e não foram executados
na preparação deste pacote. Portanto, não existe ainda validação ponta a ponta real.

## Experimento para o artigo

Compare uma política de alerta a cada previsão de deficiência com esta política
de histórico nas **mesmas** sequências. Fixe regras, janela e modelo antes de avaliar.
Registre capturas, rótulos de referência, ações esperadas, decisões e tempos.
Meça alertas falsos, episódios de deficiência sem alerta, atraso até o alerta,
solicitações de captura e alertas redundantes. Reporte também as perdas: atrasos
e casos não sinalizados, não apenas a redução no número de alertas.

As sequências controladas verificam a política; não demonstram evolução temporal
real de uma planta. Para alegações de desempenho em cultivo, use capturas reais
por planta, rótulos agronômicos documentados e avaliação independente. Os resultados
de classificação do dataset são uma avaliação separada. Este pacote não demonstra
melhoria da acurácia, originalidade científica ou aprovação em periódico.
