---
id: adr-0011
type: adr
title: Progress Artifacts, acesso a artifacts e fronteiras de bundles
status: accepted
authority: normative
owner: evidence
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: evidence/artifacts-bundles@1
sources:
  - docs/adr/0009-study-run-contract-composition.md
  - docs/contracts/evidence-bundle-v2.md
  - docs/product/semantic-execution-graph-concept.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/authoring.py
  - src/evidrun/contracts/runtime.py
  - src/evidrun/contracts/compiler.py
  - src/evidrun/evidence/bundle.py
  - scripts/generate_schemas.py
verification_refs:
  - tests/unit/test_contracts.py
  - tests/integration/test_contract_api.py
---

# Contexto

O core usa `ArtifactRef` para identificar conteúdo por ID, digest, media type e classification. Essa
identidade não prova que o blob existe, que está incluído em um bundle ou que determinado Subject,
evaluator ou humano pode lê-lo. Misturar identidade e acesso permitiria que uma simples ref virasse
grant implícito.

Runs longas também precisam de resumos auditáveis de progresso sem transformar o workspace ou uma
lista de arquivos em uma segunda fonte de verdade. Por fim, “bundle verificável”, “bundle portátil”
e “replay” são garantias diferentes e não podem ser prometidas pelo mesmo label.

# Decisão

## Identidade e acesso

`ArtifactRef` identifica conteúdo e classificação; não concede leitura, montagem, exportação ou
efeito externo. Acesso exige um grant separado e verificável, limitado por:

- principal ou consumer (`subject`, evaluator, humano ou serviço);
- Run, finalidade e operações permitidas;
- classification máxima, prazo e policy aplicável;
- artifact ID/digest exatos ou conjunto fechado de refs;
- autoridade que concedeu o acesso e seu evidence ref.

Materialização gera record próprio ligando grant, artifact ref, destino lógico e resultado. Locator
de storage, credencial e secret binding não são autoridade e não são entregues ao Subject.

## Progress Artifact

`ProgressArtifact` é um resumo derivado e imutável produzido em uma boundary verificável: checkpoint
validado, evento explícito ou intervalo de turnos declarado pela policy. Ele contém boundary,
digest, resumo permitido, source evidence refs, método/projector versionado, confidence e limitações.

Ele não é:

- inventário de arquivos do workspace;
- dump de memória privada ou chain-of-thought;
- substituto de RunEvents, artifacts, checkpoints ou evaluations;
- prova de conclusão, qualidade ou causalidade;
- contexto automático do Subject.

Correção cria novo Progress Artifact ou adjudicação append-only. Entregá-lo a um Subject ou evaluator
exige grant e envelope explícitos, além de evento de materialização.

## Bundles

Bundles declaram um perfil, sem sobreposição implícita:

- `audit`: carrega contratos, records, refs, digests e event chains suficientes para verificar o que
  foi declarado; artifacts podem permanecer externos;
- `portable`: inclui, com autorização, todos os payloads necessários ao uso offline declarado e um
  manifest que prova completude naquele escopo;
- `replay`: não é apenas bundle. Exige `ReplayPlan`, compatibilidade de runtime/provider/workspace,
  inputs materializáveis, seeds/policies e uma nova Run com lineage.

Um bundle auditável pode não ser portátil. Um bundle portátil pode não ser replayable. Checksum e
hash chain detectam alteração; não provam assinatura, acesso original, disponibilidade externa ou
reprodução do estado privado de um modelo.

# Compatibilidade e estado de implementação

Evidence Bundle v1 permanece compatível. O Evidence Bundle v2 atual declara `profile=audit`,
`artifact_content=references_only`, `portable=false` e `replayable=false`. Ele inclui contracts,
RunSpecs, admissions, RunRecords, events, evaluations, checkpoints e `artifact-manifest.json`, e
verifica estrutura, digests e event chains. O manifest enumera refs intencionalmente materializadas,
seu papel, inclusão/omissão de conteúdo e relevância para portabilidade; ele nunca é telemetria de
todo arquivo lido, editado ou observado no workspace. Os blobs referenciados e grants de acesso não
são incluídos automaticamente.

O schema atual implementa `ProgressArtifactPolicyRevision`, `ProgressArtifactContent` e
`ProgressArtifactRecord`, além dos eventos de observer iniciado, artifact criado e falha. A policy
aceita somente `checkpoint_reached` ou `subject_turn_interval`; neste último, um turno significa um
evento válido `subject.responded`, não toda mensagem, chamada interna ou tentativa. O compiler
materializa a policy no `RunSpec`, valida a referência de checkpoint e o record ancora o prefixo do
ledger e o artifact derivado. Observações e interpretações do resumo exigem evidence refs, e todo
conteúdo permanece `provisional`.

Esse é um subconjunto das boundaries aceitas acima: o schema v1 não oferece trigger genérico por tipo
de evento. O runtime não deve interpretar strings ou sintetizar um terceiro trigger fora da união
fechada.

Não existem observer/scheduler, persistência de `ProgressArtifactRecord` nem gerador em background.
Por isso qualquer RunSpec com essa policy é rejeitado na admissão como
`runtime:background_progress_observer`. Os payloads `progress.*` permanecem registrados para o
contrato futuro, mas o repository os rejeita como tipos reservados; nenhum evento ou record é criado
automaticamente. Também não existem `ArtifactAccessGrant`, materialization records, export
`portable`, restore ou replay executável.

## Questões críticas em aberto

- Qual serviço observará boundaries e garantirá idempotência, retry e persistência atômica entre o
  artifact, o `ProgressArtifactRecord` e os eventos de lifecycle?
- Qual contrato fechará grants e materialização antes de permitir que um consumer leia um artifact?
- Quais critérios objetivos de completude e autorização permitirão um futuro perfil `portable`?

# Alternativas rejeitadas

- Considerar posse de `ArtifactRef` como acesso: transforma metadado em autorização.
- Usar a lista atual de arquivos como Progress Artifact: é instável, incompleta e incentiva uma
  segunda fonte de verdade.
- Atualizar um resumo mutável ao longo da Run: apaga a interpretação disponível em boundaries
  anteriores.
- Chamar todo bundle de replayable: confunde integridade de evidência com reprodução de execução.

# Consequências

- APIs e bundles deverão resolver identity, grant, materialization e inclusion separadamente.
- Progress Artifacts sempre apontam para evidência anterior e permanecem projeções.
- Exportações futuras precisam declarar `audit` ou `portable`; replay terá contrato e ADR próprios.
- A ausência de blob ou grant deve aparecer como limitação verificável, não ser ocultada pelo digest.
