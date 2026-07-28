---
id: adr-0022
type: adr
title: Trust explícito de execução sem autenticação por Run
status: accepted
authority: normative
volatility: timeless
owner: governance
created_at: 2026-07-28
updated_at: 2026-07-28
applies_to: execution-trust@1
sources:
  - docs/adr/0010-verifiable-human-authority.md
  - docs/adr/0015-human-subject-envelope-and-authenticator-lifecycle.md
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/contracts/study-run-v1.md
supersedes:
  - docs/adr/0010-verifiable-human-authority.md
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Contexto

O contrato original só permite que o compiler resolva revisions aceitas. O caminho de aceitação
humana verificável existe de forma opt-in, mas exigir uma cerimônia de autenticação para cada Study,
repetição ou Run tornaria o uso cotidiano repetitivo e faria a instalação depender do lifecycle de
WebAuthn antes de permitir experimentação local. Manter o default atual também ficou incoerente
depois da superfície pública de Workspace/Project: o usuário consegue criar o laboratório e drafts,
mas não consegue executar o próprio Study sem ligar authority ou importar a fixture canônica.

Ao mesmo tempo, remover a confirmação não pode transformar automação em humano, chamar um draft de
aceito ou esconder do bundle que a Run usou revisions sem decisão humana. Trust, admissão técnica e
isolamento são três eixos diferentes.

# Decisão

## A execução comum usa trust explícito, não autenticação humana por Run

O caminho default futuro será executar um conjunto exato de revisions como
`unverified_revision_set`. “Não verificada” significa somente **sem confirmação humana das
revisions**. O sistema ainda valida digests, schema, pertencimento ao Project, compilação, RunSpec,
capabilities, classifications e compatibilidade do runtime antes da admissão.

Uma Run não verificada não cria `RevisionDecisionRecord`, não muda revision para `accepted`, não
produz `HumanAttestationRecord` e não pode ser apresentada como evidência confirmada por humano.
Agente, serviço e automação continuam proibidos de afirmar autoridade humana.

`verified_revision_set` fica reservado para um conjunto cujas revisions exatas possuem decisões
humanas verificadas. A autenticação local é uma evolução futura e não é exigida pelo caminho comum do
MVP. O adapter WebAuthn existente permanece compatível para records já produzidos e para o fluxo
opt-in, mas deixa de ser dependência do default e não recebe expansão dentro do WS-40. Remoção do
adapter ou substituição da cerimônia exige decisão sucessora e migração que preserve a verificação
dos records históricos.

## O Execution Revision Set é selado por conteúdo

Antes da compilação sem aceitação, um serviço determinístico coleta a Study raiz e a união de todas
as revisions alcançáveis pelos campos `ContractRef` permitidos pelo schema vigente. O coletor é uma
allowlist versionada; campo futuro não entra silenciosamente no conjunto.

O selo contém:

- `schema_version` do formato do conjunto;
- `project_id` obrigatório;
- `study_ref` exata;
- todas as `revision_refs` exatas, inclusive a própria Study, ordenadas por
  `contract_type`, `logical_id`, `revision` e `digest`.

Cada ref precisa resolver uma revision imutável do mesmo Project com o digest alegado. Ref ausente,
digest divergente, dependência fora do Project, ciclo não suportado ou duas identidades incompatíveis
rejeitam o selo. Não existe resolução de “latest” depois do selo.

O `revision_set_digest` é SHA-256 do JSON canônico desse documento, com chaves ordenadas, UTF-8 e sem
whitespace variável, reutilizando a convenção `canonical_json`/`sha256_json` já aplicada aos
contracts. Os payloads completos não são duplicados no manifesto: o digest de cada `ContractRef`
já identifica o documento semântico. O `ReviewPackage` expande os documentos para leitura e diff,
mas não cria uma segunda identidade.

O compiler resolve exclusivamente o conjunto selado e produz RunSpecs imutáveis. Cada
`ExecutionTrustRecord` liga um `revision_set_digest` a um único `run_spec_digest`; essa segunda
ligação detecta mudança de compilação ou de override mesmo que a raiz continue igual.

Para revisão legível de uma Study inteira, um `ReviewTarget` canônico liga o
`revision_set_digest` à lista não vazia e ordenada de todos os `run_spec_digests` produzidos. Seu
`review_target_digest` usa a mesma função SHA-256 sobre JSON canônico. O `ReviewPackage` é somente a
projeção humana desse target: HTML, PDF, texto explicativo e ordem visual podem evoluir sem criar uma
identidade semântica concorrente. Mudar qualquer revision ou RunSpec muda o target.

## ExecutionTrustRecord é a fonte canônica de trust da Run

O contrato v1 possui os kinds:

```text
unverified_revision_set
verified_revision_set
```

O record existe antes da admissão. AdmissionRecord e RunRecord precisam apontar para sua identidade
e digest; fila, read model e bundle revalidam a ligação com o RunSpec exato. Campo ausente, kind
desconhecido ou digest divergente falha fechado. Trust não é inferido da ausência de decision, de um
ator, de configuração da UI ou de um nome de Run Environment.

