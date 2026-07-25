---
id: planning-task-default-authoring-authority
type: implementation-task
title: WS-03 Decisao de autoria default no produto instalado
status: proposed
authority: planning
owner: governance
created_at: 2026-07-23
updated_at: 2026-07-24
observed_at: 2026-07-24
review_due: 2026-08-07
applies_to: control-plane-trust
sources:
  - docs/adr/0010-verifiable-human-authority.md
  - docs/adr/0015-human-subject-envelope-and-authenticator-lifecycle.md
  - docs/architecture/agents-and-authority.md
  - docs/contracts/experiment-manifest.md
  - docs/planning/mvp-implementation-roadmap.md
  - docs/planning/tasks/40-trust-sandbox-review-package.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-03 — Decisao de autoria default

`workstream_state: queued`

## Resultado pratico

A entrega desta task **nao e codigo de sandbox**. E um par indissociavel:

1. um **ADR sucessor** aceito que decide como um usuario do produto instalado aceita uma revision de
   contract, ou executa sem aceitar, sem que o sistema afirme autoridade humana que nao possui;
2. o **contrato de trust** derivado dessa decisao — nomes, estados, records e regras de exibicao —
   consumido pela WS-40 (implementacao) e pela UI (WS-51), fixado em texto normativo antes de
   qualquer branch de implementacao existir.

A decisao final e humana. O agente desta task **modela, mede o trade-off e escreve as opcoes**; ele
nao escolhe qual opcao vira default nem marca o ADR como `accepted` sozinho. O ponto de parada normal
desta task e um ADR em `status: proposed` com as opcoes instrumentadas e a recomendacao explicitamente
separada da decisao.

Criterio de sucesso observavel: ao final, WS-40 consegue comecar sem precisar responder nenhuma
pergunta normativa sobre trust, e a UI sabe exatamente quais estados precisa distinguir e com que
vocabulario.

## Snapshot inicial (verificado em 2026-07-24)

Estes fatos foram lidos no codigo, nao inferidos. Reconfirme cada um antes de escrever o ADR, porque
a Onda 0 corre em paralelo e `main` se move.

- `src/evidrun/shared/settings.py`: `Settings.authority_enabled: bool = False`; `Settings.load` liga o
  campo apenas quando `EVIDRUN_AUTHORITY` esta em `{"1", "true"}`. Este e o bloqueio B3.
- `src/evidrun/contracts/compiler.py`, `InMemoryContractRegistry.__init__`: aceita
  `human_attestation_verifier` opcional e `allow_repository_fixture: bool = False`; sem verifier
  injetado, cai em `UnavailableHumanAttestationVerifier()`.
- `InMemoryContractRegistry.decide`: se `decision.authority.kind == "verified_human"`, delega a
  `verify` do verifier; qualquer outro `kind` exige `allow_repository_fixture`, senao levanta
  `PermissionError("repository fixture acceptance is restricted to the legacy import path")`.
- `InMemoryContractRegistry.resolve`: exige revision presente, digest igual ao do `ContractRef`, e
  `decision.decision == "accepted"`; senao `ValueError("only accepted contract revisions can be
  resolved")`. Consequencia direta: sem aceitacao, nao existe compile — logo nao existe Run.
- `src/evidrun/contracts/authority.py`: `UnavailableHumanAttestationVerifier.verify` sempre levanta
  `HumanAttestationUnavailable`. E o default fail-closed do processo.
- `src/evidrun/contracts/base.py`: `VerifiedHumanDecisionAuthority.kind == "verified_human"` (exige
  `principal_id` + `HumanAttestationRecord`); `RepositoryFixtureDecisionAuthority.kind ==
  "repository_fixture"` com `fixture_id` fixado no literal `experiment-manifest-v1:crl-ctx-002`, e
  `validate_authority` so permite `decision == "accepted"` para esse kind.
