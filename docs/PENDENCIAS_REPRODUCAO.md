# Pendências de reprodução

## Materiais encontrados

- Scripts Python de preparação, divisão, treinamento, avaliação e comparação de sementes.
- Código do agente principal Python com estado persistente em SQLite e publicação opcional em Redis.
- [Suplemento de Monte Carlo](../suplemento_monte_carlo/LEIA-ME.md): scripts, resultados, análises de sensibilidade, intervalos de confiança e referência JavaScript de verificação.
- Testes `unittest`, cenários JSON/JSONL e resultados funcionais registrados.
- Configurações, históricos CSV, matrizes, probabilidades NPZ e resumos JSON.
- `manifesto.csv`, `copias_identicas.csv`, `divisao_agrupada/manifesto_divisao.csv` e manifestos de recorte/sintéticas.

## Materiais apenas mencionados ou esperados

- Dataset completo e identificação da versão exata utilizada historicamente; a fonte de download e a licença declarada estão identificadas abaixo.
- Modelos `.keras` referenciados pelas configurações e pelo agente.
- Servidor Redis para o caminho de publicação real.
- Revisão agronômica das imagens sintéticas, indicada como pendente nos resultados.

## Materiais ausentes

- Notebooks.
- Evidência de identificação por planta ou sequência de captura que permita confirmar independência biológica entre treino, validação e teste.
- Arquivo de ambiente completo com todas as versões para cada experimento; Matplotlib não tem versão registrada.
- Avaliação independente final em dados não consultados durante o desenvolvimento.
- Comprovação independente da procedência biológica das imagens e da validade dos rótulos.
- Comparação direta da política da simulação com o agente principal Python; os testes publicados comparam a simulação com a referência JavaScript.

## Itens deliberadamente excluídos

- 1.811 imagens `.png`/`.jpg` do dataset, recortes e conjuntos sintéticos.
- 14 modelos `.keras` (aprox. 382 MB).
- Cinco bancos SQLite operacionais.
- `FNNPK_preparacao.zip` (aprox. 2,52 GB).
- Cache Python, diretórios de carregamento temporário e arquivos compilados.

## Ajustes feitos somente na cópia

- Caminhos absolutos com o nome do usuário foram convertidos em caminhos relativos nos arquivos textuais.
- `scripts/preparar_base.py`, `scripts/conferir_imagens.py`,
  `scripts/dividir_base.py` e as cópias de `treinar_alface.py` aceitam variáveis
  de ambiente para os diretórios locais.
- Foram adicionados `.gitignore`, `.env.example`, documentação e inventário. Resultados numéricos e hiperparâmetros não foram recalculados nem alterados.

## Riscos de interpretação

- Os agrupamentos visuais registrados são provisórios; não equivalem a agrupamento comprovado por planta.
- O conjunto denominado teste aparece em consultas anteriores e deve ser descrito como exploratório.
- A comparação de políticas usa uma sequência fictícia e previsões fixas. A contagem menor de alertas não demonstra desempenho agronômico em cultivo real.
- O hash de entrada preservado em `comparacao_resultados.json` antecede a
  sanitização da cópia pública de `entrada_cenario.jsonl`. A reexecução confirma
  as mesmas decisões e os demais campos, mas o hash histórico não é o hash da
  cópia publicada; consulte `RASTREABILIDADE.md`.
- O treinamento principal exige GPU na implementação atual; as avaliações
  dependentes de modelos não foram executadas nesta preparação.
- Os ambientes de treino e recorte registram versões diferentes de NumPy e não
  devem ser instalados como um único ambiente universal.
- Os pesos ImageNet são um material externo; sua obtenção pode exigir rede e deve respeitar os termos aplicáveis.

## Licenciamento

O código original deste repositório está sob a licença MIT. Essa licença não se
estende automaticamente ao dataset, às imagens, aos pesos ImageNet, aos modelos
ou a outros materiais de terceiros. A fonte de download informada do dataset é
[Baronn — Lettuce NPK Dataset](https://www.kaggle.com/datasets/baronn/lettuce-npk-dataset);
a plataforma declara **CC0: Public Domain**, conforme a
[consulta registrada no suplemento](../suplemento_monte_carlo/conferencia/VERIFICACAO.md).
Isso não comprova a procedência biológica das imagens nem a validade dos rótulos.
Marcas coloridas não comprovam isoladamente origem sintética. A identificação da
versão histórica e a comprovação independente dessas questões permanecem pendentes.
A declaração da plataforma não altera a licença ou as atribuições dos demais materiais.
