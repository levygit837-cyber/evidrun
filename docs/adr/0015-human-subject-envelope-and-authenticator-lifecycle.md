---
id: adr-0015
type: adr
title: HumanSubjectEnvelope, autenticador local e ciclo de vida de credencial
status: accepted
authority: normative
volatility: timeless
owner: governance
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: authority/human-actions@1
sources:
  - docs/adr/0010-verifiable-human-authority.md
  - docs/architecture/agents-and-authority.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/authority/subject.py
  - src/evidrun/authority/verifier.py
  - src/evidrun/authority/authenticator.py
  - src/evidrun/authority/challenge.py
  - src/evidrun/authority/repository.py
  - src/evidrun/authority/policy.py
  - src/evidrun/authority/service.py
  - src/evidrun/authority/router.py
  - alembic/versions/0003_human_authority.py
verification_refs:
  - tests/unit/test_authority_crypto.py
  - tests/unit/test_authority_policy.py
  - tests/unit/test_authority_subject.py
  - tests/integration/test_authority_flow.py
---

# Contexto

O ADR 0010 fixou o schema de `HumanAttestationRecord`, `VerifiedHumanDecisionAuthority` e o
protocolo `HumanAttestationVerifier`, mas deixou explicitamente em aberto o adapter/cerimônia
WebAuthn, enrollment, recovery, revogação e a proteção do artifact de assertion. Também não definia
qual documento exato o humano confirma quando aceita uma revision ou registra review/adjudicação.

Sem uma fonte de verdade para esse "subject" da attestation, cada entrypoint recomputava o digest
que o humano assina, arriscando divergência silenciosa da regra canônica do kernel
(`RevisionDecisionRecord.human_subject_digest()` e `EvaluationRecord.human_subject_digest()`).

# Decisão

## HumanSubjectEnvelope

O conteúdo assinado passa a ser um contract fechado e versionado na package `authority`,
discriminado por `kind`:

- `RevisionDecisionSubject` = `{revision_ref, decision, rationale}`;
- `EvaluationDecisionSubject` = `{source_type, run_id, plan_ref, stage_id, evaluator_ref, boundary,
  dimension_values, gate_status, relation}` com `status` sempre `final`.

O envelope é a única fonte de verdade sobre o que é assinado. Ele computa `subject_digest()`,
`target_digest` e `action`, e constrói o record canônico do kernel (`build_decision` /
`build_evaluation`) já ligado à attestation. O envelope não altera o kernel; seu `subject_digest()`
deve ser byte-a-byte igual ao `human_subject_digest()` do record correspondente, garantido por um
teste de anti-drift. Se a regra do kernel mudar, o teste falha e o envelope é atualizado no mesmo
commit.

O termo `SubjectEnvelope` (envelope do Subject Agent) permanece um conceito distinto e não é
sobrecarregado por este envelope de autoridade humana.

## Autenticador local (estado atual)

O adapter confiável desta iteração é um autenticador de software local (`KeyringAuthenticator`),
com par de chaves EC P-256 (ES256) guardado no keystore do SO. A assinatura cobre
`authenticatorData ‖ SHA-256(clientDataJSON)`, onde `clientDataJSON.challenge` carrega o digest do
intent. O `challenge_digest` liga action, target digest, subject digest, principal, credential,
relying party e origin, mais um nonce de uso único. O verifier `LocalWebAuthnVerifier` valida
rpIdHash, flags UP/UV, origin, challenge e a assinatura contra a chave pública enrolada, e é puro e
idempotente para poder rodar tanto na persistência quanto no replay do ledger. A garantia de
uso único do challenge e o estado da credencial (`active`/`revoked`) são impostos na camada de
serviço/repository, não no verifier.

O verifier default do processo permanece `UnavailableHumanAttestationVerifier` (fail-closed). A
feature é opt-in por `EVIDRUN_AUTHORITY=1`; sem ela, API e CLI continuam recusando decisions humanas
como no ADR 0010.

## Política de autonomia

Autenticação é opcional para criar, testar e executar em sandbox. É obrigatória apenas quando o
sistema faz uma afirmação de autoridade humana, libera risco maior ou promove evidência para o
estado verificado. `AuthorityPolicy` mapeia modo × risco de ação: ações críticas
(`revision.accepted/rejected/superseded`, `evaluation.adjudicated/reviewed`,
`external_effect.authorized`) sempre exigem humano verificado e rejeitam principal não humano,
independentemente do modo; ações rotineiras em sandbox/create/test/execute seguem sem autenticação.

# Consequências

- A camada authority é isolada (package, router, repository e migration próprios) para minimizar
  conflito com o Runtime Kernel; não executa Runs nem altera RunSpec/Admission.
- O envelope evita duplicação de regra de digest e torna auditável exatamente o que foi assinado.
- O autenticador de software é um adapter confiável desta fase; presença humana é imposta por
  cerimônia explícita e política, não por hardware.

# Questões críticas em aberto

- Canonicalização normativa de RP ID e origins entre desktop local, empacotamento e futuros
  autenticadores de plataforma/hardware.
- Recovery e rotação de credencial: hoje a revogação é terminal e não há fluxo de recuperação.
- Ciclo de vida completo da credencial (expiração, reenrollment, atestação de fabricante) e a
  substituição do autenticador de software por um autenticador de plataforma real.
- Autorização humana de efeito externo (`external_effect.authorized`) ainda não possui record nem
  runtime; a policy já a trata como crítica, mas o pipeline não existe.

# Alternativas rejeitadas

- Recomputar o digest do subject em cada entrypoint: dispersa a regra e diverge do kernel.
- Um novo `human_subject_digest` divergente do kernel: quebraria a validação do record ao persistir.
- Habilitar o verifier por padrão: violaria o fail-closed do ADR 0010.
