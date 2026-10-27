# Pendências de reprodução

## Materiais encontrados

- Scripts Python de preparação, divisão, treinamento, avaliação e comparação de sementes.
- Código do agente com estado persistente em SQLite e publicação opcional em Redis.
- Testes `unittest`, cenários JSON/JSONL e resultados funcionais registrados.
- Configurações, históricos CSV, matrizes, probabilidades NPZ e resumos JSON.
- `manifesto.csv`, `copias_identicas.csv`, `divisao_agrupada/manifesto_divisao.csv` e manifestos de recorte/sintéticas.

## Materiais apenas mencionados ou esperados

- Dataset público original e sua referência/URL/licença.
- Modelos `.keras` referenciados pelas configurações e pelo agente.
- Servidor Redis para o caminho de publicação real.
- Revisão agronômica das imagens sintéticas, indicada como pendente nos resultados.

## Materiais ausentes

- Notebooks.
- Scripts e resultados de Monte Carlo.
- Análises de sensibilidade e cálculo de intervalos de confiança.
- Evidência de identificação por planta ou sequência de captura que permita confirmar independência biológica entre treino, validação e teste.
- Arquivo de ambiente completo com todas as versões para cada experimento; Matplotlib não tem versão registrada.
- Avaliação independente final em dados não consultados durante o desenvolvimento.
- Documentação verificável da fonte e dos termos de redistribuição do dataset.

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
- Os pesos ImageNet são um material externo; sua obtenção pode exigir rede e deve respeitar os termos aplicáveis.

## Licenciamento

O código original deste repositório está sob a licença MIT. Essa licença não se
estende automaticamente ao dataset, às imagens, aos pesos ImageNet, aos modelos
ou a outros materiais de terceiros. A documentação da origem e dos respectivos
termos de uso e redistribuição permanece pendente.