O serviço pode criar deterministicamente um record `unverified_revision_set`, porque isso não é
ação humana. Um record `verified_revision_set` só pode existir quando cada revision do conjunto está
coberta por uma decisão `accepted` com autoridade humana verificável. A
`Repository Fixture Authority` permanece não humana e não é promovida a esse kind.

## Promoção cria uma nova Run

Confirmar depois um conjunto não reescreve o record, a admissão, a Run ou o bundle anteriores. A
promoção cria decisions append-only para as revisions exatas, outro `ExecutionTrustRecord` com kind
`verified_revision_set`, nova admissão e nova Run. A Run anterior permanece para sempre rotulada
`unverified_revision_set`, mesmo quando os documentos não mudaram.

Uma futura cerimônia pode confirmar atomicamente um `ReviewPackage`, mas precisa materializar as
decisions exatas cobertas. Ela não concede aceitação aberta a refs futuras e não autoriza um agente a
confirmar em nome do usuário.

O WS-40 somente materializa e verifica o `ReviewTarget` e consome decisions humanas que já sejam
válidas. Assinar o `review_target_digest`, enrollment, recovery, rotação e revogação pertencem à
evolução futura do autenticador local; não fazem parte do caminho B.

## Não verificado não ignora segurança ou admissão

O trust record não amplia capabilities. No primeiro marco do WS-40:

- `public` e `internal` podem prosseguir;
- `sensitive` e `restricted` continuam rejeitados pelo runtime ativo;
- efeitos externos permanecem `denied`;
- network pode ser `denied` ou `provider_only` quando o adapter e a admissão comprovarem suporte;
- human review e adjudicação continuam indisponíveis sem autoridade humana verificável;
- somente capabilities reais do catálogo seguro e admitido chegam ao SubjectEnvelope.

Assim, o usuário pode optar por uma Run sem confirmação humana, mas não pode usar o rótulo para
contornar capability ausente, classificação, admission ou policy.

## Trust e isolamento aparecem separados

`AuthorityMode.SANDBOX` fica confinado como identificador legado da policy de authority e não será
usado em `ExecutionTrustRecord`, bundle ou rótulo da Run. Uma versão futura deve renomeá-lo ou
removê-lo quando o contrato de policy for revisado.

A interface e os relatórios sempre mostram dois campos independentes:

```text
Trust: Não verificada — sem confirmação humana
Isolamento: in_process
```

ou, quando existir adapter que prove isolamento:

```text
Trust: Não verificada — sem confirmação humana
Isolamento: sandboxed — adapter e capabilities identificados
```

Sandbox forte é opcional e recomendado quando disponível, mas nunca presumido. O runtime atual
continua sendo descrito como `in_process`.

O kind machine-readable é obrigatório na API e no bundle. A forma humana usa texto, não somente cor,
ícone ou tooltip: aparece na linha da Run, no cabeçalho do detalhe, no resumo do bundle e em
cabeçalho/rodapé de cada página impressa. Dessa forma o significado permanece presente em export,
impressão e captura de tela sem depender do restante da aplicação.

# Escopo da supersession

Este ADR substitui somente a premissa do ADR 0010 de que toda compilação precisa resolver revisions
aceitas e, portanto, não pode existir Run sem adapter humano confiável. Continuam vigentes a
exigência de `HumanAttestationRecord` para claims humanos, a distinção entre review e adjudicação, a
natureza não humana de `repository_fixture` e todas as regras append-only. O caminho não verificado
não é uma exceção a essas regras porque não cria decision nem claim humano.

# Alternativas consideradas

## Autenticador local por default

Adiado. Preserva um único caminho verificado, mas torna enrollment, recovery, rotação e repetição da
cerimônia bloqueios cotidianos. Uma evolução futura pode oferecer confirmação local de um
ReviewPackage inteiro sem exigir autenticação por Run e sem alegar garantia de plataforma.

## Manter authority opt-in como único caminho

Rejeitado como default. É fail-closed, mas deixa o produto criar Workspace, Project e drafts que não
consegue executar normalmente.

## Chamar a execução não verificada de sandbox

Rejeitado. Trust descreve confirmação humana; sandbox descreve isolamento técnico. O mesmo Run pode
ser não verificado e isolado, não verificado e `in_process`, ou futuramente verificado e isolado.

## Autenticar cada Run

Rejeitado. Repetições e retries tornariam a cerimônia ruidosa sem adicionar decisão semântica. A
unidade futura de revisão humana é o conjunto fechado de revisions, não cada processo iniciado.

# Consequências

WS-40 precisa implementar o contrato de trust, o coletor fechado de dependências, a resolução contra
o conjunto selado, a ligação em admissão/Run/bundle e os rótulos honestos. Até isso aterrissar, o
compiler continua aceitando somente revisions aceitas e não existe execução não verificada.

O caminho default ficará simples sem degradar claims humanos. O custo é tornar trust um estado
explícito em todos os consumidores e manter duas Runs quando o usuário quiser repetir como evidência
verificada. Essa duplicidade é deliberada: preserva a imutabilidade e deixa claro o que foi executado
antes e depois da confirmação.