- `src/evidrun/infrastructure/database/repository.py`: `decide_contract_revision` recusa
  `repository_fixture` com `PermissionError("repository fixture acceptance requires
  import_legacy_contract_package")`; `import_legacy_contract_package` confere um conjunto fechado de
  sete identidades (`goal`, `scenario`, `agent_inventory`, `workspace_template`,
  `interaction_protocol`, `evaluation_plan`, `study` do `crl-ctx-002-context-policy`), exige que as
  decisions cubram exatamente os refs do pacote, e so ali monta o registry com
  `allow_repository_fixture=True`.
- `src/evidrun/authority/policy.py`: `AuthorityMode` = `SANDBOX | CREATE | TEST | EXECUTE |
  PRIVILEGED`; `CRITICAL_ACTIONS` inclui `revision.accepted/rejected/superseded`,
  `evaluation.adjudicated/reviewed` e `external_effect.authorized`;
  `AuthorityPolicy.requires_verified_human` retorna `True` para acao critica em qualquer modo, e para
  qualquer acao em `PRIVILEGED`. **O membro `SANDBOX` existe hoje apenas como modo de policy: nada em
  `RunSpec`, `Run`, admissao, ledger ou bundle referencia esse modo.** O nome existe; a semantica de
  execucao nao.
- `src/evidrun/authority/verifier.py`: `LocalWebAuthnVerifier` valida `subject_digest`, posse da
  credencial pelo principal, `relying_party_id`, `origin` e a assinatura do assertion artifact; e
  puro e idempotente, para rodar tanto na persistencia quanto no replay.
- `src/evidrun/authority/authenticator.py`: `KeyringAuthenticator` guarda chave EC privada no keystore
  do SO sob o service `evidrun-human-authenticator`; assinar exige `credential_id` e a cerimonia
  explicita — nao existe caminho implicito de automacao.
- Composicao atual: `entrypoints/api/app.py` e `entrypoints/cli/app.py` so instanciam
  `LocalWebAuthnVerifier` quando `settings.authority_enabled`; caso contrario o `Repository` nasce com
  o verifier indisponivel.

### Corrigido neste ciclo — contexto, nao trabalho pendente

A investigacao que produziu B3 tambem corrigiu tres defeitos que **ja estao em `main`**. Nao os
replaneje:

- a CLI reconstruia `Repository` sem verifier, gravando uma aceitacao verificada que ela propria nao
  conseguia reler depois;
- `authority accept` sobrescrevia o verifier e assim ignorava o gate do ADR 0015;
- `contract accept` era um stub morto que duplicava `authority accept`.

Hoje `_components` e `_authority_service` honram `EVIDRUN_AUTHORITY` nos dois caminhos, e
`authority accept` passa por `AuthorityMode.PRIVILEGED` + `confirm_with_local_authenticator` antes de
chamar `decide_contract_revision`. O problema restante e de **default e de vocabulario**, nao de
wiring.

### Fatos a redescobrir antes de escrever

- Onde exatamente a UI hoje deriva estado de contract/Run, e qual vocabulario ela ja mostra ao
  usuario (nao invente estados novos sem saber os que existem).
- Se a API expoe algum campo que ja poderia ser lido como "verificado" sem attestation.
- O que o bundle v3 afirma hoje sobre autoridade nos grupos de records, e onde caberia um marcador de
  trust sem quebrar verificacao existente.
- Se WS-01 introduziu superficie de criacao que muda a premissa da Opcao C (produto instalado que nao
  cria Studies novos).

## Dependencias e ownership de paths

Sem dependencia de codigo. Corre em paralelo com WS-01 e WS-02; **precede WS-40**, que implementa a
decisao.

Pode editar:

- `docs/adr/00NN-<slug>.md` — o ADR sucessor novo, numerado com o proximo numero livre em
  `docs/adr/`;
- `docs/index.md` — apenas a entrada do ADR novo, se o indice exigir registro;
- `docs/planning/tasks/40-trust-sandbox-review-package.md` — apenas para apontar o ADR resultante como
  pre-condicao normativa resolvida, se e quando o ADR for aceito.

