# Operator Console React Design Sprint

Este diretório contém cinco protótipos React independentes. Eles são artifacts exploratórios de
design e não alteram contratos, backend, DTOs, Electron ou a implementação em `apps/web`.

## Matriz

| Workspace | Direção | Fonte visual | Porta |
|---|---|---|---:|
| `01-carbon-rhythm` | Carbon Rhythm | Uma imagem nova, criada apenas para esta variante | 4301 |
| `02-civic-console` | Civic Console | Uma imagem nova, criada apenas para esta variante | 4302 |
| `03-command-deck` | Command Deck | Direção autônoma, sem imagem | 4303 |
| `04-spatial-trace` | Spatial Trace | Direção autônoma, sem imagem | 4304 |
| `05-evidence-ledger-open-canvas` | Evidence Ledger Open Canvas | Seis imagens já selecionadas na exploração anterior | 4305 |

O quinto workspace é a geração de código da direção visual anterior. Ele não é agregador nem
launcher dos demais.

## Contrato comum

Cada protótipo deve oferecer Lab, Projects, Study e Runs; dados locais explicitamente marcados como
stub; fluxo navegável; interação demonstrável do Agent com `Atividade observável`, Tool Call e Tool
Result; spinner próprio acima do composer; e Chat adaptativo com dock lateral, expansão, controle de
altura e previews de snap por long-press.

Cada workspace possui seu próprio `package.json`, lockfile, dependências, fontes, testes e artifacts
de QA. Nenhum protótipo importa arquivos de outro. Os prompts detalhados ficam dentro do próprio
workspace para preservar isolamento de contexto.

## Verificação esperada por workspace

```bash
npm test
npm run build
npm run test:sites
npm run dev -- --host 127.0.0.1 --port <porta> --strictPort
```

Os relatórios finais ficam em `design-qa.md` e `qa/manual-audit.md`; ações reproduzíveis de browser
ficam em `qa/flow.yaml`; screenshots aceitas ficam em `qa/screenshots/`.

## Estado final

Os cinco workspaces passaram em `npm test`, `npm run build` e `npm run test:sites`, totalizando
15 execuções com zero falhas na matriz comum. Cada implementação também recebeu uma auditoria
independente pós-build e encerrou sem finding P0, P1 ou P2 aberto.

Resultados, correções e limites de validação estão consolidados em
[QA_SUMMARY.md](./QA_SUMMARY.md).

## Limite de produto

Os protótipos não são Runs canônicas e não podem produzir autoridade humana, evidência real ou
efeito externo. Project e Workspace permanecem distintos; StudyRevision, RunSpec, AdmissionRecord,
Run, job e attempt também. Chat não entra no SubjectEnvelope.
