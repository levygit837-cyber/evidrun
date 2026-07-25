---
id: planning-mvp-implementation-roadmap
type: roadmap
title: Roadmap executavel ate o MVP operacional
status: accepted
authority: planning
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-25
observed_at: 2026-07-25
review_due: 2026-08-07
applies_to: mvp-implementation
sources:
  - docs/roadmap/mvp.md
  - docs/planning/mvp-capability-map.md
  - docs/product/charter.md
  - docs/governance/delivery-status.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Roadmap executavel do MVP

## Resultado de produto

O MVP nao exige Canvas, nested agents ou replay. Ele exige que um usuario consiga, pelo aplicativo
local, transformar uma hipotese em uma Run auditavel sem editar o banco ou chamar scripts internos.

## O que ja atravessa o pipeline

O corredor canonico foi exercitado ponta a ponta em `main` usando somente superficies publicas:

```text
contract register -> authority accept -> study compile -> run admit -> run enqueue
  -> worker --once -> run.completed -> bundle export -> bundle verify
```

O ledger emitiu a sequencia completa (`run.queued`, `run.preparing`, `context.composed`,
`run.running`, `subject.invoked`, `subject.responded`, `run.evaluating`, `evaluation.completed`,
`run.completed`) e o Bundle v3 verificou todos os grupos de records.

Isso significa que o problema do MVP **nao e** a espinha de execucao. A espinha existe e e auditavel.
O problema e que ela esta inalcancavel para um usuario e estreita demais para um Study real.

## Os tres bloqueios que impedem uso

Estes bloqueios foram reproduzidos, nao inferidos. Nenhum deles e uma capability nova: sao lacunas de
superficie e de lifecycle em cima de dominio que ja funciona.

| # | Bloqueio | Evidencia observada |
| --- | --- | --- |
| B1 | Nao existe como criar Workspace ou Project | Banco novo tem zero projects. `create_workspace`/`create_project` existem apenas como metodos de `Repository`; nao ha comando CLI nem rota `POST`. `contract register` falha com `FOREIGN KEY constraint failed`. O unico caminho e `evidrun demo`, que importa a fixture legada. |
| B2 | O desktop empacotado nunca processa Runs | `backend-lifecycle.ts` faz spawn de `evidrun serve --desktop-handshake`; `serve` sobe apenas uvicorn. Nenhum path do produto inicia `evidrun-worker`. A UI enfileira Runs que ninguem executa. |
| B3 | Autoria verificada e opt-in e desligada por padrao | `Settings.authority_enabled` default `False`. Sem `EVIDRUN_AUTHORITY=1`, `StudyCompiler.resolve` recusa toda revision, porque `decide` exige verifier confiavel. Por padrao o unico corredor que aceita revisions e o `repository_fixture` nao humano. |

Corrigido neste ciclo, pela mesma investigacao: a CLI reconstruia `Repository` sem verifier, entao
gravava aceitacao verificada que ela mesma nao conseguia reler; `authority accept` sobrescrevia o
verifier ignorando o gate do ADR 0015; e `contract accept` era um stub morto que duplicava
`authority accept`.

## Por que esta ordem

A ordem nao segue a numeracao dos workstreams. Ela segue duas perguntas: *o que torna o produto
utilizavel* e *o que precisa existir antes de varias frentes poderem editar em paralelo*.

1. **Espinha alcancavel primeiro.** Enquanto B1/B2/B3 existem, qualquer capability nova nasce
   inalcancavel. Uma feature que so pode ser exercitada por teste de integracao nao e entrega de
   produto. Estes tres itens sao pequenos, independentes entre si e desbloqueiam todo o resto.
2. **Costuras antes da largura.** Tres arquivos concentravam o que WS-20, WS-30 e WS-40 precisam
   editar: `Repository`, `AdmissionService.admit` e `RuntimeAdapterCatalog.validate_spec`, que
   duplicava parte da decisao de admissao. Toda capability nova exigia um `if` novo na mesma funcao e
   um metodo novo na mesma classe. As duas costuras foram abertas na Onda 1: hoje uma capability nova
   nasce em `contracts/admission/checks/` mais o envelope do catalogo, e uma escrita nova nasce no
   agregado dono da sua atomicidade.
3. **Largura depois.** Com superficie utilizavel e costuras abertas, as frentes de evidencia,
   artifacts e confianca sao genuinamente independentes e podem correr juntas.
4. **Frontend por ultimo, por dependencia real.** A pagina Observability ja consome endpoints reais.
   O wizard de Create so pode deixar de ser rascunho local quando existir criacao de Project e um
   caminho de aceitacao usavel. Laboratory so deixa de ser mock quando o Lab Agent existir. Integrar
   UI antes disso produz tela que mente.

## Ondas de execucao

### Onda 0 — espinha alcancavel

Tres fatias independentes, sem arquivo compartilhado entre elas. Executam em paralelo.

- **WS-01 Superficie de Workspace/Project:** rotas `POST` e comandos CLI, com os mesmos invariantes
  do dominio. Resolve B1.
- **WS-02 Lifecycle do worker no desktop:** o app local passa a supervisionar execucao, nao apenas a
  API. Resolve B2. Inclui reinicio observavel e o gate de CI que hoje nao roda (`test:handshake`).
- **WS-03 Decisao de autoria default:** ADR sucessor que define como um usuario aceita uma revision
  no produto instalado, sem afirmar falsa autoridade humana. Resolve B3 e fixa o contrato que a
  WS-40 vai implementar.

WS-03 e decisao, nao codigo: ela precisa aterrissar antes da Onda 2 porque define o vocabulario de
trust que WS-40 e o frontend consomem.

### Onda 1 — costuras do dominio (entregue)

