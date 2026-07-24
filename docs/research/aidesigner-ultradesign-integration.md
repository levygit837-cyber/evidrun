---
id: research-aidesigner-ultradesign-integration
type: research
title: Integração do AIDesigner para gerações Ultradesign longas
status: draft
authority: research
owner: core
created_at: 2026-07-24
updated_at: 2026-07-24
applies_to: incubation/operator-console-design
sources:
  - https://www.aidesigner.ai/docs/mcp
  - https://www.aidesigner.ai/docs/api
  - https://www.npmjs.com/package/@aidesigner/agent-skills/v/0.1.4
  - user-conversation:2026-07-24-aidesigner-ultradesign
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
observed_at: 2026-07-24
review_due: 2026-08-24
---

# Integração do AIDesigner para gerações Ultradesign longas

> Estado: pesquisa temporal e proposta de experimento, não decisão arquitetural nem comportamento
> implementado. Nenhum contrato, ADR ou código do Evidrun é alterado por este documento.

## Questão e conclusão prática

O problema observado é uma geração completa do AIDesigner que pode durar cerca de dez minutos,
enquanto o harness encerra a chamada da tool antes disso. A duração de dez minutos é observação do
usuário, não garantia publicada pelo fornecedor.

Para **Ultradesign**, a superfície pública comprovada hoje é o MCP: `generate_design` e
`refine_design` aceitam `design_mode: "ultradesign"`. O REST público e o CLI publicado não expõem
esse campo. Porém, o MCP também é uma chamada longa que só devolve `run_id` junto do HTML concluído;
a documentação pública não oferece submit assíncrono, consulta de status, cancelamento ou retomada.

Assim, a opção mais segura para um spike é **MCP + supervisor local de processo**, não uma chamada
MCP bloqueante feita diretamente pelo turno principal do agente. O supervisor devolve um ID local
imediatamente e mantém a conexão longa viva fora do limite da tool do agente. O CLI oficial fica
responsável por captura, preview e adoption do resultado. Isso contorna timeout do harness, mas não
cria capacidades remotas que o AIDesigner não documenta.

## Fatos publicados pelo AIDesigner

### MCP

- O endpoint é `https://api.aidesigner.ai/api/v1/mcp`; Codex é host suportado e config de projeto só
  carrega em repositórios confiáveis. O setup documentado é
  `npx -y @aidesigner/agent-skills init codex --trust-project`.
- MCP usa OAuth gerenciado pelo host. REST usa API key bearer; a documentação recomenda REST quando
  o serviço próprio controla o lifecycle e MCP quando o coding assistant chama a ferramenta.
- `generate_design` recebe `prompt`, `repo_context`, `viewport`, `design_mode`, modo/URL de referência
  e `brand_kit_id`. A resposta de exemplo contém `run_id`, HTML completo, viewport e `created_at`.
- `refine_design` recebe um run ID anterior ou HTML bruto e também aceita `design_mode`.
- `ultradesign` é descrito apenas como o workflow de maior fidelidade, para quem pode esperar mais.
  Não há duração, deadline ou SLA publicado.
- O limite publicado é 30 requisições por 60 segundos e quatro gerações remotas concorrentes por
  conta. `429` traz `Retry-After` e headers de rate limit.
- Sessões de editor permitem criar/parear um projeto, entregar gerações ao canvas e ler resultados
  por `list_canvases`, `get_canvas` e `extract_canvas_design`. O código de pareamento expira em dez
  minutos e só uma sessão fica pareada por OAuth client.
- A referência pública de tools não lista `submit_generation`, `get_generation_status`,
  `cancel_generation` nem equivalente. O `run_id` aparece na resposta final, não como aceite
  antecipado de um job.

