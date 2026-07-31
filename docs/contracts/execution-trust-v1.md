---
id: contract-execution-trust-v1
type: contract
title: Execution Trust v1
status: accepted
authority: normative
volatility: timeless
owner: governance
created_at: 2026-07-28
updated_at: 2026-07-31
applies_to: execution-trust@1
sources:
  - docs/adr/0022-explicit-execution-trust-without-per-run-authentication.md
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/contracts/study-run-v1.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/execution_trust.py
  - src/evidrun/contracts/review_package.py
  - src/evidrun/infrastructure/database/trust.py
  - src/evidrun/runs/preparation.py
  - src/evidrun/contracts/admission/checks/execution_trust.py
  - src/evidrun/infrastructure/database/catalog.py
  - src/evidrun/infrastructure/database/queue/enqueue.py
  - src/evidrun/runs/review.py
  - src/evidrun/entrypoints/review_html.py
  - src/evidrun/entrypoints/api/routers/reviews.py
  - apps/web/src/features/observability/executionTrust.ts
verification_refs:
  - tests/unit/test_execution_trust.py
  - tests/integration/test_execution_trust_migration.py
  - tests/unit/test_unverified_admission.py
  - tests/acceptance/test_unverified_execution.py
  - tests/integration/test_execution_preparation_surfaces.py
  - tests/acceptance/test_verified_execution_review.py
---

# Execution Trust v1

Este contrato define como uma Run declara se o conjunto de revisions usado na compilação foi ou não
confirmado por autoridade humana. Os dois kinds estão implementados. O corredor não verificado sela
a closure exata de uma Study draft e compila sem Decision humana. Quando a closure inteira já possui
decisions `accepted` de autoridade humana revalidada, a mesma preparação deriva o kind verificado.
Ambos persistem trust antes da admissão e propagam a mesma ref para AdmissionRecord, fila, RunRecord,
read models e Bundle v4. O ReviewPackage é projetado por API, CLI e HTML a partir de ReviewTargets
persistidos; nenhum caller escolhe kind ou fornece refs futuras para o diff.

Trust não é admission, lifecycle, avaliação nem isolamento. `unverified_revision_set` significa
“sem confirmação humana”; não significa documento mutável, digest opcional ou execução sem
validação técnica.

## Execution Revision Set

O documento selado usa o seguinte shape semântico:

| Campo | Tipo | Regra |
| --- | --- | --- |
| `schema_version` | literal `1` | versão deste algoritmo de closure e digest |
| `project_id` | id | hard boundary; todas as revisions pertencem a este Project |
| `study_ref` | `ContractRef` | Study raiz exata e também presente em `revision_refs` |
| `revision_refs` | lista não vazia de `ContractRef` | closure completa, sem duplicatas, em ordem canônica |

O `revision_set_digest` não é um campo autoritativo inserido dentro do próprio documento. Ele é
calculado externamente como:

```text
SHA-256(UTF-8(canonical_json(execution_revision_set)))
```

`canonical_json` ordena chaves, preserva Unicode, usa separadores compactos e não depende da
formatação do arquivo original. `revision_refs` é ordenada por
`contract_type → logical_id → revision → digest` antes da serialização.

O `project_id` faz parte do selo porque o digest semântico atual de uma revision não inclui seu
Project. Assim, o mesmo conteúdo pode ser reutilizado conscientemente em outro Project sem permitir
que um trust record atravesse a fronteira por coincidência de payload.

### Closure v1

O coletor parte da `StudyRevision` exata e inclui a união das refs necessárias para compilar toda a
matriz da Study:

- a própria Study;
- Goal e todos os Scenarios;
- Agent Inventory, Run Environment Template, Interaction Protocol e EvaluationPlan do blueprint;
- todas as refs substituídas por qualquer Variant;
- CheckpointPolicy e ProgressArtifactPolicy quando presentes;
- qualquer nova ref transitiva somente depois de ela entrar na allowlist de uma versão sucessora do
  coletor.

ArtifactRefs, capability refs, hidden inputs e extensions permanecem dentro dos payloads canônicos
das revisions que os declaram e, por isso, já alteram seus digests. O `ReviewPackage` os expande para
leitura humana e diff; ele não muda a identidade do conjunto.

O selo falha fechado quando:

