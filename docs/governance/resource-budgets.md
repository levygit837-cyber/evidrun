---
id: governance-resource-budgets
type: governance
title: Budgets de performance e recursos
status: implemented
authority: normative
volatility: current
owner: core
created_at: 2026-07-31
updated_at: 2026-07-31
applies_to: repository
sources:
  - docs/adr/0001-benchmark-first-and-local-first.md
  - docs/adr/0017-structural-budget-and-named-seams.md
supersedes: []
superseded_by: null
implementation_refs:
  - resource-budget.toml
  - scripts/check_resource_budgets.py
  - scripts/resource_budget
  - .github/workflows/ci.yml
verification_refs:
  - tests/unit/test_resource_budget.py
  - tests/unit/test_resource_budget_policy.py
---

# Budgets de performance e recursos

`scripts/check_resource_budgets.py` mede poucos cenários reais e registra o resultado em texto e
JSON. A primeira política prefere sinal honesto a precisão falsa: duração e pico de memória nunca
bloqueiam o merge; tamanhos, contagens e fatos contratuais bloqueiam somente quando a metodologia os
classifica como determinísticos. Métrica warning amostrada usa mediana com guarda de amplitude
relativa; tamanho de artifact e de banco são lidos exatos e não passam por esse guarda.

```bash
uv run python scripts/check_resource_budgets.py --profile python
uv run python scripts/check_resource_budgets.py --profile build
```

Use `--json-out <path>` para guardar o documento de máquina. O CI publica separadamente
`python-resource-report` e `build-resource-report`; cache, `.venv` e `node_modules` não entram nos
budgets de output.

## Cenários medidos

- `startup_import`: importa a CLI real em cinco processos isolados;
- `crl_ctx_002`: executa três vezes o CRL-CTX-002 offline pelo Runtime Kernel, com SQLite e artifacts
  temporários reais, e mede seus bytes e contagens;
- `run_bundle`: prepara uma Run canônica, exporta seu Evidence Bundle audit e executa o verificador
  isolado três vezes;
- `application_build`: executa o `pnpm build` real três vezes em processos isolados e mede duração e
  pico RSS dos processos filhos;
- `web_build`, `desktop_main_build`, `desktop_preload_build` e `desktop_shared_build`: medem bytes e
  arquivos produzidos pelo último build, incluindo os módulos compartilhados importados pelo Main.

A Issue #48 citava Bundle v3. Desde a introdução de Execution Trust, toda Run nova possui trust e
usa Bundle v4; o contrato v3 rejeita corretamente essas Runs e permanece somente para Runs legadas
sem trust. O cenário mede o dispatcher público `export_run`, que decide pela presença de trust
registrado, e confirma versão 4 em vez de fabricar uma Run legada que o runtime atual não pode
admitir.

`verification_valid` é o resultado dos três eixos de `evidrun.evidence.verify`: checksums exatos,
cadeias de evento e records. Checksum isolado não satisfaz a métrica. O bundle medido é auditável, e
isso não é portabilidade nem replay: o próprio verificador reporta `portable` e `replayable` como
falsos, e este documento não promete nenhum dos dois.

## Estatística e estados

Toda métrica warning usa a mediana das repetições como valor reportado.

A dispersão é a **amplitude relativa**: `(max - min)` dividido pela mediana. Acima de
`methodology.noise_spread_ratio`, o estado é `inconclusive`, não regressão.

A escolha é deliberada e substitui a MAD relativa usada antes. MAD não tem resolução nos tamanhos de
amostra que este repositório configura: com três amostras os desvios da mediana são `[b-a, 0, c-b]`,
cuja mediana é `min(b-a, c-b)`, então um par apertado fixa a MAD perto de zero por mais longe que
esteja a terceira amostra. Medido no perfil real, `crl_ctx_002.duration_ms` reportava MAD relativa
`0.0000` contra amplitude verdadeira de `0.0531`, e a amostra sintética `(100, 101, 1000)` marcava
`0.0099` — um outlier de dez vezes chamado de estável. A amplitude relativa é pessimista de
propósito: reage à pior amostra. Para sinal warning-only essa é a direção segura, porque a
consequência de exagerar ruído é `inconclusive`, nunca build vermelho.

