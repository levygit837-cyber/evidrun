---
id: contract-observable-errors
type: contract
title: Catálogo de erros observáveis por costura
status: implemented
authority: normative
volatility: current
owner: core
created_at: 2026-07-31
updated_at: 2026-07-31
applies_to: repository
sources:
  - github:issue/46
  - docs/contracts/triage-error.md
  - docs/contracts/workspace-project-surface-v1.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/triage.py
  - src/evidrun/contracts/scope.py
  - src/evidrun/evidence/verify/failures.py
  - apps/desktop/src/shared/desktop-contract.ts
verification_refs:
  - tests/unit/test_triage_errors.py
  - tests/unit/test_scope_contracts.py
  - tests/unit/test_bundle_failures.py
  - tests/integration/test_runtime_kernel.py
  - apps/desktop/src/shared/bridge-errors.test.ts
---

# Catálogo de erros observáveis por costura

Um refactor pode preservar o happy path e alterar silenciosamente uma falha observável. Este
documento enumera as costuras públicas, onde vive o catálogo executável de cada uma e onde estão
seus testes de contrato.

O princípio é único em todas elas: **código, categoria, status/exit code e forma do payload são
contrato; mensagem é texto livre para o humano.** Nenhuma borda deduz causa a partir de texto.

## Costuras e seus catálogos

| Costura | Representação | Fonte executável | Testes |
| --- | --- | --- | --- |
| Fases de triagem (`parse`, `register`, `decide`, `compile`, `admit`, `enqueue`) | `TriageError` | `src/evidrun/contracts/triage.py` | `tests/unit/test_triage_errors.py` e a matriz por fase |
| Criação de Workspace/Project | `ScopeError` | `src/evidrun/contracts/scope.py` | `tests/unit/test_scope_contracts.py` |
| Verificação de Evidence Bundle | `BundleVerificationFailure` | `src/evidrun/evidence/verify/failures.py` | `tests/unit/test_bundle_failures.py`, `tests/integration/test_runtime_kernel.py` |
| Desktop bridge | `BridgeError` | `apps/desktop/src/shared/desktop-contract.ts` | `apps/desktop/src/shared/bridge-errors.test.ts` |

`TriageError` e `ScopeError` são contratos separados de propósito: criar uma fronteira do Control
Plane não é uma das seis fases que antecedem uma Run. Ver
[erros de triagem](triage-error.md) e [Workspace/Project v1](workspace-project-surface-v1.md).

## Verificação de bundle

`verify()` responde três eixos independentes — checksums, cadeia de eventos e records — e `valid`
exige todos. Esses mapas decidem validade, mas não diziam **por que** um bundle foi recusado: o
consumidor precisava ler nomes de chave e adivinhar seu significado.

`failures` é uma projeção aditiva desses mapas. Ela não altera `valid`, `checksums`, `event_chains`
nem `records`, então consumidores existentes continuam funcionando.

| Código | Categoria | Significado |
| --- | --- | --- |
| `bundle.checksums_absent` | `integrity` | O arquivo não enumera a si mesmo; nada pode ser verificado |
| `bundle.checksum_mismatch` | `integrity` | Um membro não corresponde ao digest selado |
| `bundle.file_list_incomplete` | `integrity` | Um arquivo entrou sem entrada de checksum |
| `bundle.duplicate_file_name` | `integrity` | Dois membros do zip compartilham um path |
| `bundle.event_chain_invalid` | `ledger` | O replay contradiz as regras do próprio runtime |
| `bundle.structure_invalid` | `record` | O layout do bundle não reproduz |
| `bundle.record_invalid` | `record` | Um record persistido não reproduz |

A ordem é determinística: integridade, depois ledger, depois record; cada eixo ordenado por subject.
Isso permite comparar duas verificações sem ordenar antes. Um bundle válido produz `failures` vazio,
então `failures` e `valid` não podem discordar sobre haver recusa.

Um arquivo adicionado **com** checksum correto passa integridade e é recusado pela allowlist exata,
portanto seu código é `bundle.record_invalid` e nunca `bundle.checksum_mismatch`.

## Desktop bridge

O Main lança através de uma fronteira IPC e o renderer recebe apenas a mensagem serializada. Por
isso o código é prefixado na própria mensagem: sem isso não sobraria nada estável para ler do outro
lado. `bridgeErrorCodeOf` recupera o código de um `Error` ou de uma string.

`bridge.invalid_backend_handshake` e `bridge.invalid_executor_handshake` são distintos porque os dois
processos anunciam coisas diferentes; um código único apagaria qual plano falhou.

## Como adicionar um erro novo

1. Declare um membro novo no enum da costura, prefixado pelo nome dela.
2. Adicione a categoria e todas as traduções (`HTTP_STATUS_BY_CODE`, `CLI_EXIT_BY_CODE`) no **mesmo
   patch**. As tabelas são totais e a verificação falha se um código ficar sem entrada.
3. Acrescente um caso de contrato que exercite o ramo observável.
4. Nunca reutilize um código antigo com significado novo. Código antigo mantém seu significado; uma
   condição nova recebe um código novo.

Mensagem não é congelada por padrão. Congele texto apenas quando ele for declaradamente parte da
interface pública ou necessário para equivalência de refactor.

## O que este catálogo prova e não prova

Prova que cada costura listada possui representação estável, tabelas totais e testes que exercitam
seus ramos observáveis. Um refactor que mude código, categoria, status ou forma de payload falha
nesses testes antes de ser aceito.

Não prova que toda mudança semântica foi percebida, que a cobertura é suficiente, nem que uma
mensagem livre permaneceu adequada. Essas conclusões pertencem a Spec, Standards e Verification.

Fora deste catálogo por decisão explícita: `ProviderRequestError`, cujo código sanitizado já é
coberto em `tests/unit/test_provider.py`, e falhas internas de runtime que não atravessam uma
superfície pública.
