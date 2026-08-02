---
id: docs-index
type: architecture
title: Roteador da documentação Evidrun
status: implemented
authority: normative
volatility: current
owner: core
created_at: 2026-07-22
updated_at: 2026-07-28
applies_to: repository
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/validate_docs.py
verification_refs:
  - docs/_generated/manifest.json
---

# Roteador da documentação Evidrun

Escolha um perfil pela intenção da tarefa e leia somente seus documentos obrigatórios. `AGENTS.md`
continua sendo a instrução operacional do repositório e não conta no orçamento do perfil. Não faça
uma leitura integral de `docs/` antes de saber a tarefa.

Quando um perfil disser “documento afetado”, selecione somente o contrato, ADR ou operação que a
mudança toca. Um documento opcional entra apenas quando uma pergunta concreta não puder ser
respondida pelos obrigatórios.

## Autoridade e tempo

- `normative`: contrato, ADR ou regra que governa a implementação. Conflitos são resolvidos pela
  fonte normativa mais específica e vigente.
- `informative` e `non-normative`: explicam ou demonstram; não alteram contrato.
- `planning`, `research` e `incubation`: intenção, observação temporal ou hipótese. Nunca provam
  comportamento atual.
- `timeless`: invariantes e decisões que mudam somente por revisão normativa.
- `current`: retrato do comportamento implementado; confirme `implementation_refs` e código.
- `snapshot`: estado datado que pode estar obsoleto.
- `generated`: projeção reproduzível; sua autoridade vem das entradas e do gerador, não do arquivo.

O [manifest gerado](_generated/manifest.json) serve para inventário. Ele não promove planning,
research, incubação ou snapshot a fonte de comportamento atual.

## Perfis mínimos

### Domínio e terminologia

Obrigatórios, 3 documentos e até 4.000 palavras:

1. [`CONTEXT.md`](../CONTEXT.md)
2. [Glossário](product/glossary.md)
3. [Charter](product/charter.md)

Opcional: a [linguagem do pipeline](product/pipeline-language.md) quando a tarefa tocar nomes de
produto ou a narrativa entre autoria e evidência; ou o ADR vigente do termo discutido. Proibidos como fonte de terminologia implementada:
research, incubação, planning e roadmap.

Roteamento atual: Workspace/Project/Run Environment usa o
[ADR 0020](adr/0020-workspace-project-run-environment-boundaries.md); sessão, scope e memória do Lab
Agent usam o [ADR 0021](adr/0021-hierarchical-lab-agent-scope.md); runtime, tools e instruções do Lab
Agent usam o [ADR 0024](adr/0024-lab-agent-native-tool-runtime.md); trust de execução usa o
[ADR 0022](adr/0022-explicit-execution-trust-without-per-run-authentication.md).

### Lab Agent

Obrigatórios, 3–4 documentos e até 8.000 palavras:

1. [ADR 0024](adr/0024-lab-agent-native-tool-runtime.md)
2. o único contrato do Lab Agent afetado: [tools](contracts/lab-agent-tools-v1.md),
   [loop](contracts/lab-agent-loop-v1.md), [erros](contracts/lab-agent-errors-v1.md),
   [instruções](contracts/lab-agent-instructions-v1.md),
   [store de sessão](contracts/lab-agent-session-store-v1.md) ou
   [escopo](contracts/lab-agent-scope-v1.md)
3. [ADR 0018](adr/0018-lab-agent-copilot-scope.md), quando a fronteira de autoridade estiver em escopo
4. [ADR 0021](adr/0021-hierarchical-lab-agent-scope.md), quando sessão ou memória estiver em escopo

Opcional: [agentes e autoridade](architecture/agents-and-authority.md) para a fronteira entre Lab
Agent e Subject; o [contrato de memória v2](contracts/lab-agent-memory-v2.md) quando a tarefa tocar
`informed_by` ou retrieval. Proibido: descrever o Lab Agent como existente em `src/evidrun/`, tratar
instrução de sistema como fronteira de isolamento, ou anunciar tool que o catálogo efetivo não ofereça.

### Contrato ou schema

Obrigatórios, 3–4 documentos e até 8.000 palavras:

1. [Glossário](product/glossary.md)
2. o único [contrato](contracts/) afetado
3. o ADR vigente que decide esse contrato
4. [Governança documental](governance/documentation.md), quando metadata ou schema documental mudar