O guarda de ruído só se aplica a grandeza amostrada, isto é, classificação `timing` ou `memory`.
Contagem e bytes lidos do artefato pronto são exatos: chamá-los de inconclusivos esconderia fato que
o checker de fato possui.

Uma amostra estável acima de `baseline * warning_ratio` é `regression`, e continua exit 0.

Quando a medição não existe, o estado é `unavailable` e o documento explica o motivo. Ferramenta
ausente no runner — `pnpm` fora do PATH, por exemplo — é propriedade do ambiente, não política
quebrada: ela produz `unavailable` com JSON emitido, e não aborta o comando. Métrica `unavailable`
usa exit 2 apenas quando é bloqueante, porque aí o gate ficaria sem a proteção que declara ter;
métrica warning-only indisponível é reportada e nada mais, coerente com tempo e memória nunca
bloquearem.

Um valor fora de `minimum`/`limit` bloqueante é `violation` e usa exit 1. Hoje isso protege somente:

- duas Runs, uma Comparison e o bundle verificável do cenário offline;
- seis entradas reais no Artifact Store do CRL-CTX-002;
- versão, resultado da verificação e número de membros do bundle atual;
- bytes e número de arquivos gerados pelas quatro raízes do build.

O checker não afirma que tempo local é comparável entre máquinas nem que pico RSS isolado prova
consumo total do produto. O cenário de bundle mede a duração somente de export/verify; seu pico RSS
é o pico do processo completo, inclusive a preparação necessária. No build, `RUSAGE_CHILDREN`
representa o maior pico observado entre os filhos encerrados, não a soma simultânea de toda a árvore.

## Baseline e revisão de limites

`resource-budget.toml` registra ambiente, metodologia, classificação e baseline. Os valores são
escritos à mão a partir de calibração local, e não existe comando que atualize o arquivo
automaticamente. Isso difere do precedente de `code-budget.toml`, cujo baseline é recomputado por
`--update-baseline`: aqui uma medição depende de máquina e de build real, então recomputar em
qualquer checkout gravaria o ambiente de quem rodou como se fosse política acordada. Mudar um valor
exige o registro revisável descrito abaixo.

O checker lê a política no merge-base e recusa remoção de cenário/métrica ou mudança silenciosa de
workload, repetições, paths, classificação, enforcement, unidade, tolerância a ruído e exclusões de
cache. Essas mudanças exigem um `[[policy_adjustments]]` exato e justificado. Alterar baseline ou
razão de warning exige `[[baseline_adjustments]]`. Qualquer aumento, remoção ou redução de minimum
que relaxe um limite anterior exige um `[[limit_adjustments]]` com cenário, métrica, limites
anterior/novo, `bound` quando for `minimum`, e justificativa concreta.

O registro precisa ser **novo nesta mudança**. Um registro que já existia no merge-base não autoriza
nada: casar apenas contra o arquivo atual permitia que uma aprovação antiga de `8 -> 16` ficasse para
trás depois de um aperto de volta para `8` e reautorizasse silenciosamente o próximo `8 -> 16`, de
modo que uma única justificativa cobriria aquele afrouxamento para sempre.

O lado do merge-base decide sozinho se um limite existia. Sair de `blocking` não retira o limite
antigo sem registro próprio, senão uma mudança de enforcement aprovada carregaria junto um
afrouxamento não registrado.

Lado ausente é nomeado `absent` (não existia no merge-base) ou `removed` (deixou de existir), porque
TOML não tem null: sem essa convenção o checker exigia registro cujo `previous` nenhum autor
conseguia escrever, e adicionar campo de metodologia ficava inautorizável.

Assim o mesmo PR pode propor uma mudança deliberada, mas não pode esconder a regressão apenas movendo
ou retirando a proteção.

Generated outputs, runtime artifacts e caches permanecem classes distintas. Os globs
`classifications.cache_excluded` são aplicados ao inventário; limpar ou aquecer cache não pode fazer
um gate passar.
