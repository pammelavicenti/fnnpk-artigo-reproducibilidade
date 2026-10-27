# Histórico de melhorias

## 2026-10-27 — licença, citação e organização inicial

### Documentação

- inclusão de `CITATION.cff` e licença MIT;
- separação entre `docs/` e `scripts/`;
- inventário e lista de publicação atualizados;
- ressalvas explícitas para materiais de terceiros.

### Código

- caminhos padrão dos três scripts de preparação ajustados após a mudança para
  `scripts/`;
- nenhum algoritmo experimental ou resultado numérico alterado.

### Testes

- doze testes do agente executados com sucesso;
- sintaxe e arquivos estruturados conferidos.

## 2026-10-27 — reestruturação didática e de reprodutibilidade

### Documentação

- diagnóstico inicial rastreável;
- novos guias de instalação, reprodução progressiva e metodologia;
- matriz de rastreabilidade entre afirmações, experimentos e evidências;
- README reestruturado para usuários iniciantes;
- relatório final de verificação com estados `APROVADO`, `FALHOU`,
  `NÃO EXECUTADO` e `NÃO REPRODUZÍVEL INTEGRALMENTE`.

### Código

- comando central de verificação sem dataset, GPU, modelo ou Redis;
- saídas geradas somente em diretórios temporários;
- nenhuma mudança nas regras da política, treinamento ou avaliação histórica.

### Testes e automação

- workflow de CI limitado às verificações leves e reproduzíveis;
- comparação determinística conferida contra a referência versionada;
- validação de sintaxe, arquivos estruturados, links e inventários.

### Mudanças de comportamento

- nenhuma mudança pretendida no comportamento científico ou operacional;
- a alteração é de navegação, documentação e verificação automatizada.
