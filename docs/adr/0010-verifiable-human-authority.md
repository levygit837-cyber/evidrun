---
id: adr-0010
type: adr
title: Autoridade humana verificável e separação entre review e adjudicação
status: superseded
authority: normative
volatility: timeless
owner: governance
created_at: 2026-07-23
updated_at: 2026-07-28
applies_to: authority/human-actions@1
sources:
  - docs/adr/0009-study-run-contract-composition.md
  - docs/architecture/agents-and-authority.md
supersedes: []
superseded_by: docs/adr/0022-explicit-execution-trust-without-per-run-authentication.md
implementation_refs:
  - src/evidrun/contracts/base.py
  - src/evidrun/contracts/authority.py
  - src/evidrun/contracts/runtime
  - src/evidrun/infrastructure/database/repository.py
  - src/evidrun/entrypoints/api/app.py
  - src/evidrun/entrypoints/cli/app.py
verification_refs:
  - tests/unit/test_contract_revisions.py
  - tests/unit/test_contract_evaluation.py
  - tests/integration/test_contract_api.py
  - tests/integration/test_contract_cli.py
---

# Contexto

O ADR 0009 reserva aceitação de revisions, adjudicação e efeitos externos ao humano. Na origem
desta decisão, o contract v1 restringia `actor_type` ao literal `human`, mas isso só validava uma
alegação no payload. Um agente ou automação não pode ganhar autoridade humana por preencher esse
campo.

O modelo de evaluation também precisa separar duas ações que hoje podem parecer equivalentes:

- `human_review`: stage planejado que produz uma avaliação humana primária;
- adjudicação: decisão posterior que resolve, confirma ou substitui a precedência de records
  anteriores sem apagá-los.

# Decisão

Uma ação só pode ser apresentada como humana quando estiver ligada a um principal autenticado e a
evidência de uma confirmação explícita naquela boundary. O registro deve preservar, sem credenciais:

- `principal_id` estável e `principal_kind=human`;
- canal/autenticador e nível de assurance;
- ação, objeto e digest exatos aprovados;
- timestamp UTC e evidence ref do evento de autenticação/confirmação;
- rationale fornecida pelo humano.

`actor_type=human` sem essa ligação significa apenas `human_asserted`; nunca `verified_human`.
Agentes podem preparar drafts, recomendações e solicitações de aprovação, mas não podem emitir,
preencher em nome do usuário ou autoafirmar autoridade humana.

`human_review` e adjudicação permanecem semanticamente distintos:

- review é um stage previamente declarado pelo `EvaluationPlan`; seu record não precisa substituir
  outro record e conserva status próprio;
- adjudicação é append-only, referencia os records julgados, declara a decisão de precedência e
  exige principal humano verificável;
- adjudicação não reescreve judge, grader ou review anterior;
- `HumanAdjudicationPolicy.required` impede uma projeção final quando a adjudicação exigida ainda não
  existe, mas não impede preservar resultados provisórios;
- scorecard ou relatório deve mostrar qual record prevaleceu e por qual regra.

Aceitação, rejeição, supersession, adjudicação e autorização de efeito externo usam a mesma fronteira
de principal verificável, embora permaneçam tipos de record diferentes.

# Compatibilidade e estado de implementação

O schema atual implementa `HumanAttestationRecord`, `VerifiedHumanDecisionAuthority` e o protocolo
`HumanAttestationVerifier`. A attestation cobre principal, ação, target digest, subject digest,
challenge, assertion ref, relying party, origin, verifier e timestamp verificado. O repository valida
o conteúdo assinado antes de persistir uma decision ou evaluation humana. Sem adapter confiável, o
verifier default falha fechado; API e CLI recusam aceitação em vez de aceitar `actor_id` informado
pelo cliente.

`repository_fixture` é uma authority separada e explicitamente não humana. O método comum de
decision sempre a rejeita. O único caminho de escrita é
`Repository.import_legacy_contract_package`, que aceita exclusivamente o pacote canônico completo
do `CRL-CTX-002`, confere a lista fechada de revisions/refs e exige que todas as decisions cubram o
digest exato do pacote. Seu `repository-owner` não é prova criptográfica de ação humana.

`EvaluationRecord.source_type` distingue `human_reviewer` de `human_adjudicator`. Review usa relação
`independent_review`; adjudicação usa `adjudicates` com targets explícitos. Ambos exigem attestation,
status final e verificação no repository. A adjudicação também precisa estar autorizada pelo
`HumanAdjudicationPolicy` e apontar para records da mesma Run, plan e stage.

Ainda não existe adapter WebAuthn/passkey real, cerimônia de UI/CLI, enrollment, recovery ou lifecycle
de credential. Por isso o runtime não oferece decision ou evaluation humana verificável: a ausência
do adapter é rejeição, não uma authority degradada. Uma Run cujo plano exige adjudicação humana é
rejeitada na admissão como `runtime:verified_human_adjudication`; não existe pipeline executável que
espere essa adjudicação e publique uma projeção final.

O enum de attestation atual cobre decisions de revision, review e adjudicação. Autorização humana
de efeito externo, embora governada pela mesma decisão deste ADR, ainda não possui record ou runtime.

## Questões críticas em aberto

- Qual adapter e cerimônia WebAuthn serão confiáveis no desktop local, incluindo RP ID, origins,
  enrollment, recovery, revogação e proteção do assertion artifact?
- Qual projeção operacional representará uma adjudicação obrigatória pendente quando o pipeline
  humano existir, sem confundir Run terminal com evaluation final?

# Alternativas rejeitadas

- Confiar somente em `actor_id` fornecido pelo cliente: não prova identidade nem intenção.
- Permitir que o Lab Agent assine como humano após receber uma instrução genérica: mistura proposta
  e autoridade.
- Sobrescrever o record julgado durante adjudicação: destrói auditabilidade e divergência histórica.
- Tratar todo `human_review` como adjudicação: impede review humano primário e torna precedência
  implícita.

# Consequências

- Principal e authority evidence possuem schema fechado; o adapter futuro deve produzi-los sem
  armazenar segredo ou material autenticador no contrato.
- CLI/UI precisarão de uma ação humana explícita e não delegável para decisões privilegiadas.
- Projeções distinguem asserted, verified, provisional e final.
- Ausência de autoridade verificável é estado auditável, não motivo para inventar um humano.