Nao pode editar:

- qualquer arquivo sob `src/` — esta task nao muda comportamento;
- `docs/adr/0010-verifiable-human-authority.md` e
  `docs/adr/0015-human-subject-envelope-and-authenticator-lifecycle.md` — ADR aceito nao e reescrito
  (`AGENTS.md`, "Fonte de verdade"); a mudanca entra como sucessor com `supersedes` apontando para o
  antecessor e o antecessor recebendo `superseded_by` somente no momento da aceitacao humana;
- `apps/` — vocabulario de UI e proposto aqui, consumido em WS-51;
- `docs/planning/mvp-implementation-roadmap.md` e `docs/planning/tasks/README.md` — pertencem ao
  integrador.

Se a analise concluir que o ADR precisa mudar um invariante de `AGENTS.md`, pare e escale. Um brief
nao autoriza relaxar invariante.

## As tres opcoes a instrumentar

Cada opcao deve responder, em texto normativo, exatamente tres perguntas: **o que passa a ser
afirmavel**, **o que continua proibido**, e **como bundle e UI distinguem o modo**. Uma opcao sem as
tres respostas nao esta modelada.

### Opcao A — ligar o autenticador local por padrao

`authority_enabled` passa a `True` por default, e o produto instalado enrola uma credencial local no
primeiro uso.

- O que isso significa: `LocalWebAuthnVerifier` + `KeyringAuthenticator` viram o adapter confiavel do
  caminho normal; a aceitacao de revision passa por cerimonia explicita com `credential_id`, e o
  `HumanAttestationRecord` resultante e verificavel no replay do ledger.
- O que isso **nao** significa: nao e passkey de plataforma, nao e autenticador de hardware, nao e
  atestacao de fabricante, e nao prova presenca fisica alem do que a cerimonia local impoe. A chave
  privada vive no keystore do SO; quem controla a maquina controla a credencial. O ADR deve dizer isso
  em voz alta, porque a diferenca entre "humano verificado por autenticador local" e "humano
  verificado por plataforma" e exatamente o que o bundle vai afirmar.
- Afirmavel: autoria humana verificada no escopo do dispositivo, ligada a principal e credencial.
- Proibido: qualquer promocao a claim de plataforma; enrollment silencioso sem interacao; qualquer
  caminho onde a automacao dispare `sign` sem cerimonia.
- Bundle/UI: o claim precisa carregar a classe do adapter (software local vs plataforma), nao apenas
  "verified". A UI nao pode exibir um selo que sugira garantia mais forte que a real.
- Custo honesto a registrar: recovery e rotacao continuam abertos no ADR 0015 (revogacao e terminal).
  Ligar por default transforma essa lacuna em problema de usuario real, nao mais hipotetico.

### Opcao B — Run explicitamente `unverified_sandbox`

Introduz um caminho de execucao que compila sem aceitacao humana e se declara nao verificado.

- Afirmavel: "esta Run executou estes documentos, nestes digests exatos, sem autoridade humana".
  Nada mais.
- Proibido: alterar o status das revisions para `accepted`; reusar `RevisionDecisionRecord` para
  declarar trust; efeitos externos (`denied`); dados `sensitive`/`restricted`; human review ou
  adjudicacao; qualquer promocao automatica de sandbox para evidencia verificada; qualquer reescrita
  da Run original quando uma aceitacao humana surgir depois.
- Bundle/UI: trust e campo de primeira classe, nao ausencia de campo. O bundle marca a Run como
  `unverified_sandbox` e a UI a distingue de `verified` de forma que sobreviva a export, print e
  captura de tela. Uma Run sandbox nunca aparece em lista de evidencia verificada sem rotulo.
- Nota estrutural: `AuthorityMode.SANDBOX` existe hoje sem ligacao com `RunSpec`/`Run`. O ADR deve
  decidir se o modo de policy e o trust de execucao sao o mesmo conceito ou dois conceitos que
  colidem no nome. Reusar a palavra sem unificar a semantica e como esta divergencia se torna bug.