- uma ref não resolve;
- o documento resolvido não reproduz o digest alegado;
- uma revision pertence a outro Project;
- a Study raiz não aparece na closure;
- a mesma identidade aparece com digest incompatível;
- um ciclo ou tipo de ref não suportado impede provar a closure completa.

Depois do selo, compilação não consulta “latest”, não troca revision por uma accepted mais recente e
não resolve documento fora de `revision_refs`.

## ExecutionTrustRecord

O record v1 possui:

| Campo | Tipo | Regra |
| --- | --- | --- |
| `schema_version` | literal `1` | versão do record |
| `trust_id` | id | identidade estável gerada pelo sistema |
| `kind` | enum | `unverified_revision_set` ou `verified_revision_set` |
| `project_id` | id | igual ao Project do conjunto selado |
| `study_ref` | `ContractRef` | igual à raiz do conjunto |
| `revision_refs` | lista de `ContractRef` | closure canônica preservada no record |
| `revision_set_digest` | SHA-256 | recomputável do Execution Revision Set |
| `run_spec_digest` | SHA-256 | exatamente um RunSpec compilado do conjunto |
| `verified_decisions` | lista de bindings | vazia no kind não verificado; cobertura total no verificado |
| `created_at_utc` | timestamp UTC | atribuído pelo sistema |

Cada binding de `verified_decisions` contém a `revision_ref` e o digest do
`RevisionDecisionRecord` `accepted` correspondente. No kind `verified_revision_set`, a lista cobre
exatamente `revision_refs`, sem faltas ou entradas extras, e cada decision possui autoridade humana
verificada. `repository_fixture` não satisfaz esse kind.

O digest do record usa o JSON canônico de todos os campos sem um campo autorreferente de digest.
Criação é idempotente para o mesmo conteúdo semântico; uma colisão de identidade com conteúdo
divergente falha fechado.

### Quem pode criar

- Serviço determinístico pode criar `unverified_revision_set`. Isso declara ausência de confirmação,
  não autoridade.
- `verified_revision_set` exige validação de cada decision humana antes da persistência.
- Lab Agent pode propor drafts e solicitar revisão, mas não cria decision humana nem escolhe o kind
  verificado.
- API e CLI não aceitam `actor`, `verified=true` ou `kind` como prova de autoridade.

## Ligação com admissão, Run e bundle

O record é persistido antes da admissão. O corredor implementado acrescenta uma ref tipada e o digest
exato do `ExecutionTrustRecord` ao `AdmissionRecord` e ao `RunRecord`. A persistência rejeita:

- trust ausente;
- kind desconhecido;
- Project, Study, revision set ou RunSpec divergente;
- decision incompleta no kind verificado;
- policy incompatível com o kind.

A fila usa somente uma admissão que já passou por essa validação. O Evidence Bundle exporta o
documento completo e o verificador recalcula `revision_set_digest`, digest do trust record e todas
as ligações com RunSpec, AdmissionRecord e RunRecord. Uma string solta em metadata não satisfaz este
contrato.

## Policy do kind não verificado

`unverified_revision_set` não altera a capability matrix do runtime. No v1:

| Eixo | Permitido | Rejeitado |
| --- | --- | --- |
| classificação | `public`, `internal` | `sensitive`, `restricted` |
| network | `denied`, `provider_only` quando admitido | acesso amplo não declarado |
| efeitos externos | nenhum | qualquer efeito autorizado |
| avaliação humana | nenhuma | human review e adjudicação |
| capabilities | catálogo seguro realmente resolvido | ausente, incompatível ou apenas representável |

`provider_only` permite somente comunicação necessária com o provider configurado e admitido. Não
concede navegação geral, mounts, secrets ou efeitos externos. Se o adapter não consegue aplicar e
provar o modo, a admissão rejeita.

## Promoção

Não existe alteração in-place:

```text
Run A + unverified_revision_set
  → decisions humanas append-only sobre as revisions
  → novo ExecutionTrustRecord verified_revision_set
  → nova AdmissionRecord
  → Run B
```

Run A, seus eventos, evaluations e bundle permanecem não verificados. Run B pode usar o mesmo
RunSpec digest quando nada semântico mudou, mas possui trust record, admissão e identidade de Run
novos. UI e Comparison podem relacionar as duas sem apresentá-las como a mesma execução.

## ReviewPackage

`ReviewPackage` é uma projeção determinística, não um record de autoridade. Sua identidade semântica
é um documento mínimo separado, o `ReviewTarget` v1:

