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
classifica como determinísticos. Toda métrica warning repetida usa a mesma mediana/MAD, inclusive
tamanho de artifact e banco.

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
sem trust. O cenário mede o dispatcher público e confirma versão 4 e verificação válida, em vez de
fabricar uma Run legada que o runtime atual não pode admitir.

## Estatística e estados

Toda métrica warning com pelo menos três amostras usa a mediana das repetições. O ruído é a mediana
dos desvios absolutos dividida pela mediana (MAD relativa). Acima de
`methodology.noise_mad_ratio`, o estado é `inconclusive`, não regressão. Uma amostra estável acima de
`baseline * warning_ratio` é `regression`, mas continua exit 0. Warning determinístico com uma
amostra compara diretamente seu valor. Se o sistema não produz uma métrica, o estado é
`unavailable`; indisponibilidade de output exigido é erro de medição e usa exit 2.

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

`resource-budget.toml` registra ambiente, metodologia, classificação e baseline. Não existe comando
que atualiza esse arquivo automaticamente. O checker lê a política no merge-base e recusa remoção de
cenário/métrica ou mudança silenciosa de workload, repetições, paths, classificação, enforcement,
unidade, tolerância a ruído e exclusões de cache. Essas mudanças exigem um
`[[policy_adjustments]]` exato e justificado. Alterar baseline ou razão de warning exige
`[[baseline_adjustments]]`. Qualquer aumento, remoção ou redução de minimum que relaxe um limite
anterior exige um
`[[limit_adjustments]]` com cenário, métrica, limites anterior/novo, `bound` quando for `minimum`, e
justificativa concreta. Assim o mesmo PR pode propor uma mudança deliberada, mas não pode esconder a
regressão apenas movendo ou retirando a proteção.

Generated outputs, runtime artifacts e caches permanecem classes distintas. Os globs
`classifications.cache_excluded` são aplicados ao inventário; limpar ou aquecer cache não pode fazer
um gate passar.