- Custo honesto: cria um segundo estado de evidencia que todo consumidor (bundle, API, UI, futuro Lab
  Agent) precisa tratar. E o caminho que a WS-40 assume, e por isso o que mais depende deste ADR
  fechar a fonte de verdade do pacote sandbox.

### Opcao C — manter opt-in

Nada muda no default; o produto instalado assume que o usuario nao cria Studies novos e opera sobre o
pacote canonico importado.

- Afirmavel: exatamente o que hoje e afirmavel. Fail-closed permanece intacto por construcao.
- Proibido: apresentar a instalacao como capaz de autorar Studies; usar `evidrun demo` ou o import
  legado como se fosse caminho de autoria de usuario.
- Bundle/UI: sem estado novo. Em compensacao, a UI precisa dizer explicitamente que autoria esta
  desativada e como habilitar, em vez de falhar com erro de compile que o usuario nao consegue
  interpretar.
- Custo honesto: o produto continua sendo, para um usuario novo, um visualizador de uma fixture. A
  premissa "nao cria Studies novos" precisa ser confrontada com o que WS-01 acabou de entregar; se
  WS-01 cria Project pela CLI/API, esta opcao passa a produzir um produto que cria Project mas nao
  consegue compilar nada nele.

## Invariantes normativas que nao podem ser relaxadas

Nenhuma opcao, recomendacao ou atalho de UX pode tocar nestes pontos. Se uma opcao exigir relaxar
qualquer um, ela esta rejeitada por construcao — registre a rejeicao no ADR.

- Agente, automacao e servico **nunca** afirmam ser humano, preenchem decisao em nome do humano, nem
  transformam campo de ator em prova de autoridade; podem apenas criar draft e pedido de aprovacao
  (`AGENTS.md`, "Invariantes de autoridade e execucao"; ADR 0010).
- Autoridade humana exige `HumanAttestationRecord` verificado. Sem adapter confiavel, API, CLI e
  repository **falham fechado** (`AGENTS.md`; ADR 0010; ADR 0015, que mantem
  `UnavailableHumanAttestationVerifier` como default do processo).
- `repository_fixture` e **nao humano** e entra somente pelo import dedicado do pacote canonico
  completo `CRL-CTX-002`, via `import_legacy_contract_package` (`AGENTS.md`; ADR 0010;
  `docs/contracts/experiment-manifest.md`). Nenhuma opcao pode generalizar esse caminho, alargar o
  conjunto fechado de identidades, nem usa-lo como default de autoria.
- Acoes criticas (`revision.accepted/rejected/superseded`, `evaluation.adjudicated/reviewed`,
  `external_effect.authorized`) exigem humano verificado em qualquer modo (ADR 0015,
  `AuthorityPolicy`). Um modo novo nao pode criar excecao.
- ADR aceito nao e reescrito para mudar decisao: cria-se sucessor (`AGENTS.md`, "Fonte de verdade").
- Documento nao promete capability ausente. Este brief e o ADR descrevem intencao executavel; nenhum
  paragrafo pode descrever sandbox, promocao ou claim de trust como se ja existisse.

## Loop

```text
TASK_ID=WS-03
DELIVERABLE=successor_adr + trust_contract
MAX_REPAIR_LOOPS=6
ALLOW_CODE_CHANGES=0
ALLOW_ADR_REWRITE=0
ALLOW_FAKE_HUMAN=0
HUMAN_DECISION_REQUIRED=1
```

```text
REDISCOVER settings/registry/policy/verifier facts on current main
-> MAP every consumer that would read a trust state (compiler, admission, ledger, bundle, API, UI)
-> MODEL option A/B/C: affirmable, forbidden, bundle+UI distinction
-> ATTACK each option for claim confusion (can any path end up claiming human authority?)
-> WRITE successor ADR with options, trade-offs, rejected alternatives, open questions
-> DERIVE the trust contract WS-40 and the UI will consume
-> REPAIR wording until no sentence overstates the local authenticator
-> HAND OFF for human decision
```

