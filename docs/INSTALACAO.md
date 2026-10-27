# Guia de instalação

Este projeto possui duas rotas de ambiente porque as etapas históricas não
foram executadas todas com as mesmas versões. Para começar, instale somente o
necessário para a atividade que deseja reproduzir.

## Requisitos gerais

- Git, para obter e atualizar o repositório;
- Python 3.11 é a opção mais próxima do treinamento registrado (Python 3.11.17);
- espaço adicional apenas se você obtiver legalmente dataset e modelos;
- GPU não é necessária para testes, simulação ou comparação de políticas.

## Ambiente mínimo: testes e demonstrações

O núcleo da política usa apenas a biblioteca padrão do Python. No Windows 11,
em PowerShell:

```powershell
git clone https://github.com/pammelavicenti/fnnpk-artigo-reproducibilidade.git
cd fnnpk-artigo-reproducibilidade
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python scripts/verificar_reproducibilidade.py
```

No Linux ou macOS:

```bash
git clone https://github.com/pammelavicenti/fnnpk-artigo-reproducibilidade.git
cd fnnpk-artigo-reproducibilidade
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python scripts/verificar_reproducibilidade.py
```

O último comando deve terminar com código zero e uma mensagem de aprovação. Ele
não baixa dados, não carrega modelos e não conecta ao Redis.

Se o PowerShell bloquear `Activate.ps1`, você pode executar diretamente:

```powershell
.\.venv\Scripts\python.exe scripts\verificar_reproducibilidade.py
```

## Ambiente do agente com imagem e modelo real

Instale as dependências do adaptador apenas quando possuir um modelo compatível:

```powershell
python -m pip install -r FNNPK_preparacao/agente_visao_v1/requirements.txt
```

Esse arquivo inclui Pillow, NumPy e o cliente Redis, mas não instala TensorFlow.
O registro do treinamento principal informa TensorFlow 2.17.1, Keras 3.15.1 e
NumPy 1.26.4. Use um ambiente separado e teste a compatibilidade do seu sistema.
Um modelo com camadas personalizadas pode exigir código adicional para ser
carregado. A inferência em uma imagem pode usar CPU; GPU é opcional nesse caminho.

## Ambiente histórico de treinamento

O arquivo
`FNNPK_preparacao/resultado_divisao_agrupada_seed321/configuracao.json` registra:

| Componente | Versão histórica |
| --- | --- |
| Python | 3.11.17 |
| TensorFlow | 2.17.1 |
| Keras | 3.15.1 |
| NumPy | 1.26.4 |
| scikit-learn | 1.9.1 |

Matplotlib é importado pelo treinamento, mas sua versão não foi registrada.
Essas versões descrevem uma execução passada; não garantem, isoladamente, que o
treinamento será reproduzido em qualquer hardware. Pesos ImageNet podem exigir
acesso à rede. A implementação atual de `treinar_alface.py` exige uma GPU e
interrompe a execução quando nenhuma é detectada.

## Ambiente separado de recorte

`FNNPK_preparacao/preparar_fundo_uniforme.py` usa `rembg`, Pillow e ONNX Runtime.
Os protocolos preservados registram rembg 2.0.85, Pillow 12.3.0, ONNX Runtime
1.30.0 e NumPy 2.4.6, diferentes do ambiente de treinamento. Use outro ambiente
virtual. A primeira execução do segmentador pode baixar pesos e, portanto, exige
rede. Essa etapa funciona em CPU.

## Redis

Redis é opcional. Testes e simulações não precisam de servidor. Para publicação
real, configure `REDIS_URL` somente no ambiente; não grave senha no repositório.

```powershell
$env:REDIS_URL = 'redis://localhost:6379/0'
```

## Erros comuns

| Sintoma | Causa provável | Ação segura |
| --- | --- | --- |
| `ModuleNotFoundError: tensorflow` | Comando de treino/inferência em ambiente mínimo | Use o ambiente histórico separado. |
| Modelo `.keras` não encontrado | Pesos não são distribuídos | Obtenha o arquivo exato com a autora; não substitua silenciosamente. |
| Pasta de classe ausente | Dataset não segue a estrutura esperada | Confira o Nível 2 do guia de reprodução. |
| Falha ao conectar no Redis | Servidor opcional não iniciado/configurado | Execute sem `--redis` ou configure o serviço. |
| Resultados numéricos diferentes | Hardware, biblioteca, pesos ou dados divergentes | Compare versões, manifesto, hash e sementes antes de interpretar. |
