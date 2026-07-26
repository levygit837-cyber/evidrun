---
id: planning-task-domain-seams
type: implementation-task
title: WS-11/12 Costuras do dominio para paralelismo real
status: verified
authority: planning
volatility: snapshot
owner: core
created_at: 2026-07-23
updated_at: 2026-07-25
observed_at: 2026-07-25
review_due: 2026-08-07
applies_to: domain-seams
sources:
  - docs/planning/mvp-implementation-roadmap.md
  - docs/architecture/codebase-layout.md
  - docs/adr/0017-structural-budget-and-named-seams.md
  - docs/adr/0003-modular-monolith.md
  - docs/adr/0014-durable-runtime-kernel.md
  - docs/contracts/study-run-v1.md
  - docs/contracts/agent-inventory-workspace-v1.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/infrastructure/database/repository.py
  - src/evidrun/infrastructure/database/unit_of_work.py
  - src/evidrun/contracts/admission/service.py
  - src/evidrun/contracts/admission/envelope.py
  - src/evidrun/runs/admission/catalog_checks.py
  - code-budget.toml
verification_refs:
  - tests/unit/test_admission_oracle.py
  - tests/unit/admission_oracle.json
  - tests/integration/test_runtime_queue.py
  - tests/unit/test_code_budget.py
---

# WS-11/12 — Costuras do dominio

`workstream_state: delivered`