### Condicionais

- Se uma opcao permitir que qualquer caminho de automacao produza um record indistinguivel de
  aceitacao humana, marque P0 e rejeite a opcao no ADR; nao a "conserte" com validacao adicional.
- Se a modelagem exigir um record novo, especifique-o como record proprio; **nunca** reuse
  `RevisionDecisionRecord` para declarar trust nao humano.
- Se `AuthorityMode.SANDBOX` e o trust de execucao divergirem, decida explicitamente no ADR: unificar
  ou renomear. Nao deixe dois significados no mesmo identificador.
- Se WS-01 aterrissar em `main` durante a task, releia a superficie de criacao antes de finalizar a
  Opcao C — a premissa dela pode ter deixado de valer.
- Se a decisao entre A e B depender de informacao que so um humano tem (apetite de risco, publico do
  MVP, o que o produto vai afirmar publicamente), **pare e escale**; nao escolha por default nem
  esconda a escolha numa recomendacao.
- Se o ADR nao conseguir fixar a fonte de verdade do pacote usado numa execucao sandbox, registre isso
  como bloqueio de WS-40 em vez de deixar ambiguo.
- Se surgir requisito de passkey de plataforma ou recovery, abra follow-up; o autenticador local
  opt-in continua o escopo desta fase (ADR 0015, questoes abertas).

## Condicoes de parada e escalacao

Pare e escale, com o ADR em `proposed`, quando:

- as tres opcoes estiverem modeladas e a escolha for genuinamente de apetite de risco;
- uma opcao exigir mudar `AGENTS.md` ou um invariante dos ADRs 0010/0015;
- a decisao implicar afirmar publicamente garantia mais forte que a do autenticador local.

Nao pare quando: faltar leitura de codigo (leia), faltar clareza de vocabulario (proponha), ou o
consumidor a jusante ainda nao existir (especifique o contrato que ele consumira).

## Testes focais e gates

Esta task nao altera codigo, entao nao ha teste de comportamento a escrever. Os gates sao
documentais e de coerencia:

```bash
uv run python scripts/validate_docs.py
```

Verificacoes manuais obrigatorias antes do handoff:

- frontmatter do ADR novo completo, `id` unico no repo, `sources` apontando somente para paths
  existentes, `implementation_refs` e `verification_refs` vazios enquanto nao houver codigo;
- `supersedes` do ADR novo aponta para o antecessor correto; nenhum arquivo de ADR aceito foi
  modificado no diff;
- cada afirmacao sobre codigo no ADR tem um simbolo e um arquivo reais por tras (releia; nao cite de
  memoria);
- nenhuma frase descreve sandbox, promocao ou trust record como implementado;
- cada uma das tres opcoes responde as tres perguntas (afirmavel / proibido / bundle+UI);
- a recomendacao esta tipograficamente separada da decisao, e a decisao esta marcada como pendente de
  humano.

Nao rode a suite completa, linters de codigo ou builds: esta task nao toca `src/` nem `apps/`.

## Handoff

Entregue:

- path e numero do ADR sucessor, e o antecessor que ele supersede quando aceito;
- as tres opcoes com trade-off explicito, mais a recomendacao **rotulada como recomendacao**;
- o contrato de trust que WS-40 implementa: nome do record, estados, quem pode escreve-lo, o que ele
  autoriza, o que ele proibe;
- o vocabulario que a UI (WS-51) deve distinguir, e o que o bundle deve carregar para que a distincao
  sobreviva ao export;
- questoes normativas abertas que WS-40 nao pode resolver sozinha;
- confirmacao de que nenhum arquivo sob `src/` ou `apps/` foi alterado;
- a decisao humana pendente, enunciada como pergunta unica e respondivel.