O contrato antecessor é opcional somente para compatibilidade. Planning, research, fixtures e
schemas gerados são proibidos como autoridade normativa; schemas gerados podem apenas confirmar a
projeção da implementação.

### Runtime

Obrigatórios, 4 documentos e até 8.000 palavras:

1. [Arquitetura do sistema](architecture/system.md)
2. [Runtime de providers](architecture/provider-runtime.md)
3. [Operação do worker](operations/runtime-worker.md)
4. o contrato de Run ou provider afetado

Opcional: ADR 0014 ou 0016 quando a decisão correspondente estiver em escopo. Planning, research,
benchmarks demonstrativos e incubação são proibidos como fonte de capacidade ativa.

### Evidence ou bundle

Obrigatórios, 4 documentos e até 9.000 palavras:

1. [Dados e evidência](architecture/data-and-evidence.md)
2. o contrato de bundle afetado: [v1](contracts/evidence-bundle.md),
   [v2](contracts/evidence-bundle-v2.md), [v3](contracts/evidence-bundle-v3.md) ou
   [v4](contracts/evidence-bundle-v4.md)
3. [Run Event](contracts/run-event.md)
4. [ADR 0011](adr/0011-progress-artifacts-and-bundle-boundaries.md)

O catálogo de payloads é opcional quando um Event mudar. Relatórios, manifests, benchmarks e
planning são proibidos como prova isolada de completude, portabilidade, replay ou autenticidade.

### Frontend ou desktop

Obrigatórios, 4 documentos e até 6.000 palavras:

1. [Arquitetura do sistema](architecture/system.md)
2. [Runtime desktop](architecture/desktop-runtime.md)
3. [Contrato da bridge](contracts/desktop-bridge.md)
4. [ADR 0004](adr/0004-python-core-typescript-ui-and-electron.md)

Opcional: [segurança Electron](security/electron-security.md) quando a bridge, preload ou lifecycle
mudar. Mockups, conceitos de produto, research e planning são proibidos como comportamento atual.

### Segurança

Obrigatórios, 4–5 documentos e até 9.000 palavras:

1. [Threat model](security/threat-model.md)
2. [Privacidade e retenção](security/privacy-and-retention.md)
3. [Agentes e autoridade](architecture/agents-and-authority.md)
4. [Captura e retenção](contracts/capture-and-retention.md)
5. o ADR de autoridade vigente, quando autoridade humana ou trust de execução estiver em escopo

Roteamento atual: o [ADR 0022](adr/0022-explicit-execution-trust-without-per-run-authentication.md)
preserva a exigência de attestation para claims humanos e decide o caminho futuro de execução
explicitamente não verificada; o [ADR 0015](adr/0015-human-subject-envelope-and-authenticator-lifecycle.md)
continua governando o autenticador local opt-in.

Opcional: segurança Electron para mudanças desktop. Planning, research, exemplos e logs não
substituem contrato, ameaça reproduzível ou teste de segurança.

### Operação

Obrigatórios, 3 documentos e até 5.000 palavras:

1. [Desenvolvimento local](operations/local-development.md)
2. o runbook afetado em [`operations/`](operations/)
3. [Arquitetura do sistema](architecture/system.md)

Opcional: contrato do recurso operado. Propostas, roadmap e snapshots são proibidos como instrução
operacional atual; um documento `proposed` não deve ser executado como runbook implementado.

### Planejamento

Obrigatórios, 3 documentos e até 6.000 palavras:

1. [Entrada de planning](planning/README.md)
2. [Mapa temporal de capabilities](planning/mvp-capability-map.md)
3. o único task document ou roadmap em escopo

Opcional: issue/PR correspondente no tracker e o
[contrato de mudança](governance/change-contract.md) quando a implementação usar o gate de escopo.
Planning organiza intenção e dependências, mas é proibido como prova de comportamento atual; valide
qualquer claim de entrega no código, Git, testes e records canônicos.

## Orçamento warning-only

Os limites de documentos e palavras acima são guardrails de seleção, ainda não gates bloqueantes.
Ao exceder um limite, registre o perfil, os documentos adicionais e a pergunta que justificou cada
um. Não conte `AGENTS.md`, este roteador nem trechos abertos para localizar o documento correto.

Incubação, research e planning nunca entram por padrão em perfis de implementação. Histórico de
entrega pertence ao tracker e ao Git; ADRs preservam decisões e são sucedidos, não reescritos para
esconder histórico.