| Campo | Tipo | Regra |
| --- | --- | --- |
| `schema_version` | literal `1` | versão do target |
| `project_id` | id | mesmo hard boundary do Execution Revision Set |
| `revision_set_digest` | SHA-256 | digest do conjunto fechado de revisions |
| `run_spec_digests` | lista não vazia de SHA-256 | todos os RunSpecs produzidos, sem duplicatas e em ordem lexicográfica |

O digest semântico é:

```text
review_target_digest = SHA-256(UTF-8(canonical_json(review_target)))
```

Uma Study que produz somente um RunSpec usa uma lista de um item. O target falha fechado se qualquer
RunSpec não puder ser reproduzido do Execution Revision Set, pertencer a outro Project ou aparecer
fora da matriz compilada. Mudar revision, variant, repetition, override, disclosure, capability,
classification, input, protocol ou EvaluationPlan muda `revision_set_digest`, algum
`run_spec_digest` ou ambos.

O `ReviewPackage` apresenta o `ReviewTarget`, `review_target_digest` e:

- Project, Study e closure exata com digests;
- diff para um pacote anterior selecionado;
- RunSpecs que o conjunto produz;
- disclosure do Subject;
- capabilities, classificações, network e efeitos externos;
- EvaluationPlan e refs de hidden inputs sem entregar conteúdo oculto ao Subject;
- limitações, recusas de admissão conhecidas e tipo de Run Environment.

Não existe `review_package_digest`: bytes de HTML/PDF, texto explicativo, localização e layout não
são autoridade. Uma futura confirmação em lote poderá cobrir o `review_target_digest` e materializar
decisions para a closure listada. Essa cerimônia não pertence ao WS-40. Alterar qualquer entrada
semântica produz outro target; não existe aprovação aberta para refs futuras.

## Projeção humana e machine-readable

API, bundle e DTOs usam sempre `execution_trust.kind`. A UI não infere trust por cor ou por ausência
de decision.

Texto canônico:

| Kind | Rótulo curto | Explicação |
| --- | --- | --- |
| `unverified_revision_set` | `Não verificada` | `Sem confirmação humana das revisions` |
| `verified_revision_set` | `Verificada` | `Revisions confirmadas por autoridade humana` |

O rótulo aparece na lista de Runs, cabeçalho do detalhe, resumo do bundle e em cada página de uma
projeção impressa. Cor e ícone podem reforçar, mas nunca substituir o texto. O JSON exportado carrega
o kind e o digest; relatórios HTML/PDF repetem pelo menos o rótulo curto e o `trust_id` no
cabeçalho/rodapé. Assim, uma captura de tela ou página isolada não perde o contexto.

Isolamento usa outro campo e outra linha, por exemplo:

```text
Trust: Não verificada — sem confirmação humana
Isolamento: in_process
```

Não existe kind `sandbox`, e `in_process` nunca recebe selo de sandbox seguro.

## Estado de implementação e compatibilidade

- `ExecutionPreparationService` resolve revisions registradas por refs exatas, sem consultar
  `latest`, sela a closure, compila a matriz inteira e deriva um trust não verificado ou verificado
  por RunSpec conforme a cobertura humana preexistente;
- API e CLI recebem somente `execution_trust_id`; `kind`, ator ou claim humano enviado pelo caller
  não escolhe o trust;
- persistência, enqueue e worker exigem e revalidam a mesma ref de trust;
- `EVIDRUN_AUTHORITY` e o autenticador local continuam opt-in e não são usados pelo corredor não
  verificado;
- Runs legadas não ganham trust retroativo: ausência permanece `not_recorded`;
- o store cria `verified_revision_set` somente depois de revalidar cada decision humana persistida;
  restart posterior revalida documentos, digests e bindings sem exigir nova cerimônia por Run;
- ReviewPackage JSON não possui `review_package_digest`; diff aceita somente outro ReviewTarget
  persistido do mesmo Project, e a projeção HTML identifica o target sem se declarar autoridade;
- recusas conhecidas no package são derivadas somente do RunSpec imutável; incompatibilidades
  dependentes de trust ou do catálogo ativo pertencem ao AdmissionRecord criado separadamente;
- lista e detalhe de Runs mostram trust e isolamento em campos textuais separados;
- `repository_fixture` continua pelo import dedicado e explicitamente não humano.
