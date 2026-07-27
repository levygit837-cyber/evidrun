---
id: architecture-system
type: architecture
title: Arquitetura do sistema
status: implemented
authority: normative
volatility: current
owner: core
created_at: 2026-07-22
updated_at: 2026-07-27
applies_to: repository
sources:
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun
  - apps/web
  - apps/desktop
verification_refs:
  - tests/acceptance/test_demo_flow.py
  - tests/integration/test_admission_and_evaluation.py
  - tests/integration/test_contract_api.py
  - tests/integration/test_runtime_kernel.py
  - tests/integration/test_runtime_queue.py
---

# Arquitetura do sistema

O Evidrun é um monólito modular com três planes:

- **Control Plane:** Workspaces, Projects, Studies, revisions, decisões humanas e chats; é onde vive o Lab Agent,
  copiloto do laboratório com escopo funcional amplo e sem autoridade humana
  ([ADR 0018](../adr/0018-lab-agent-copilot-scope.md)). Seu runtime ainda não existe.
- **Execution Plane:** compilador, admissão, coordinator, worker, Subject Runner e Run Environment.
- **Evidence Plane:** event ledger, snapshots, artifacts, checkpoints, evaluations e bundles.

Workspace é a raiz durável de isolamento do Control Plane; Project é a linha de investigação filha e
fronteira de autoria/proveniência. Run Environment é efêmero por Run e vem de configuração
versionada, nunca de um mount implícito do Workspace. O schema v1 ainda usa
`WorkspaceTemplateRevision`/`RunSpec.workspace`; esses nomes de compatibilidade não unem os dois
conceitos. A superfície pública e a unicidade de Workspace/Project estão aceitas, mas ainda não
implementadas; hoje existem somente writes internos e listagens derivadas do dashboard.

O fluxo novo é `StudyRevision aceita → compilação → RunSpec → admissão → Run → eventos`. Revisions,
specs e admissions são imutáveis. Checkpoints e evaluations se ancoram a sequence/hash do ledger.
Status, comparison, Grade, relatório e grafo permanecem projeções.

`RunRow.status` é um cache operacional. O repository valida a máquina de estados e avança a coluna
na mesma transação que grava cada evento de lifecycle; `update_run` não aceita mudança direta de
status. O event ledger continua sendo a autoridade normativa e permite verificar ou reconstruir
essa projeção.

Eventos factuais são aceitos somente na fase permitida e com seus records canônicos ligados.
Invocações e respostas do Subject são pareadas; evaluation só começa depois de uma resposta;
`evaluation.completed` aponta para o EvaluationRecord exato; e `run.completed` exige os records e
stages requeridos pelo EvaluationPlan. O coordinator fechado de `read_text` publica
`capability.offered` e pares `tool.called`/terminal cercados por lease. Eventos de pause/resume,
outras tools, skills, checkpoint e Progress Artifact permanecem reservados enquanto seus
coordinators não existem.

Superfícies:

- CLI Python;
- FastAPI em loopback;
- worker local;
- React renderer;
- Electron Main e preload.

Electron gerencia o lifecycle do backend, mas não contém regras de domínio. O React usa a mesma API
no browser e no aplicativo desktop. SQLite é canônico localmente; JSONL é exportação.

O Runtime Kernel executa jobs persistidos em SQLite/WAL por um worker separado. O catálogo ativo é
compartilhado pela admissão e pelo coordinator: uma combinação sem runner e evaluator completos é
rejeitada antes do enqueue. Claim cria attempts com lease e fencing; restart ou lease expirado retoma
a mesma Run sem permitir writes do worker antigo. O demo usa esse mesmo kernel, embora drene seus
jobs sincronamente para preservar sua interface histórica.

O runtime admite apenas `single_turn`, Run Environment `in_process` e capabilities catalogadas. Um protocolo
em grafo é tipável e compilável, mas rejeitado na admissão. Dois pares completos estão ativos: o
runner scripted com grader legado offline e o Responses read agent com grader exato fundamentado em
tool result. Cada par cobre um único stage booleano determinístico; model judge, human review e
adjudicação continuam indisponíveis para execução pública.

O adapter offline recebe somente objective e context. O adapter real recebe objective, inventário de
inputs e o schema fechado de `read_text`; os resultados vêm apenas de artifacts já materializados no
SubjectEnvelope. Ambos executam uma única interação e aplicam `max_wall_seconds`. O adapter real
também aplica `max_tool_calls`; rounds internos de provider/tool não são turnos adicionais. Timeout ou
estouro grava `run.budget_exhausted`, nunca `run.completed`. Budgets de tokens ou custo,
`max_turns > 1`, pause e stops fora de `goal_complete`/`budget_exhausted` terminal bloqueiam a
admissão. Todo disclosure de evaluation diferente de `none` também bloqueia a admissão.

A admissão também falha fechado para checkpoint coordinator, Progress Artifact observer, pipeline de
evaluation fora do grader determinístico suportado, adjudicação humana required, disclosure dinâmico
e terminal de bounded exploration. Esses contratos serem tipáveis e compiláveis não anuncia
capacidade executável. Decisions humanas possuem schema e verifier protocol, mas API/CLI recusam o
fluxo enquanto não houver adapter WebAuthn confiável.

O SubjectEnvelope materializado é persistido antes de `subject.invoked` e referencia o input
selecionado em CAS. Resposta raw autorizada é cifrada por projeto e pode ser retomada depois de crash
sem reinvocar o provider. Evidence Bundle v3 exporta RunSpec, AdmissionRecord, revisions, ledger,
evaluations, SubjectEnvelope quando materializado, job, attempts e refs de tool/output para
verificação isolada, sem afirmar portabilidade ou replay.
