# Independent QA — Carbon Rhythm

Data da revisão: 2026-07-23  
Escopo: `design/operator-console-prototypes/01-carbon-rhythm`  
Snapshot avaliado: fonte recongelada após a correção dos bloqueios encontrados durante a passagem independente.

## Resultado

O snapshot final passou na QA independente. Não permanece aberto nenhum achado P0, P1 ou P2. Achados P3 não foram perseguidos, conforme o protocolo.

| Severidade | Abertos no snapshot final |
| --- | ---: |
| P0 | 0 |
| P1 | 0 |
| P2 | 0 |
| P3 | não perseguido |

## Achados e revalidação dos bloqueios

### Project isolation — passou

No Chrome, criei o Project local `Sem Study final` e confirmei que ele nasceu sem Study, Run, evidência ou thread herdados de `Release Integrity`:

- o seletor de Project e o painel de Projects passaram a apontar para o novo Project;
- o Chat exibiu `Project: Sem Study final`, `thread isolado` e nenhuma nota anterior;
- `/study` exibiu `Nenhuma Study vinculada`, sem editor de revisão ou linhas de Admission;
- `/runs` exibiu `Nenhuma Run disponível`, sem overview, identificador `run:`, preset Failed/Completed, enqueue ou start;
- ao voltar a `Release Integrity`, a revisão 03 preservou o AdmissionRecord `Rejected` e manteve `Enfileirar 2 RunSpecs` desabilitado.

Isso confirma a fronteira fail-closed: um Project sem Study própria não reutiliza StudyRevision, RunSpec, AdmissionRecord, Run, eventos, evidência ou conversa de outro Project.

### Run preset bypass — passou

No Project sem Study, a rota Runs não materializou presets, Run, Job ou Attempt. Na fixture `Release Integrity`, o AdmissionRecord rejeitado continuou bloqueando enqueue. A suíte final também cobre o fluxo positivo separado, no qual somente uma revisão corrigida e integralmente admitted libera enqueue e o lifecycle do stub.

### Focus trap do diálogo — passou após correção

A primeira passagem independente encontrou fuga de foco do botão de submit para o grip do Chat. No snapshot recongelado, a sequência real de teclado ficou contida no diálogo:

`Nome do Project → Intenção → Cancelar → Criar Project → Fechar diálogo → Nome do Project`

A sequência reversa `Shift+Tab` a partir de `Nome do Project` chegou a `Fechar diálogo`, sem alcançar o conteúdo de fundo. `Escape` fechou o diálogo e restaurou o foco ao gatilho `Criar Project`.

### Overflow horizontal no tablet — passou após correção

A primeira passagem mediu 12 px de overflow horizontal em 834 × 1112. No snapshot recongelado, a medição final foi:

| Métrica | Valor |
| --- | ---: |
| `innerWidth` | 834 px |
| `documentElement.clientWidth` | 819 px |
| `documentElement.scrollWidth` | 819 px |
| `body.scrollWidth` | 819 px |
| descendentes fora do viewport | 0 |
| elementos `<main>` | 1 |
| sobreposição entre main e Chat | 0 px |

O Chat ocupou `x=523…805`, sem ultrapassar a largura útil do documento.

## Gates determinísticos finais

| Gate | Resultado final |
| --- | --- |
| `npm test` | passou: 1 arquivo, 12/12 testes, 0 falhas |
| `npm run build` | passou: Vite 6.4.2, 4.989 módulos transformados, build Sites preparado |
| `npm run test:sites` | passou: 4/4 testes, 0 falhas |
| Console do Chrome em aba fresca | 0 warnings, 0 errors |

A suíte final cobre rotas e browser history, composer vazio, `Shift+Enter`, sequência observável do Agent, snaps e persistência do Chat, Admission rejeitado, revisão corrigida, lifecycle queued → preparing → running → evaluating → terminal, Projects seed sem Study, isolamento de threads e criação de Project sem records herdados.

## Cobertura funcional e de domínio

| Área | Evidência independente |
| --- | --- |
| Lab | objective/context e atividade pública permanecem separados de raciocínio privado; o Lab Agent produz draft, não aceitação humana |
| Projects | criação local, seleção, estado inicial e escopo lógico exercitados; Workspace continua explicitamente separado |
| Study | StudyRevision e RunSpec permanecem records distintos; disclosure `pre_run` rejeita o RunSpec incompatível; nova revisão é append-only |
| Admission | enqueue permanece bloqueado enquanto qualquer RunSpec estiver rejected |
| Runs | nenhuma Run aparece antes de Admission admitted + enqueue explícito; lifecycle e terminal são cobertos deterministicamente |
| Evidência | `ArtifactRef` é apresentado como identificação de conteúdo, sem prometer acesso; bundle não é descrito como replay ou restore |
| Chat | thread isolado por Project, fora do SubjectEnvelope e persistente entre rotas |
| Teclado | skip link, navegação, composer e diálogo foram exercitados; foco do diálogo foi revalidado no DOM real |

## Responsividade

As três viewports obrigatórias foram inspecionadas durante a passagem independente:

| Viewport | Resultado |
| --- | --- |
| Desktop 1440 × 940 | um único `<main>`, rail e Chat sem sobreposição; composer disponível no fluxo da primeira viewport |
| Tablet 834 × 1112 | revalidado após a correção: `clientWidth = scrollWidth = body.scrollWidth = 819`, zero overflow e zero sobreposição |
| Mobile 390 × 844 | um único `<main>`, navegação inferior visível e Chat em bottom sheet; Chat terminou em `y=764` e a navegação começou em `y=772`, com 8 px de separação |

## Direção visual e qualidade de implementação

A implementação preserva a direção da referência `reference/source.png` e das capturas aceitas:

- shell Carbon/graphite contínuo, com superfícies discretas em vez de uma coleção de cards destacados;
- texto quente off-white e acento oxidized orange usados com parcimônia;
- command rail compacto, canvas operacional amplo e densidade coerente com uma console técnica;
- tipografia Manrope + IBM Plex Mono e IDs técnicos tratados como dados, não como ornamento;
- Chat adaptativo como coluna no desktop/tablet e bottom sheet acima da navegação no mobile;
- iconografia importada de Phosphor, sem Lucide, SVG artesanal ou emoji decorativo no source revisado;
- ausência dos elementos visuais proibidos no brief, incluindo status verde decorativo, balance scale, gradients e glows promocionais.

O modo `prefers-reduced-motion: reduce` foi exercitado via CDP: a media query respondeu `true`, animações ficaram sem nome ativo e transições foram reduzidas a `0.001ms` (`1e-06s`).

## Fontes e método

Foram lidos o protocolo independente do diretório pai, `BUILD_BRIEF.md`, `AGENTS.md`, `reference/source.png`, `reference/image-audit.md`, as notas de geração, `design-qa.md`, `qa/manual-audit.md`, `qa/flow.yaml`, source e testes. A comparação visual incluiu todas as capturas aceitas disponíveis. A auditoria combinou o framework de Product Design, os critérios aplicáveis de `design-taste-frontend`, inspeção estática e interação real no Chrome.

## Limites da evidência

- A verificação visual e interativa foi feita em Chrome local; Safari/WebKit e Firefox não foram executados.
- Não houve leitor de tela real, auditoria automatizada completa de contraste ou dispositivo touch físico.
- O long press do grip não foi validado em hardware; os estados do Chat foram cobertos por interação e testes determinísticos.
- Não houve provider/backend real, credenciais, efeito externo, deploy ou publicação.
- Os estados são stubs locais do protótipo; o relatório não os apresenta como integração de produção.

independent result: passed
