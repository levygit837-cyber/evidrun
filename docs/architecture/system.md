---
id: architecture-system
type: architecture
title: Arquitetura do sistema
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: repository
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun
  - apps/web
  - apps/desktop
verification_refs:
  - tests/acceptance/test_demo_flow.py
---

# Arquitetura do sistema

O Evidrun é um monólito modular com três planes:

- **Control Plane:** projetos, experimentos, chats, Lab Agent e aprovações.
- **Execution Plane:** coordinator, worker, Subject Runner, tools e graders.
- **Evidence Plane:** event ledger, snapshots, artifacts, comparações e relatórios.

Superfícies:

- CLI Python;
- FastAPI em loopback;
- worker local;
- React renderer;
- Electron Main e preload.

Electron gerencia o lifecycle do backend, mas não contém regras de domínio. O React usa a mesma API
no browser e no aplicativo desktop. SQLite é canônico localmente; JSONL é exportação.

No estágio atual o coordinator executa o runner determinístico localmente. A interface de worker já
é uma superfície separada, mas leases e execução assíncrona durável pertencem ao próximo marco.

