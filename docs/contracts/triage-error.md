---
id: contract-triage-error
type: contract
title: Erros estáveis das fases de triagem
status: implemented
authority: normative
volatility: current
owner: core
created_at: 2026-07-26
updated_at: 2026-07-26
applies_to: contracts
sources:
  - github:issue/59
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/triage.py
  - src/evidrun/contracts/admission/rejection.py
  - src/evidrun/entrypoints/api/routers/contracts.py
  - src/evidrun/entrypoints/cli/commands/runs.py
  - src/evidrun/runs/service.py
verification_refs:
  - tests/unit/test_triage_errors.py
  - tests/unit/test_admission_rejection.py
  - tests/integration/test_admission_rejection_surfaces.py
---

# Erros estáveis das fases de triagem

As seis fases anteriores à criação de uma Run compartilham um vocabulário de recusa sem I/O e sem
dependências de API, CLI ou persistência. Este contrato declara a representação e as tabelas que as
fatias verticais seguintes devem consumir; neste estágio, nenhuma borda externa foi alterada.

## Representação

`TriageError` contém:

- `phase`: `parse`, `register`, `decide`, `compile`, `admit` ou `enqueue`;
- `code`: identificador estável prefixado pela fase;
- `category`: classe derivada do código, nunca da mensagem;
- `message`: texto humano em português brasileiro, livre e traduzível;
- `field_path`: caminho ordenado do campo culpado, quando aplicável;
- `remediation`: próxima ação declarada, quando conhecida;
- `issues`, `missing_requirements` e `denied_policies`: achados de admissão em ordem de fold.
- `unresolved_required_capabilities`: refs tipadas das capabilities obrigatórias cujo status no
  inventário resolvido não seja `resolved`; campo aditivo, omitido da serialização quando vazio para
  preservar os payloads existentes das demais recusas.

Mensagens não são parte estável da interface. Código, categoria, status HTTP, exit code e forma do
payload são contrato. Um código novo recebe significado novo; código antigo nunca é reutilizado para
outra condição.

## Catálogo

| Fase | Códigos |
| --- | --- |
| `parse` | `document_not_object`, `contract_type_missing`, `contract_type_unknown`, `field_undeclared`, `revision_invalid`, `identifier_empty`, `payload_type_invalid`, `schema_invalid` |
| `register` | `project_not_found`, `revision_not_monotonic`, `immutability_conflict`, `initial_status_invalid` |
| `decide` | `human_authority_unavailable`, `revision_not_found`, `decision_conflict`, `repository_fixture_forbidden` |
| `compile` | `revision_not_found`, `revision_not_study`, `dependency_not_accepted`, `digest_mismatch`, `controlled_slots_mismatch`, `confounder_missing` |
| `admit` | `run_spec_not_found`, `rejected`, `inventory_not_persistible` |
| `enqueue` | `run_spec_not_found`, `admission_not_found`, `admission_not_admitted`, `admission_run_spec_mismatch`, `digest_mismatch`, `idempotency_key_empty`, `idempotency_conflict`, `retry_source_succeeded`, `retry_admission_not_newer`, `retry_admission_reused`, `retry_legacy_run` |

O valor completo é sempre `<fase>.<código>`. A enumeração em
`src/evidrun/contracts/triage.py` é a fonte executável e exaustiva.

## Categorias e traduções

| Categoria | HTTP | Exit code CLI | Significado |
| --- | ---: | ---: | --- |
| `invalid` | 422 | 2 | documento ou parâmetro inválido |
| `rejected` | 422 | 3 | recusa semântica ou por política |
| `not_found` | 404 | 4 | identidade canônica inexistente |
| `conflict` | 409 | 5 | pedido contradiz estado ou identidade já persistidos |
| `unavailable` | 503 | 3 | autoridade ou persistência necessária indisponível; recusa na CLI |

`HTTP_STATUS_BY_CODE` e `CLI_EXIT_BY_CODE` são totais, imutáveis e independentes. A primeira tabela
preserva indisponibilidade como HTTP 503; a CLI possui somente as quatro classes declaradas (inválido,
recusado, não encontrado e conflito), portanto indisponibilidade usa exit code 3. A verificação falha
se qualquer código ficar sem entrada ou se uma tabela contiver código órfão. Adicionar erro exige, no
mesmo patch: novo membro com prefixo da fase, categoria, ambas as traduções e caso de contrato.
As fases diferentes de `admit` ainda aguardam suas fatias verticais. A rejeição de admissão já
projeta `admit.rejected` nas superfícies da API, CLI e fachada de execução por um único renderizador.

## Causa de rejeição de admissão

Uma admissão rejeitada é persistida antes de a causa alcançar o operador. API e CLI mantêm os campos
de resposta existentes e acrescentam `error` somente quando `decision=rejected`; esse objeto é o
`TriageError` serializado. A API responde com o status de `HTTP_STATUS_BY_CODE` e a CLI termina com o
exit code de `CLI_EXIT_BY_CODE`; portanto `admit.rejected` produz HTTP 422 e exit 3. A fachada de
execução usa a mesma mensagem quando precisa interromper o fluxo de compatibilidade antes da criação
da Run.

O renderizador copia `issues`, `missing_requirements` e `denied_policies` do `AdmissionRecord` sem
reordenar seus itens. A mensagem cita primeiro os `subject_ref` dos issues bloqueantes, depois os
requisitos faltantes e as policies negadas, mantendo a ordem interna de cada tupla persistida. Por
fim, cita capabilities obrigatórias cujo status resolvido não seja `resolved` e as projeta em
`unresolved_required_capabilities`. Esse bloqueio é canônico no inventário e não exige inventar
outro achado no record; consumidores não precisam interpretar a mensagem livre para identificá-lo.

Essa projeção não altera decisão, status de workspace ou interação, capabilities resolvidas, achados
persistidos nem o digest do `AdmissionRecord`. Texto humano permanece livre; consumidores decidem
apenas por código e campos estruturados.
