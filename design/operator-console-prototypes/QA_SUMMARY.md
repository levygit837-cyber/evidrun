# QA consolidada — Operator Console React Design Sprint

Data de fechamento: 23 de julho de 2026  
Escopo: cinco protótipos React locais e independentes, todos com backend demonstrativo em memória.

## Resultado executivo

Os cinco workspaces passaram na matriz automatizada comum, no build de produção, no empacotamento
local compatível com Sites e em uma revisão independente posterior à implementação. O fechamento não
possui finding P0, P1 ou P2 aberto. Findings P3 não foram perseguidos, conforme o protocolo da sprint.

O quinto workspace é a implementação Image-to-Code das seis referências visuais Evidence Ledger já
produzidas na exploração anterior. Ele não agrega, enquadra ou inicia os outros protótipos.

| # | Variante | Método | Testes React | Build | Sites | QA independente |
|---:|---|---|---:|---|---:|---|
| 1 | Carbon Rhythm | Uma nova imagem + audit + implementação guiada | 12/12 | passou | 4/4 | passou |
| 2 | Civic Console | Uma nova imagem + audit + implementação guiada | 13/13 | passou | 4/4 | passou |
| 3 | Command Deck | Direção autônoma sem imagem | 10/10 | passou | 4/4 | passou |
| 4 | Spatial Trace | Direção autônoma sem imagem | 10/10 | passou | 4/4 | passou |
| 5 | Evidence Ledger Open Canvas | Image-to-Code das seis imagens anteriores | 10/10 | passou | 4/4 | passou |

A execução final de `verify-all.mjs` realizou 15 comandos em sequência — `npm test`,
`npm run build` e `npm run test:sites` em cada workspace — com zero falhas.

## Cobertura funcional comum

Cada variante demonstra, por caminhos de UI próprios:

- Lab/Home, Projects, Study e Runs;
- seleção e criação local de Project, com contexto isolado;
- workflow visual entre intenção, StudyRevision, RunSpec, Admission, Run e evidência;
- bloqueio fail-closed quando o Project não possui records próprios;
- Admission rejeitada sem enqueue ou materialização silenciosa de Run;
- Run demonstrativa com job, attempt e lifecycle explicitamente ilustrativos;
- Chat lateral adaptativo, estado compacto, expansão, controle de altura e previews de snap;
- interação stub do Agent com User, Agent, Atividade observável, Tool Call de leitura e Tool Result;
- spinner próprio acima do composer durante execução;
- estados loading, empty, rejected, failed, unavailable e terminal;
- navegação e operações principais por teclado;
- layouts desktop, tablet e mobile;
- `prefers-reduced-motion` para remover motion não essencial.

Nenhum Chat é enviado ao SubjectEnvelope. O Chat é somente uma superfície de operação e interação
demonstrativa do Lab Agent; não altera autoridade, admission ou evidência canônica.

## Revisões visuais novas

Somente duas imagens novas foram geradas, conforme o limite da sprint:

1. [Carbon Rhythm — referência](/Users/apple/Documents/evidrun/design/operator-console-prototypes/01-carbon-rhythm/reference/source.png)
2. [Civic Console — referência](/Users/apple/Documents/evidrun/design/operator-console-prototypes/02-civic-console/reference/source.png)

Cada imagem recebeu uma revisão separada antes do build:

- [Carbon Rhythm — audit da imagem](/Users/apple/Documents/evidrun/design/operator-console-prototypes/01-carbon-rhythm/reference/image-audit.md)
- [Civic Console — audit da imagem](/Users/apple/Documents/evidrun/design/operator-console-prototypes/02-civic-console/reference/image-audit.md)

Os builders receberam os findings como contexto de correção. A imagem funcionou como direção e base,
não como especificação literal; problemas de densidade, abstração, iconografia e legibilidade foram
resolvidos na estrutura React, sem regenerar a imagem.

## Findings corrigidos durante a auditoria independente

### 01 — Carbon Rhythm

- isolou Study, Runs, evidência e Chat por Project;
- impediu presets e enqueue de contornarem Admission;
- adicionou focus trap completo e retorno de foco no diálogo;
- removeu 12 px de overflow horizontal no tablet de 834 px;
- medição final: `clientWidth=819`, `scrollWidth=819`, zero descendants fora do viewport.

Evidência: [tablet sem overflow](/Users/apple/Documents/evidrun/design/operator-console-prototypes/01-carbon-rhythm/qa/screenshots/19-projects-tablet-no-overflow-834x1112.png) ·
[focus trap](/Users/apple/Documents/evidrun/design/operator-console-prototypes/01-carbon-rhythm/qa/screenshots/18-create-project-focus-trap-834x1112.png) ·
[relatório independente](/Users/apple/Documents/evidrun/design/operator-console-prototypes/01-carbon-rhythm/independent-qa.md)

### 02 — Civic Console