WS-11 aterrissou em `812b330` (PR #20) e WS-12 em `62ddec8` (PR #21). O bloqueio pela Onda 0 foi
dispensado: as frentes WS-01/02/03 mudam superfície de workspace, lifecycle desktop e autoria, e
nenhuma delas tocou `repository.py`, `compiler.py` ou `adapters.py` no intervalo, então o refactor não
competiu com mudança de superfície.

## O que foi entregue

**WS-11.** `Repository` deixou de ser um God Object: `repository.py` tem 53 linhas e é raiz de
composição sobre nove agregados que compartilham um `UnitOfWork`. Ordem de extração seguida como
especificado (`read_model` → `registry` → `evaluation` → `catalog` → `ledger` → `queue`), com a suíte
obrigatória completa verde entre cada agregado. Atomicidade de `claim_next_job` e
`prepare_run_execution` medida por listener DBAPI e comparada contra worktree do commit base:
`begin`/`commit` idênticos nos dois lados.

**WS-12.** `AdmissionService.admit` virou orquestração de checkers puros `(spec, envelope) -> findings`
em `contracts/admission/`, e a segunda camada foi nomeada em `runs/admission/`. O envelope virou
objeto explícito (`RuntimeCapabilityEnvelope`), produzido apenas por
`RuntimeAdapterCatalog.capability_envelope()` e exposto como mapping read-only. A camada dona de cada
eixo de sobreposição está registrada em
[Layout da codebase](../../architecture/codebase-layout.md).

**O oráculo existe.** `tests/unit/test_admission_oracle.py` percorre 62 RunSpecs cobrindo cada ramo de
rejeição das duas camadas e trava decisão, statuses, `missing_requirements`, `denied_policies`,
warnings, inventário resolvido e a tripla `(category, subject_ref, reason.code, reason.detail,
blocking)` byte a byte contra `tests/unit/admission_oracle.json`. Os cinco ramos que o snapshot
apontava sem cobertura nenhuma passaram a ser exercitados. 60 dos 62 casos são byte-idênticos ao
baseline pré-refactor.

**Nenhuma capability foi promovida.** As nove condições de ataque continuam rejeitadas com a mensagem
exata, travadas em teste permanente.

**Baseline removido.** `code-budget.toml` perdeu a entrada `function_lines=481` de `repository.py`
(entrada inteira) e a `function_lines=567` de `compiler.py`; `file_lines` de `compiler.py` apertou de
1156 para 530. Nada foi adicionado ou aumentado; `--update-baseline` não rodou.

## Defeito latente encontrado e corrigido

A condição de escalação "as duas camadas discordarem para algum spec real" não ocorreu, mas outra sim:
ao exercitar pela primeira vez o ramo de provider indisponível, `admit` levantava `ValidationError` em
vez de devolver `decision=rejected`. Preenchia `provider_profile_id` sem digest, model, reasoning e
adapter, combinação que `ResolvedAgentInventory` rejeita. Alcançável pela composição de produção, com
zero cobertura anterior. Foi escalado ao humano conforme o brief manda, e a decisão registrada foi
corrigir dentro de WS-12: um profile não resolvido agora deixa o bloco de provider inteiro vazio.

## Resultado pratico

Depois desta entrega, tres frentes independentes conseguem adicionar capability sem editar o mesmo
trecho de arquivo. Hoje elas nao conseguem: toda capability nova exige um `if` novo na mesma funcao de
admissao e um metodo novo na mesma classe de persistencia.

O resultado observavel e negativo por definicao: **nada muda para quem usa o sistema**. Mesmas
decisoes, mesmas mensagens, mesma evidencia, mesma suite verde. O ganho e estrutural.

## Snapshot inicial

Fatos medidos em 2026-07-24. Redescubra cada um antes de editar: o refactor invalida contagem de
linha rapidamente, e `uv run python scripts/check_code_budget.py --json` da o numero atual.

O layout-alvo, a arvore de arquivos e o grafo de conversa entre pastas estao em
[Layout da codebase](../../architecture/codebase-layout.md). Este brief nao redefine o alvo; ele
executa a parte de `Repository` e admissao.

### O God Object de persistencia

`src/evidrun/infrastructure/database/repository.py`: 2942 linhas, uma classe `Repository`, 72 metodos
dos quais 50 publicos. Seis agregados convivem sem costura entre eles — ledger (~700 linhas),
fila/lease (~640), contract registry (~250), evaluation/checkpoint (~510), catalog (~380) e read-model
(~380). A tabela agregado-a-agregado com linhas e fronteira transacional esta em
[Layout da codebase](../../architecture/codebase-layout.md).

Dois fatos medidos decidem o desenho:

1. **Nenhum metodo publico recebe sessao.** Todos abrem `with self.database.session()`. O unico que
   opera dentro de sessao alheia e `_append_event_once_in_session`, um `@staticmethod` que recebe
   `session` explicitamente. A costura de sessao ja existe como convencao privada; a decomposicao a
   promove a modulo (`unit_of_work.py`), nao a inventa.
2. **O estado de instancia e `self.database` e `self.human_attestation_verifier`.** Sem cache mutavel
   compartilhado, a decomposicao pode ser por composicao de colaboradores.

So `update_run` e `project_id_for_run_spec` nao tem chamador externo. Os outros 48 publicos sao
interface real: a extracao e migracao de chamadores, nao renomeacao interna.

### A decisao de admissao fatiada em duas camadas

`AdmissionService.admit` (compiler.py:462-1029) faz 26 checagens em 567 linhas acumulando `missing`,
`denied_policies`, `warnings` e `issues`. Na linha 990 ela roda `self.execution_validators`, que
`RuntimeAdapterCatalog.admission_service()` (adapters.py:756-765) preenche com `self.validate_spec`.
**Toda chamada a `admit()` executa as duas camadas, sempre.**

A divisao real, hoje nao declarada em lugar nenhum:

- `admit` decide contra um **envelope de capacidade declarado** que o catalogo injeta:
  `network_modes`, `supported_budget_fields`, `supports_raw_encrypted_capture`,
  `runtime_capabilities`, `workspace_runtime_kinds`, `interaction_modes`, `external_effect_modes`;
- `validate_spec` + `_validate_scripted_spec` + `_validate_real_spec` (adapters.py:767-992) fazem 24
  checagens contra o **par concreto de adapters** resolvido para aquele RunSpec.

Nao ha duplicata textual: nenhuma checagem produz mensagem identica nas duas camadas. Ha sobreposicao
semantica confirmada em quatro eixos, onde envelope e adapter afirmam a mesma verdade por caminhos
diferentes:

| Eixo | No envelope (`admit`) | No adapter (`validate_spec`) |
| --- | --- | --- |
| rede | `network_modes` (compiler.py:744) | `offline_network` (adapters.py:894), `provider_network` (964) |
| capture | `supports_raw_encrypted_capture` (813) | `offline_raw_capture` (908), `recoverable_subject_output` (980) |
| budgets | `supported_budget_fields` (936) | `offline_tool_budget` (901), `max_tool_calls` (973) |
| evaluator | `runtime:evaluation_pipeline` (890) | `evaluator_adapter` (862), `scripted_evaluator` (873), `real_evaluator` (921) |

`admission_service()` monta o envelope a mao a partir dos mesmos adapters que `validate_spec`
inspeciona. Sao duas leituras da mesma verdade sincronizadas por atencao humana. Isso nao e bug
observavel hoje; e o mecanismo pelo qual uma capability nova pode ser promovida por acidente em um
lado so.

### A rede de seguranca nao cobre o que o refactor pode quebrar

**Nenhum teste asserta `reason.code` nem `reason.detail`.** A suite trava decisao
(`admitted`/`rejected`) e tokens de `missing_requirements`, nao as mensagens observaveis. Trocar uma
mensagem ou um codigo de rejeicao hoje passa verde.

Ramos sem cobertura nenhuma:

- digest divergente de runner no registry (`runner.digest != spec.agent_inventory.runner_ref.digest`,
  compiler.py:468) — o teste de digest existente pega o artifact, nao o runner;
- `mount_authority` (compiler.py:699) e `read_write_mount` (712);
- `runtime_kind` nao suportado (673);
- `credential_available=False` em `_validate_real_spec` (adapters.py:936).

Consequencia direta: **o oraculo do passo 1 nao e opcional nem cerimonia.** Sem ele, "sem perda de
precisao" e uma afirmacao sem evidencia.

## Dependencias e ownership de paths

Pode editar:

- `src/evidrun/infrastructure/database/repository.py` e os modulos novos sob
  `src/evidrun/infrastructure/database/` previstos no layout-alvo (`unit_of_work.py`, `ledger/`,
  `queue/`, `registry.py`, `evaluation/`, `catalog.py`, `read_model/`);
- `src/evidrun/contracts/compiler.py` e os modulos novos sob `src/evidrun/contracts/admission/`;
- `src/evidrun/runs/adapters.py`, apenas na parte de validacao de spec, e os modulos novos sob
  `src/evidrun/runs/admission/`;
- `src/evidrun/runs/composition.py`, se a composicao precisar acompanhar as novas colaboracoes;
- `code-budget.toml`, apenas para REMOVER entradas de baseline que a extracao tornou obsoletas;
- os testes existentes, somente para acompanhar assinatura, nunca para afrouxar expectativa.

Nao pode editar:

- nenhum documento em `docs/contracts` ou `docs/adr`, porque esta entrega nao muda contrato;
- `src/evidrun/contracts/runtime.py` e `authoring.py` na parte de shape de contrato;
- `src/evidrun/evidence/bundle.py`, que tem ownership da WS-30;
- nada em `apps/`.

Esta e uma linha serial. Ela nao compartilha onda com WS-20, WS-30 ou WS-40 — e exatamente o arquivo
que essas frentes consomem, e por isso precisa aterrissar antes delas.

## Invariantes que nao podem ser relaxadas

- **Refactor nao promove capability.** Toda capability hoje rejeitada continua rejeitada, com o mesmo
  codigo (`unsupported`, `denied`, `unavailable`) e a mesma mensagem observavel. Como a suite atual
  nao asserta mensagem nem codigo, o oraculo do passo 1 e a unica rede real.
- **A fronteira transacional e o risco principal, nao a contagem de linhas.** `claim_next_job` usa
  `BEGIN IMMEDIATE` com expiracao de lease e incremento de geracao; `prepare_run_execution` roda como
  transacao unica com fencing. Decompor por agregado nao pode transformar uma transacao em duas.
  Quando a atomicidade e o objeto do design, mantenha o metodo junto do seu agregado e passe a
  sessao via `unit_of_work`, nunca reabra uma sessao aninhada.
- **O ledger continua a autoridade normativa da Run** (AGENTS.md). Ordem, hash chain, validade por
  fase e os event types reservados permanecem impostos no mesmo ponto logico.
- **Fronteiras do AGENTS.md:** o dominio Python nao importa FastAPI, SQLAlchemy, OpenAI, Electron ou
  React. A decomposicao vive na camada de infraestrutura e nao vaza ORM para o dominio.
- **ADR aceito nao e reescrito.** Se a decomposicao exigir mudanca normativa, pare e proponha um ADR
  sucessor. O ADR 0017 ja cobre orcamento e costuras nomeadas; qualquer coisa alem dele e ADR novo.
- **O orcamento so aperta.** Entrada de `[baseline]` em `code-budget.toml` pode ser removida quando o
  arquivo cabe no orcamento, nunca aumentada. `--update-baseline` nao e parte deste trabalho.

## Loop de trabalho

1. **Descobrir.** Antes de mover codigo, construa o oraculo: para um conjunto de RunSpecs cobrindo
   cada ramo de rejeicao das DUAS camadas, registre decisao, `missing_requirements`,
   `denied_policies`, e para cada issue a tripla `(category, subject_ref, reason.code, reason.detail)`.
   Inclua os cinco ramos hoje sem cobertura listados no snapshot. Esse baseline e o oraculo do
   refactor e deve virar teste permanente, porque hoje ele nao existe de forma reutilizavel.
2. **Implementar WS-11.** Extraia um agregado por vez, nesta ordem: `read_model` (menor acoplamento
   transacional) → `registry` → `evaluation` → `catalog` → `ledger` → `queue` (maior acoplamento, por
   ultimo). Introduza `unit_of_work.py` antes do primeiro agregado que precise de sessao compartilhada.
   Depois de cada extracao, suite obrigatoria completa verde e uma entrada de baseline removida.
3. **Implementar WS-12.** Converta `admit` em composicao de checkers por familia (ver layout-alvo),
   cada um com assinatura `(spec, envelope) -> issues`. Torne o envelope um objeto explicito
   (`RuntimeCapabilityEnvelope`) produzido por `runs/adapters/catalog.py`, em vez de oito kwargs
   montados a mao. Para cada eixo de sobreposicao da tabela do snapshot, escolha uma camada dona e
   registre a escolha; cada checker precisa produzir exatamente o mesmo issue que a checagem que
   substitui.
4. **Atacar.** Tente promover uma capability por acidente: spec com dois stages de evaluation, com
   `checkpoint_policy`, com `progress_artifact_policy`, com disclosure diferente de `none`, com
   `bounded_exploration`, com `max_turns > 1`, com `runtime_kind` fora de `in_process`, com mount
   `read_write`, e com credencial de provider ausente. Todos devem continuar rejeitados com a mesma
   mensagem. Tente tambem um event type reservado e uma escrita de lease sem fencing.
5. **Reparar.** Qualquer divergencia contra o oraculo e regressao, nao melhoria.

## Condicoes de parada e escalacao

Pare e escale se:

- preservar a atomicidade exigir mudar o contrato de uma transacao existente;
- a consolidacao de um eixo de sobreposicao entre `admit` e `validate_spec` revelar que as duas
  camadas hoje discordam para algum spec real — isso e defeito latente e precisa de decisao explicita
  antes de ser congelado num checker;
- a decomposicao exigir alterar a ordem de eventos ou o conteudo de um record persistido;
- um dos cinco ramos sem cobertura revelar comportamento diferente do que o codigo sugere ao ser
  exercitado pela primeira vez.

## Testes focais e gates

Focais: a suite existente inteira mais o oraculo, com atencao a `tests/integration/test_runtime_queue.py`,
`test_runtime_kernel.py`, `test_admission_and_evaluation.py`, `test_contract_migration.py` e
`tests/acceptance/`. O oraculo de equivalencia de decisao de admissao e entrega obrigatoria deste
workstream, nao opcional.

Gates: a suite obrigatoria completa do `AGENTS.md`, que inclui
`uv run python scripts/check_code_budget.py`.

## Handoff

Entregue base SHA, head SHA e branch; os agregados extraidos e a fronteira transacional de cada um;
a tabela de equivalencia de decisao antes e depois; qual camada ficou dona de cada eixo de
sobreposicao e por que; qualquer discordancia encontrada entre as duas camadas de validacao; as
entradas de `[baseline]` removidas de `code-budget.toml`; e a confirmacao explicita de que nenhuma
capability foi promovida.
