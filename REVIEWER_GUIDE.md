# Evidrun — guia para avaliadores

> **Resumo em 30 segundos:** o Evidrun é um laboratório local-first para avaliar agentes de IA com foco em evidência. Ele registra o que mudou entre baseline e candidato, qual contexto e quais ferramentas foram realmente entregues, como a execução progrediu, como foi avaliada e quais conclusões os dados permitem sustentar.

## Por que este projeto existe

Avaliações de agentes frequentemente reduzem uma execução complexa a uma nota final. O Evidrun trata a própria execução como evidência: contratos são revisionados, Runs passam por admissão explícita, eventos são duráveis, resultados podem ser exportados em bundles verificáveis e capacidades não implementadas são recusadas em vez de simuladas silenciosamente.

O projeto é hoje um laboratório técnico, não um serviço SaaS concluído. Sua principal contribuição é o runtime auditável e o modelo de evidência.

## O que inspecionar

| Superfície | Por que importa | Ponto inicial |
|---|---|---|
| Lifecycle canônico de Run | Mostra preparação, admissão, enqueue, worker e estados terminais explícitos | `src/evidrun/runs/` |
| Evidence bundles | Exporta evidência versionada de Run/comparação e verifica integridade | `src/evidrun/evidence/` |
| Contracts e autoridade | Separa intenção, revisão, trust e autoridade de execução | `src/evidrun/contracts/`, `src/evidrun/authority/` |
| Infraestrutura durável | Implementa persistência, filas, leases, retries e armazenamento de artifacts | `src/evidrun/infrastructure/` |
| Benchmark determinístico | Exercita a infraestrutura sem depender de um modelo externo | `benchmarks/` |
| Superfícies de produto | CLI, API, interface web, Laboratory conectado e shell Electron | `src/evidrun/entrypoints/`, `apps/` |
| Gates de engenharia | Executa testes, typing, lint, schemas, documentação e budgets estruturais | `.github/workflows/ci.yml` |

## Arquitetura em uma visão

```mermaid
flowchart LR
    A[Study e contracts] --> B[Authority e admission]
    B --> C[RunSpec e job durável]
    C --> D[Worker e Subject]
    D --> E[Event ledger e artifacts]
    E --> F[Graders e comparação]
    F --> G[Evidence bundle]
    G --> H[Verificação independente]
```

## Sinais de engenharia

- Contracts canônicos e digests imutáveis separam intenção declarada de estado mutável do runtime.
- O caminho de Run usa jobs duráveis, attempts, leases, heartbeats, fencing e retry, não apenas um loop em memória.
- Event ledger e evidence bundles permitem verificar integridade e identificar evidência ausente ou alterada.
- Subjects determinístico e model-backed compartilham a mesma fronteira de execução.
- A admissão rejeita combinações de capabilities não suportadas explicitamente.
- A documentação distingue contracts e ADRs normativos de plans e research temporais.
- O CI valida código, contracts, artifacts gerados, documentação e restrições estruturais.

## Limites atuais

O runtime público é propositalmente menor que o modelo completo de contracts. A admissão executável permanece concentrada em `single_turn`, workspace `in_process` e avaliação determinística. Tools genéricas, skills, nested agents, graph protocol, checkpoints automáticos, Progress Artifacts, bounded exploration e restore/replay completo continuam incompletos.

Os bundles atuais oferecem integridade e auditabilidade, mas não tornam uma Run arbitrária automaticamente portátil ou replayable. A reprodutibilidade mais forte hoje pertence ao benchmark determinístico offline e aos caminhos explicitamente cobertos por fixtures e testes.

Esses limites são parte da proposta: o repositório procura deixar visível a fronteira entre comportamento implementado, contrato representável e trabalho futuro.

## Avaliação rápida

```bash
uv sync --extra dev
pnpm install
uv run evidrun init
uv run evidrun doctor
uv run evidrun demo
uv run pytest
pnpm test
```

Para uma revisão de código focada:

1. `src/evidrun/runs/service.py`
2. `src/evidrun/runs/coordinator/`
3. `src/evidrun/runs/worker.py`
4. `src/evidrun/evidence/bundle.py`
5. `docs/contracts/study-run-v1.md`
6. `.github/workflows/ci.yml`

## Topics sugeridos no GitHub

`ai-agents`, `agent-evaluation`, `llm-evaluation`, `evals`, `agent-observability`, `provenance`, `reproducibility`, `context-engineering`, `local-first`, `fastapi`, `electron`, `pydantic`

## Interpretação de portfólio

O Evidrun é o repositório mais forte deste portfólio para avaliadores interessados em confiabilidade de agentes, infraestrutura de evals, provenance e auditabilidade. A alegação adequada não é que exista uma plataforma comercial concluída nem execução long-horizon completa; é que o projeto demonstra uma arquitetura substancial e test-backed para tornar experimentos de agentes inspecionáveis, verificáveis e, nos caminhos determinísticos cobertos, reproduzíveis.