- fez Projects sem fixture falharem fechado em Lab, Study e Runs;
- bloqueou todos os presets quando Admission está rejeitada;
- persistiu thread e draft entre rotas, separando ambos por Project;
- completou trap de foco, primeiro campo inválido, `inert` no fundo e retorno ao trigger.

Evidência: [isolamento de Project](/Users/apple/Documents/evidrun/design/operator-console-prototypes/02-civic-console/qa/screenshots/fix-project-isolation-1440x667.jpg) ·
[Chat persistente](/Users/apple/Documents/evidrun/design/operator-console-prototypes/02-civic-console/qa/screenshots/fix-chat-persistence-1425x930.jpg) ·
[relatório independente](/Users/apple/Documents/evidrun/design/operator-console-prototypes/02-civic-console/independent-qa.md)

### 03 — Command Deck

- recuperou labels da navegação no tablet;
- completou a continuidade de foco do diálogo;
- elevou microcopy crítica para no mínimo 14 px;
- alinhou os estados terminal e failed com a semântica demonstrativa da Run.

Evidência: [Run terminal](/Users/apple/Documents/evidrun/design/operator-console-prototypes/03-command-deck/qa/screenshots/21-runs-completed-desktop-lifecycle-type-fix.jpg) ·
[Chat mobile](/Users/apple/Documents/evidrun/design/operator-console-prototypes/03-command-deck/qa/screenshots/20-chat-mobile-390x844-14px-fix.jpg) ·
[relatório independente](/Users/apple/Documents/evidrun/design/operator-console-prototypes/03-command-deck/independent-qa.md)

### 04 — Spatial Trace

- removeu vazamento de records entre Projects;
- sincronizou a etapa visual do workflow com o Project selecionado;
- completou teclado do Project switcher com setas, Home, End, Enter, Space e Escape;
- preservou foco do composer durante e depois de sucesso e falha do Agent.

Evidência: [novo Project em Intento](/Users/apple/Documents/evidrun/design/operator-console-prototypes/04-spatial-trace/qa/screenshots/13-new-project-intent-trace.png) ·
[foco no Chat](/Users/apple/Documents/evidrun/design/operator-console-prototypes/04-spatial-trace/qa/screenshots/14-chat-focus-retained.png) ·
[relatório independente](/Users/apple/Documents/evidrun/design/operator-console-prototypes/04-spatial-trace/independent-qa.md)

### 05 — Evidence Ledger Open Canvas

- isolou Projects locais da fixture CRL-CTX-002 em Study, Runs e Chat;
- manteve o lifecycle stub integralmente em identidades e eventos `demo:`;
- completou foco do diálogo e primeiro campo inválido;
- reestruturou o workflow para caber no canvas sem scroll horizontal interno.

Evidência: [workflow corrigido](/Users/apple/Documents/evidrun/design/operator-console-prototypes/05-evidence-ledger-open-canvas/qa/screenshots/fix-01b-projects-workflow-full.png) ·
[comparação com a referência](/Users/apple/Documents/evidrun/design/operator-console-prototypes/05-evidence-ledger-open-canvas/qa/screenshots/fix-01d-projects-side-by-side.png) ·
[relatório independente](/Users/apple/Documents/evidrun/design/operator-console-prototypes/05-evidence-ledger-open-canvas/independent-qa.md)

## Verificação do repositório EvidRun

Além dos gates isolados dos protótipos, a suíte obrigatória do `AGENTS.md` passou no estado final:

- `uv run pytest`: 104 testes passaram;
- `uv run ruff check .`: passou;
- `uv run pyright`: zero erros e zero warnings;
- `pnpm typecheck:web`: passou;
- `pnpm typecheck:desktop`: passou;
- `pnpm test`: passou para web, desktop e contratos;
- `pnpm build`: passou para web e desktop;
- `uv run python scripts/validate_docs.py`: 74 documentos válidos.

O cache padrão do `uv` não pôde ser inicializado pelo sandbox. Os gates Python foram repetidos com
`UV_CACHE_DIR=/tmp/evidrun-uv-cache`; isso altera somente o local do cache, não o conteúdo testado.

## Limites desta validação

- Dados, provider, backend, authority e lifecycle são stubs locais; nenhum resultado é fato canônico.
- Não houve deploy, hosting, publicação, credencial, write externo ou alteração de contratos.
- Browser QA foi feita em Chrome/in-app browser local; Safari, WebKit e Firefox não foram fechados.
- Não houve leitor de tela real, device touch físico ou auditoria automatizada completa de contraste.
- O long-press foi coberto deterministicamente em testes e por interação de browser, não em hardware.
- `dist/`, `node_modules/`, coverage e logs são artifacts ignorados e não fazem parte do source handoff.

Portanto, os protótipos estão prontos para comparação e seleção visual, mas não são uma implementação
de produção da Operator Console.