Serial e inline por natureza: e exatamente o trabalho que todos os demais consomem. Aterrissou em
`812b330` (PR #20) e `62ddec8` (PR #21).

- **WS-11 Fatiar `Repository` por agregado:** entregue. `repository.py` tem 53 linhas e e raiz de
  composicao sobre nove agregados que compartilham um `UnitOfWork`. Ledger, fila/lease, contract
  registry, evaluation/checkpoint, catalog e read-model sao colaboradores separados. A atomicidade de
  `claim_next_job` e `prepare_run_execution` foi medida contra o commit base e nao mudou.
- **WS-12 Registro de checkers de admissao:** entregue. `admit` virou orquestracao de checkers puros
  `(spec, envelope) -> findings` em `contracts/admission/`, e `validate_spec` foi nomeada como segunda
  camada em `runs/admission/`. O envelope virou objeto explicito produzido apenas pelo catalogo.

Criterio de saida cumprido: nenhuma mudanca de comportamento observavel, suite completa verde, e a
mesma decisao de admissao para os mesmos specs — travada por um oraculo de equivalencia de 62 casos
que compara decisao, statuses, requisitos, politicas negadas e a mensagem exata de cada issue byte a
byte. Um defeito latente encontrado ao exercitar o ramo de provider indisponivel pela primeira vez foi
escalado e corrigido: `admit` levantava `ValidationError` em vez de devolver `decision=rejected`.

### Onda 2 — largura real

Paralelo amplo. Cada frente tem ownership de arquivo distinto depois das costuras.

- **WS-20 Artifact access e capture:** grants, materialization records e enforcement de capture.
- **WS-30 Evaluation executavel:** multiplos stages, model judge, CheckpointCoordinator e
  ProgressObserver.
- **WS-40 Trust modes e ReviewPackage:** implementa a decisao da WS-03.
- **WS-41 Contratos tipados de HTTP:** os DTOs de resposta consumidos pelo frontend passam pelo
  gerador, fechando o drift que hoje existe entre `apps/web/src/types.ts` e os schemas reais.

### Onda 3 — laboratorio util

- **WS-50 Lab Agent e bounded exploration.**
- **WS-51 Integracao do frontend:** Create passa a criar entidades reais; Laboratory passa a
  consumir o Lab Agent; a UI distingue `sandbox`, `verified`, `rejected`, `failed` e `unsupported`.

### Onda 4 — fechamento

Dossiers determinístico, com modelo real e bounded; fluxo sandbox e fluxo verificado; E2E web +
sidecar + worker; threat review e recovery; documentacao atualizada somente depois da evidencia.

## Grafo de dependencias

```mermaid
flowchart LR
    W01["WS-01 Workspace/Project"] --> SEAM
    W02["WS-02 Worker no desktop"] --> SEAM
    W03["WS-03 Autoria default (ADR)"] --> SEAM
    SEAM["WS-11/12 Costuras"] --> W20["WS-20 Artifacts"]
    SEAM --> W30["WS-30 Evaluation"]
    SEAM --> W40["WS-40 Trust"]
    SEAM --> W41["WS-41 Tipos HTTP"]
    W03 --> W40
    W20 --> W50["WS-50 Lab Agent"]
    W30 --> W50
    W40 --> W50
    W41 --> W51["WS-51 Frontend"]
    W50 --> W51
    W51 --> MVP["MVP operacional"]
```

## Workstreams e cortes

| ID | Workstream | Dependencias | Paralelo com | Nao inclui |
| --- | --- | --- | --- | --- |
| WS-01 | Superficie de Workspace/Project | nenhuma | WS-02, WS-03 | autoria assistida, importacao em massa |
| WS-02 | Lifecycle do worker no desktop | nenhuma | WS-01, WS-03 | packaging assinado, distribuicao publica |
| WS-03 | Decisao de autoria default | nenhuma | WS-01, WS-02 | implementacao de sandbox (e WS-40) |
| WS-11 | Fatiar `Repository` | Onda 0 | serial | mudanca de comportamento |
| WS-12 | Registro de checkers de admissao | WS-11 | serial | promover capability rejeitada |
| WS-20 | Artifact access/capture | costuras | WS-30, WS-40, WS-41 | portable bundle, restricted data |
| WS-30 | Evaluation/checkpoint/progress | costuras | WS-20, WS-40, WS-41 | restore, replay, fork |
| WS-40 | Trust sandbox/ReviewPackage | WS-03 + costuras | WS-20, WS-30, WS-41 | falsa aceitacao humana |
| WS-41 | Contratos tipados de HTTP | costuras | WS-20, WS-30, WS-40 | redesenho de API |
| WS-50 | Lab Agent/bounded exploration | WS-20 + WS-30 + WS-40 | WS-51 parcial | nested agents, efeitos externos |
| WS-51 | Integracao do frontend | WS-41 + WS-50 | — | Canvas, replay |

## Gates entre ondas

Uma onda nao e promovida porque os arquivos existem. O gate exige:

1. branch atualizada com `origin/main`;
2. migrations lineares testadas em banco vazio e banco legado;
3. testes adversariais para bypasses de authority, envelope e ledger;
4. schemas/OpenAPI/TypeScript sem drift;
5. suite obrigatoria do `AGENTS.md` no commit final;
6. review read-only independente para P0/P1;
7. docs sem prometer capability ausente;
8. PR com escopo, limites e evidencia de verificacao.

## Backlog pos-MVP

Ficam fora do corte operacional inicial: runtime generico de tools e skills com approval gateway;
graph protocol e nested agents; restore, replay e fork por checkpoint; bundle portatil com blobs;
Canvas semantico; repeticoes e estatistica em escala; DuckDB/Parquet; packaging e notarizacao para
distribuicao publica; sync, cloud e multi-tenant.
