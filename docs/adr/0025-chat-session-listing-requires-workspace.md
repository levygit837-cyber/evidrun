---
id: adr-0025
type: adr
title: Exigir Workspace na listagem de sessões de chat
status: accepted
authority: normative
volatility: timeless
owner: product
created_at: 2026-08-02
updated_at: 2026-08-02
applies_to: chat-session-listing
sources:
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/infrastructure/database/read_model/queries.py
  - src/evidrun/entrypoints/api/routers/evidence.py
  - src/evidrun/entrypoints/cli/commands/runs.py
verification_refs:
  - tests/integration/test_chat_workspace_scope.py
---

# Contexto

O ADR 0020 definiu Workspace como raiz durável de isolamento local e permitiu que a superfície de
Project mantivesse uma leitura global para navegação humana. O ADR 0021 tornou o Workspace obrigatório
em toda sessão do Lab Agent e recusou leitura implícita entre Projects. Faltava decidir se a listagem
de sessões poderia continuar global, ser derivada do dashboard ou exigir que o caller declarasse a
fronteira de Workspace.

Sessão de chat contém conteúdo de usuário e contexto operacional do laboratório. Uma listagem global
misturaria esse conteúdo entre Workspaces antes que qualquer Project ou foco pudesse estreitar a
leitura.

# Decisão

Listar sessões de chat exige `workspace_id` explícito. API e CLI não oferecem forma global, Workspace
padrão implícito nem fallback pela projeção de dashboard. O dashboard global não projeta sessões de
chat porque não recebe a fronteira necessária para autorizar essa coleção.

Workspace inexistente devolve lista vazia, assim como Workspace existente sem sessões. Um `404`
permitiria usar a rota de chat como oráculo de existência de Workspace, embora a operação seja listar
conteúdo dentro de uma fronteira declarada e não resolver essa fronteira como alvo.

A assimetria com `GET /projects`, cujo filtro de Workspace permanece opcional, é deliberada. Project é
estrutura mínima de navegação do Control Plane; sessão de chat é conteúdo de usuário submetido à hard
boundary de Workspace do ADR 0021. Permitir navegação estrutural global não concede leitura global do
conteúdo das conversas.

# Alternativas rejeitadas

- Manter a listagem global de sessões: atravessa a fronteira de Workspace e mistura conteúdo de
  usuário sem escopo declarado.
- Filtrar por um Workspace escolhido implicitamente: torna o resultado dependente de estado externo
  ao request e esconde qual fronteira autorizou a leitura.
- Preservar `chats` no dashboard global: reintroduz a mesma leitura sem um parâmetro capaz de
  delimitá-la.
- Devolver `404` para Workspace inexistente: cria um oráculo de existência na superfície de conteúdo.
- Tornar também a listagem de Projects obrigatoriamente escopada nesta decisão: confunde estrutura de
  navegação com conteúdo de usuário e amplia a quebra sem necessidade.

# Consequências

Callers de `GET /api/v1/chat/sessions` e `evidrun chat list` precisam fornecer `workspace_id`. A
listagem consulta sessões diretamente, filtra pelo Workspace exato e mantém ordem determinística por
`created_at` descendente e `id` ascendente. Consumidores do dashboard deixam de esperar a coleção
`chats`.

O corte é incompatível com callers que usavam a forma global anterior, mas elimina o vazamento entre
Workspaces na fonte em vez de depender de filtro no frontend ou de instrução ao Lab Agent.
