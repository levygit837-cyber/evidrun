---
id: planning-task-default-authoring-authority
type: implementation-task
title: WS-03 Decisao de autoria default no produto instalado
status: accepted
authority: planning
volatility: snapshot
owner: governance
created_at: 2026-07-23
updated_at: 2026-07-28
observed_at: 2026-07-28
review_due: 2026-08-28
applies_to: control-plane-trust
sources:
  - docs/adr/0010-verifiable-human-authority.md
  - docs/adr/0015-human-subject-envelope-and-authenticator-lifecycle.md
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/adr/0022-explicit-execution-trust-without-per-run-authentication.md
  - docs/architecture/agents-and-authority.md
  - docs/contracts/execution-trust-v1.md
  - docs/planning/mvp-implementation-roadmap.md
  - docs/planning/tasks/40-trust-sandbox-review-package.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-03 — Decisao de autoria default

`workstream_state: done_on_main`

## Resultado

A decisao normativa esta fechada no
[ADR 0022](../../adr/0022-explicit-execution-trust-without-per-run-authentication.md), e o contrato
que a implementacao deve consumir esta em
[Execution Trust v1](../../contracts/execution-trust-v1.md). Esta entrega e exclusivamente
documental: nao cria ainda o caminho de execucao nao verificada.

O produto adotara como caminho cotidiano uma Run explicitamente nao verificada, sem exigir uma
cerimonia WebAuthn a cada execucao. Uma revisao humana autenticada continua disponivel como caminho
opt-in e futuro, mas so ela pode produzir um claim de autoridade humana.

## Decisao registrada

- O record final e `ExecutionTrustRecord`.
- Os estados sao `unverified_revision_set` e `verified_revision_set`.
- O pacote executado e selado por uma closure versionada e fechada de refs transitivas do Study,
  sempre com digests exatos, ordenacao deterministica e `project_id` explicito.
- O digest e SHA-256 do JSON canonico dessa closure e fica ligado ao digest de um unico RunSpec.
- O caminho nao verificado aceita `network=provider_only` quando o provider e as capabilities forem
  admitidos; dados `sensitive`/`restricted` e efeitos externos continuam rejeitados.
- Trust e isolamento sao eixos independentes. A UI mostra ambos em texto e nunca usa `sandbox` como
  sinonimo de revisao ou de verificacao humana.
- A marca de trust aparece em listas, detalhes, bundle e representacoes para impressao. Cor ou icone
  podem reforcar a diferenca, mas o texto continua presente para sobreviver a export, impressao em
  escala de cinza e captura de tela.
- Uma revisao humana posterior nao promove nem reescreve a Run antiga. Evidencia verificada exige
  decisions humanas append-only, novo `ExecutionTrustRecord`, nova admissao e nova Run.
- `LocalWebAuthnVerifier` e `KeyringAuthenticator` permanecem como compatibilidade/opt-in. Tornar a
  autenticacao local mais simples e default e trabalho futuro; WebAuthn nao e dependencia do WS-40.

## Como o selamento evita troca silenciosa

O selamento nao guarda uma aprovacao vaga do nome do Study. Ele guarda uma lista fechada das
revisoes exatas que formam o experimento: Study, Goal, Scenarios, Agent Inventories, Run Environment
Template, Interaction Protocol, EvaluationPlan e policies opcionais alcancadas pelo Study.

Cada ref leva seu digest de conteudo. A lista e ordenada e serializada pelo formato canonico ja
usado no repositorio; o SHA-256 dessa representacao produz `revision_set_digest`. Como a identidade
atual de uma revision nao inclui Project no proprio digest, `project_id` entra explicitamente no
selamento. O record tambem aponta para `run_spec_digest`.

Assim, qualquer uma destas mudancas produz outro selo:

- trocar uma revision por outra;
- mudar o conteudo mantendo a mesma identidade logica;
- acrescentar ou remover uma dependencia transitiva;
- mover o pacote para outro Project;
- compilar outro RunSpec.

Nao existe resolucao por `latest`, aprovacao de refs futuras nem reaproveitamento entre Projects.

## Rotulo visual recomendado

O requisito de “sobreviver a export, impressao e captura de tela” significa que o estado nao pode
depender apenas de uma borda colorida, um cadeado ou um tooltip. O contrato de apresentacao minimo e
texto explicito em toda representacao da Run:

```text
Trust: Nao verificada — sem confirmacao humana
Isolamento: in_process
```

Quando houver revisao humana valida, a primeira linha muda para `Trust: Revisao humana verificada`.
Quando um sandbox real existir e for comprovado pelo runtime, somente a segunda linha muda. Esta
separacao impede que “nao verificada” pareca insegura por definicao ou que “sandbox” pareca autoridade
humana.

## Invariantes preservados

- agente, automacao e servico nunca se declaram humanos;
- autoridade humana continua exigindo `HumanAttestationRecord` verificado;
- `repository_fixture` continua restrito ao import canonico completo `CRL-CTX-002`;
- a Run nao existe antes de admissao do RunSpec exato;
- o runtime ativo continua rejeitando `sensitive` e `restricted`;
- records e Runs permanecem append-only;
- nenhum documento desta entrega descreve `ExecutionTrustRecord` ou execucao nao verificada como
  comportamento ja implementado.

## Handoff para implementacao

O WS-40 esta normativamente desbloqueado. Ele deve implementar, nessa ordem:

1. closure e digest deterministas;
2. `ExecutionTrustRecord` e persistencia append-only;
3. compilacao/admissao nao verificada com as restricoes obrigatorias;
4. ligacao entre trust, RunSpec, Run, ledger e bundle;
5. API/CLI e testes de claim confusion;
6. projecao do `ReviewPackage` para leitura humana.

A UI completa permanece no WS-51. Nao ha questao normativa aberta que o WS-40 precise decidir por
conta propria. Mudanca futura no mecanismo de autenticacao local exige ADR sucessor.

## Verificacao desta entrega

Como este workstream nao altera `src/` nem `apps/`, o gate focal e:

```bash
uv run python scripts/validate_docs.py
```

Os gates completos permanecem obrigatorios para o WS-40, que alterara comportamento.
