---
id: architecture-codebase-layout
type: architecture
title: Layout da codebase, costuras e orçamento estrutural
status: accepted
authority: normative
volatility: current
owner: core
created_at: 2026-07-24
updated_at: 2026-07-26
applies_to: repository
sources:
  - docs/adr/0003-modular-monolith.md
  - docs/adr/0017-structural-budget-and-named-seams.md
  - docs/architecture/system.md
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/check_code_budget.py
  - scripts/check_import_directions.py
  - scripts/import_directions_typescript.py
  - code-budget.toml
  - import-directions.toml
  - src/evidrun/settings.py
  - src/evidrun/contracts/admission/service.py
  - src/evidrun/runs/composition.py
  - src/evidrun/evidence
  - src/evidrun/infrastructure/database/repository.py
verification_refs:
  - tests/unit/test_code_budget.py
  - tests/unit/test_import_directions.py
  - tests/unit/test_admission_oracle.py
---

# Layout da codebase

Este documento é `current` porque combina regras arquiteturais com um mapa navegável do repositório.
As quatro seções abaixo têm papéis diferentes: invariantes atemporais governam mudanças; estado
atual é conferível no disco; alvo futuro é apenas direção; histórico de entrega fica fora daqui.

Vocabulário: **módulo** tem uma interface e uma implementação; **costura** é onde vive a interface;
**adaptador** é uma implementação concreta nessa costura; **profundidade** é a alavancagem oferecida
por uma interface pequena.

## Invariantes e direções atemporais

### Fronteiras de runtime

- O domínio Python não importa FastAPI, SQLAlchemy, OpenAI, Electron ou React.
- Electron Main gerencia lifecycle e capacidades desktop; não implementa domínio.
- O Renderer não importa `electron`, `node:*` nem bindings nativos.
- O Subject Agent recebe somente o `SubjectEnvelope` compilado.
- O Lab Agent cria drafts; aceitação e efeitos externos permanecem humanos.
- Persistência hidrata contratos, mas não se torna dona das regras do domínio.

### Direção conceitual

O fluxo canônico é unidirecional:

```text
entrypoints -> authoring -> compilation -> admission -> run coordination -> evidence
                                      \-> infrastructure adapters <-/
desktop main -> API lifecycle <-HTTP/SSE-> web adapters -> features
```

`contracts/` contém vocabulário e validação sem I/O. `runs/` coordena execução sem assumir
autoridade humana. `evidence/` sela e verifica records canônicos. `infrastructure/` fornece
adaptadores de persistência, artifacts e providers. `entrypoints/` e `apps/` traduzem interfaces
externas e não decidem regras do domínio.

Este diagrama declara direção arquitetural; não afirma, sozinho, que todos os imports atuais a
respeitam. `scripts/check_import_directions.py` verifica o subconjunto estático e versionado descrito
em [Gate de direção de imports](../governance/import-directions.md); imports dinâmicos e cópia
semântica de regras continuam exigindo revisão.

### Costuras e módulos profundos

- Uma costura só é promovida quando há variação real. Um adaptador é uma hipótese; dois adaptadores
  justificam a costura.
- Chamadores e testes atravessam a mesma interface. Estado interno não vira interface para facilitar
  teste.
- Dependências são recebidas na raiz de composição. Regras retornam resultados observáveis antes de
  produzir efeitos externos.
- Se duas escritas precisam commitar juntas, pertencem à mesma fronteira transacional.
- Projeções de status, dashboard, comparison e relatório derivam do ledger; não viram segunda fonte
  de verdade.

### Orçamento estrutural

`code-budget.toml` é a política versionada e `scripts/check_code_budget.py` é o gate executável.
Thresholds, exceções e baseline vêm desses arquivos, não de números copiados neste documento. Um
arquivo acima do orçamento é um sinal para procurar responsabilidade ou costura escondida, nunca
permissão automática para dividir por contagem de linhas.

## Estado atual gerado ou medido

O mapa abaixo é uma ajuda de navegação, não um inventário exaustivo. Confirme paths no checkout e
use os `implementation_refs` do frontmatter antes de afirmar comportamento atual.

