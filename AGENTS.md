# Instruções para agentes

## Fonte de verdade

- Leia `docs/index.md` antes de alterar contratos ou arquitetura.
- ADRs aceitos não são reescritos para mudar uma decisão: crie um ADR sucessor.
- Não descreva roadmap como comportamento implementado.
- Resultados de runs não viram fatos sem referências `run:`, `event:` ou `artifact:`.

## Fronteiras

- Domínio Python não importa FastAPI, SQLAlchemy, OpenAI, Electron ou React.
- Electron Main gerencia lifecycle e capacidades desktop; não implementa domínio.
- Renderer nunca importa `electron`, `node:*` ou bindings nativos.
- Subject Agent não recebe chats, hidden graders ou evidência fora do `SubjectEnvelope` compilado.
- Lab Agent cria drafts; aceitação e efeitos externos pertencem ao humano.
- O provider default é `cliproxyapi-local` com `deepseek-v4-flash` e `reasoning=max`; alterá-lo
  exige ADR sucessor ao ADR 0008.
- API keys permanecem no Keychain ou em variável de ambiente efêmera. Nunca grave credenciais em
  código, docs, ledger, bundles, fixtures, snapshots ou logs.

## Invariantes de autoridade e execução

- Agente, automação e serviço nunca afirmam ser humano, preenchem decisão em nome do humano ou
  transformam um campo de ator em prova de autoridade. Podem criar draft e pedido de aprovação.
- Autoridade humana exige `HumanAttestationRecord` verificado. Sem adapter confiável, API, CLI e
  repository falham fechado; `repository_fixture` é não humano e só entra pelo import dedicado do
  pacote canônico completo `CRL-CTX-002`.
- `human_review` é avaliação humana primária; adjudicação decide precedência sobre records anteriores.
  Ambas são append-only e exigem autoridade humana verificável quando executadas.
- Nenhuma Run nova existe antes de `AdmissionRecord.decision=admitted` para o RunSpec exato.
- Falha, ausência ou incompatibilidade de capability obrigatória rejeita a admissão; capacidade
  representável não é anunciada como executável.
- O runtime ativo rejeita todo input `sensitive` ou `restricted`; não improvise materialização
  classificada fora de um adapter admitido.
- Evento factual precisa ser válido para a fase da Run e apontar para seu record canônico. Eventos de
  pause/resume, tool, skill, checkpoint e progress permanecem reservados até seus coordinators.
- O runner ativo só admite `max_wall_seconds` e uma única interação. Budgets de tokens, output,
  tools ou custo, `max_turns > 1`, pause e stop conditions fora de `goal_complete`/
  `budget_exhausted` terminal rejeitam a admissão.

## Invariantes de disclosure e evidência

- `SubjectEnvelope` é allowlist fechada. Campo novo de RunSpec, contract, artifact ou evaluation não
  entra automaticamente no envelope.
- `ArtifactRef` não possui `locator` em nenhum contrato. Não reintroduza path, URL ou storage
  locator em SubjectEnvelope, EvaluatorEnvelope, ResolvedAgentInventory ou bundles.
- O documento exato do SubjectEnvelope ainda não é persistido/exportado; o digest alegado em
  `subject.invoked` não torna o envelope recomputável pelo bundle.
- Disclosure `pre_run` continua compilável no SubjectEnvelope puro, mas todo modo diferente de
  `none` rejeita a admissão porque o runner recebe apenas objective e context.
- `ArtifactRef` identifica conteúdo; não concede acesso, montagem, exportação ou leitura.
- `SubjectRespondedPayload` deve respeitar o shape do capture mode, e o ledger deve exigir o modo
  exato declarado no RunSpec.
- Timeout de `max_wall_seconds` termina a Run por `run.budget_exhausted`; não o converta em
  `completed` nem omita o evento terminal.
- Progress Artifact é resumo derivado e ancorado em checkpoint alcançado ou intervalo de turnos do
  Subject; turno significa evento válido `subject.responded`. Não é inventário de arquivos, dump de
  memória nem segunda fonte de verdade. Sem observer/persistência, sua policy rejeita a admissão.
- EvaluationRecords, reviews e adjudicações são append-only; correção cria novo record.
- `bounded_exploration` termina por disposition/stop condition e nunca por pass/fail ou achievement
  inventado. Disposition e stop reason seguem o ADR 0013; lifecycle, conclusão do Goal e qualidade
  permanecem eixos separados. O runtime bounded continua indisponível.
- Bundle auditável não é automaticamente portátil nem replayable. Nunca prometa blobs, grants,
  restore, replay ou estado privado recuperável sem contrato e verificação específicos.
- `artifact-manifest.json` enumera refs intencionais do bundle; nunca o descreva como telemetria de
  todo arquivo lido, editado ou observado.
- O verificador do Bundle v2 deve validar lifecycle, contratos queued/terminal, IDs da comparison,
  records/eventos de evaluation e o conjunto completo de artifact entries; checksum isolado não basta.

## Verificação obrigatória completa

```bash
uv run pytest
uv run ruff check .
uv run python scripts/check_code_budget.py
uv run pyright
pnpm typecheck:web
pnpm typecheck:desktop
pnpm test
pnpm build
uv run python scripts/validate_docs.py
```

O benchmark `CRL-CTX-002` deve continuar offline e determinístico.

## Agent skills

### Issue tracker

Issues e PRDs ficam como issues do GitHub (`gh` CLI). Consulte `docs/agents/issue-tracker.md`.

### Triage labels

Cinco labels canônicas com nomes padrão (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). Consulte `docs/agents/triage-labels.md`.

### Domain docs

Layout single-context: `CONTEXT.md` + `docs/adr/` na raiz. Consulte `docs/agents/domain.md`.