Fonte: [documentação oficial do MCP](https://www.aidesigner.ai/docs/mcp).

### REST

- Existe somente o `POST /api/v1/generateDesign` documentado para geração.
- O body público aceita `prompt` ou `messages`, `streaming`, `mode` e `url`; não inclui
  `design_mode`.
- `streaming: true` mantém uma resposta SSE aberta até `[DONE]`; `streaming: false` espera uma única
  resposta JSON. Streaming incremental não equivale a um job assíncrono recuperável.
- A referência não documenta endpoint de status, polling, cancelamento, idempotency key ou retomada.
- Cada request custa ao menos um crédito; análise de URL custa crédito adicional. `401`, `403`,
  `429`, `500` e `502` são os erros documentados.

Fonte: [referência REST oficial](https://www.aidesigner.ai/docs/api).

## Auditoria do pacote público `@aidesigner/agent-skills` 0.1.4

O tarball oficial publicado no npm em 2026-04-11 foi auditado localmente em 2026-07-24, sem
executar autenticação nem uma geração. Esta seção descreve **o pacote cliente público**, não a
implementação privada do servidor do AIDesigner.

Achados do código publicado:

- `generate` e `refine` são helpers síncronos. No fallback REST, usam `streaming: false` e aguardam
  o HTML completo antes de persistir o run.
- A chamada de geração via `fetch` não recebe `AbortSignal` nem timeout próprio. Isso não garante que
  uma camada externa — MCP host, proxy ou harness — deixará a conexão aberta.
- O parser/`--help` oferece `--mode`, `--url` e `--viewport`, mas não `--design-mode`.
- No caminho MCP interno do helper, os argumentos enviados a `generate_design`/`refine_design`
  também não incluem `design_mode`. Portanto o CLI 0.1.4 não é um caminho comprovado para pedir
  Ultradesign, ainda que a documentação MCP mais nova já exponha esse modo.
- O CLI persiste `.aidesigner/runs/<run-id>/` com `request.json`, `repo-context.json`, `design.html`,
  `preview.png`, `summary.json` e artefatos de adoption. O comando `capture` permite persistir HTML
  devolvido pelo MCP junto do remote run ID.
- `refine` preserva parent run local e pode reutilizar remote run ID, mas isso serve a uma nova
  chamada de refinamento; não é consulta ou retomada de uma geração incompleta.

Fonte: [pacote oficial no npm](https://www.npmjs.com/package/@aidesigner/agent-skills/v/0.1.4),
versão e tarball obtidos pelo registry oficial. Há drift observável entre o pacote 0.1.4 e a
documentação MCP consultada: qualquer integração deve fixar a versão e validar o schema vivo de
`tools/list` antes do experimento.

## Skills, prompts e “CoT” observável

O pacote público contém templates de skill, command, referência de API e rubric de frontend. A
orquestração cliente publicamente observável instrui o agente a:

1. inspecionar o repositório e construir um brief visual compacto;
2. preferir MCP para gerar/refinar;
3. tratar o HTML como artefato de design, não implementação final;
4. capturar o resultado em run local, renderizar preview e produzir adoption brief;
5. fazer QA visual e portar tokens/estrutura para o stack real.

O template ainda recomenda uma direção coerente em vez de várias fracas, prompt curto e orientado
por arte, e separar direção visual de especificação detalhada de implementação. Esses são prompts e
regras do **cliente público**. O pacote não publica prompts internos, modelos, etapas ou código do
workflow Ultradesign no servidor.

A documentação do editor afirma que o HTML “streams live onto the canvas”. Ela não documenta a
interface exibida no editor como raciocínio bruto, chain-of-thought privado ou transcrição dos
passos internos do modelo. Portanto, qualquer texto de “CoT” visível deve ser tratado apenas como
**activity/progress apresentado pelo produto**, até existir documentação oficial que defina outra
semântica. Não deve ser armazenado ou citado como prova de raciocínio interno.

Fontes: [MCP e editor sessions](https://www.aidesigner.ai/docs/mcp) e
[pacote cliente público](https://www.npmjs.com/package/@aidesigner/agent-skills/v/0.1.4).

## Limite fundamental do recovery

Um wrapper local consegue manter uma conexão síncrona viva, observar seu processo e persistir a
resposta. Ele **não consegue**, com o contrato público atual, reconectar a uma geração depois que a
conexão foi perdida. Também não pode provar que interromper a conexão cancelou compute remoto ou
evitou cobrança.

Consequências:

- retry automático após timeout ambíguo pode duplicar trabalho e consumir outro crédito;
- cancelar o processo local deve produzir `cancel_requested` ou `outcome_unknown`, nunca
  `cancelled` remoto sem confirmação;
- um worker morto após envio deve virar `outcome_unknown`, não voltar silenciosamente para a fila;
- canvases de uma sessão dedicada podem ajudar a recuperar um resultado visual entregue ao editor,
  mas a documentação não oferece correlação/status suficiente para transformar isso em conclusão
  canônica de um job interrompido.

Essas são inferências conservadoras a partir das ausências no contrato público, não garantias sobre
o backend privado.

## Proposta de spike: supervisor local durável

### Fluxo

1. **Definir antes de gerar.** Humano aprova um brief com superfície, objetivo, conteúdo obrigatório,
   restrições e critério visual. Nenhum crédito é gasto antes dessa aprovação.
2. **Submeter localmente.** `ultradesign submit <brief>` cria um job local e retorna imediatamente
   `local_job_id`; o turno do agente não fica preso à tool remota.
3. **Executar fora do turno.** Um processo/worker separado chama MCP
   `generate_design(..., design_mode="ultradesign")` e mantém a conexão por um deadline explícito
   maior que a duração observada.
4. **Observar.** `ultradesign status <id>` lê estado, heartbeat e logs locais. Sem protocolo remoto de
   progress, heartbeat prova apenas que o worker está vivo, não percentual concluído.
5. **Persistir.** No sucesso, o worker grava resposta bruta de forma atômica e usa `aidesigner
   capture`, `preview` e `adopt`. Credenciais permanecem no host OAuth/Keychain ou ambiente efêmero.
6. **Revisar.** Humano vê o preview e decide aceitar como direção, refinar ou descartar. Nada é
   integrado automaticamente ao produto.

### Estado mínimo local

`queued → running → succeeded | failed | outcome_unknown`, com `cancel_requested` intermediário.
Guardar digest do brief/request, timestamps, attempt, PID/lease, heartbeat, deadline, transport,
editor session opcional, remote run ID somente quando recebido e paths dos artefatos locais. Não
guardar token OAuth/API key.

### Cancelamento e restart

- Antes do envio remoto, cancelamento pode concluir localmente.
- Durante a chamada, enviar aborto/SIGTERM ao worker e registrar resultado desconhecido quanto ao
  backend.
- No restart, jobs `queued` podem ser retomados. Job `running` com processo ainda vivo continua sob
  observação; sem processo vivo vira `outcome_unknown` e exige decisão humana.
- Nunca retry automático de `outcome_unknown`. Primeiro procurar artefato concluído e, se usada uma
  sessão dedicada, verificar canvas; só o humano autoriza nova tentativa/crédito.

## Direção visual do primeiro Ultradesign

Os protótipos existentes estão explicitamente descartados como referência visual. O primeiro brief
deve pedir uma direção nova para o Operator Console, com estas restrições já fornecidas:

- sintetizar `Study → Spec → validação → Admission` como superfícies contínuas;
- evitar composição baseada em cards, blocos quadrados ou blocos arredondados;
- manter aberta, para escolha humana antes da geração, a arquitetura de Runs:
  - Runs no mesmo fluxo contínuo; ou
  - página própria de Observability.

Essa escolha muda a hierarquia global da interface e deve ser decidida antes de gastar o crédito de
Ultradesign. Uma geração não deve inventar a decisão arquitetural em nome do humano.

## Critérios de saída do spike

O spike só sustenta uma decisão posterior se demonstrar:

- schema vivo com `design_mode=ultradesign` no MCP autenticado;
- processo sobrevivendo ao yield/timeout curto do harness por pelo menos o deadline escolhido;
- um resultado persistido com digest do request, HTML, preview e adoption brief;
- estados honestos sob sucesso, falha, interrupção e restart;
- ausência de retry/cobrança duplicada automática em outcome ambíguo;
- revisão visual humana da direção contínua, sem reutilizar os protótipos descartados.

Até esse spike, “MCP + supervisor local” permanece recomendação de research, não capability
implementada.