```text
src/evidrun/
├── settings.py             configuração e paths fora das camadas inferiores
├── shared/                 tipos e ports sem dependências para cima
├── contracts/
│   ├── base.py             modelos-base e capability_ref
│   ├── authoring/          revisions e parse de autoria
│   ├── runtime/            RunSpec, eventos e envelopes
│   └── admission/          envelope, checks e AdmissionService
├── runs/
│   ├── adapters/           catálogo e adaptadores de Subject, grader e tool
│   ├── admission/          checks do par concreto de adaptadores
│   ├── coordinator/        preparação, tentativa, resume e tool trace
│   ├── composition.py      raiz de composição do runtime
│   └── worker.py           claim, heartbeat e release
├── evidence/
│   ├── export/             formatos de bundle
│   ├── verify/             verificação por versão e records
│   ├── archive.py          archive, checksums e artifact manifest
│   └── bundle.py           interface das operações de bundle
├── authority/              verificação, policy e fluxo de autoridade humana
├── infrastructure/
│   ├── database/           UnitOfWork e agregados de persistência
│   ├── artifacts/          armazenamento endereçado por conteúdo
│   └── providers/          adaptadores e credenciais efêmeras/Keychain
└── entrypoints/            API, CLI e worker

apps/
├── web/src/
│   ├── api/                transporte HTTP/SSE
│   ├── data/               interfaces e adaptadores do frontend
│   └── features/           apresentação, estado e modelos puros
└── desktop/src/            main, preload e shared para lifecycle desktop
```

As costuras atuais mais importantes são:

- `runs/composition.py`: raiz única de montagem do Runtime Kernel;
- `contracts/admission/service.py`: dobra checks declarados e checks de adaptadores num
  `AdmissionRecord` observável;
- `infrastructure/database/repository.py`: raiz de composição dos agregados que compartilham o
  `UnitOfWork`;
- `evidence/bundle.py`: interface pequena para exportar e verificar bundles, com implementação
  dividida por formato;
- modelos puros em `apps/web/src/features/`: derivação separada de React e do transporte.

Para atualizar esta seção, meça o checkout atual. Não copie contagens de arquivos, linhas, tickets,
commits ou resultados de uma execução anterior. `scripts/check_code_budget.py`, testes e manifest
documental são projeções reproduzíveis; cada um prova somente o contrato declarado pelo próprio
gate.

## Alvo futuro e planning

O alvo é manter uma pasta por capacidade e nomear costuras somente onde adaptadores realmente
variam. Mudanças futuras devem preservar a direção conceitual, a atomicidade dos agregados e as
interfaces observáveis de admission, ledger e bundles.

Detalhamento, ordem e dependências de trabalho pertencem a [`docs/planning/`](../planning/) e ao
tracker. Esses documentos têm autoridade `planning` e volatilidade `snapshot`; não descrevem
capacidade implementada. Quando um alvo aterrissa, atualize esta seção a partir do código final e de
verificação nova, sem importar a narrativa histórica do task document.

## Histórico de entrega

PRs, issues, commits, datas, contagens e a sequência em que extrações chegaram permanecem no Git e
no tracker. ADRs registram decisões duráveis, não cronologia operacional. Este documento não mantém
listas “entregue em #N”, árvores antigas nem baselines copiados de uma execução passada.

## Roteamento para agentes

Antes de abrir arquivos de implementação, responda:

1. **Muda contrato?** Leia o contrato afetado e o ADR vigente antes de tocar modelos, schema ou
   payload persistido/exportado.
2. **Muda capacidade executável?** Localize declaration, adapter concreto e admissão fail-closed;
   uma forma representável não prova execução.
3. **Muda uma projeção?** Parta do ledger ou record canônico e preserve a derivação; dashboard,
   report e bundle manifest não são fontes independentes.
4. **Muda uma costura?** Teste pela interface observável e confirme que existe variação real antes
   de adicionar porta ou adaptador.

Use o perfil apropriado no [roteador documental](../index.md). Planning, research e incubação só
entram quando forem o objeto explícito da tarefa.
