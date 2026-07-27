---
id: product-run-anomaly-and-user-recourse-concept
type: product
title: Anomalia de Run e recurso do usuário
status: draft
authority: incubation
volatility: snapshot
owner: product
created_at: 2026-07-27
updated_at: 2026-07-27
observed_at: 2026-07-27
applies_to: product/run-anomaly-recourse
sources:
  - user-conversation:2026-07-27-ws02-desktop-worker-lifecycle
  - docs/adr/0014-durable-runtime-kernel.md
  - docs/adr/0013-bounded-exploration-terminal-semantics.md
  - docs/planning/tasks/02-desktop-worker-lifecycle.md
  - docs/operations/runtime-worker.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
review_due: 2026-10-27
---

# Anomalia de Run e recurso do usuário

> Estado: ideia preservada para avaliação. Este documento não descreve runtime existente, não define
> contrato aceito e não autoriza implementação. Parte da proposta original **está bloqueada por
> eventos reservados**, e o bloqueio está explicitado abaixo em vez de contornado.

## Origem

A proposta surgiu ao fatiar a WS-02, a partir de uma pergunta de produto: uma Run que falha por
motivo operacional termina como `failed`, e o usuário que gastou tokens e tempo de espera não recebe
nenhum caminho de recurso. O pedido original tinha quatro partes:

1. um estado de "anomalia" antes do terminal, para falha inesperada de runtime, provider ou
   travamento;
2. persistir o resultado e as métricas parciais até o ponto da falha;
3. um botão crítico, com confirmação explícita e consentimento registrado, avisando que retomar pode
   comprometer a consistência dos dados;
4. em vez de retomar a Run original, criar um "fork" ou "Sub-Run" que preserve o contexto até o ponto
   anterior à anomalia.

Depois, uma quinta parte, que se tornou a principal: permitir **continuar a mesma Run** de onde o
agente parou, com o contexto que já é do usuário, quando a interrupção foi de transporte — uma queda
de rede de segundos numa execução longa. O argumento: se os tokens, os dados e o tempo são do
usuário, o produto não deveria bloqueá-lo de continuar mediante consentimento explícito de que o dado
perde confiabilidade.

A intuição de produto é legítima e a quinta parte é tecnicamente fundamentada. O que este documento
separa é o que já existe, o que é atrito de interface, e o que exige decisão normativa.

## O que já existe e atende partes da proposta

### `not_assessable` já é a anomalia

`GoalStateTerminalResult.state` (`src/evidrun/contracts/runtime/events.py:207`) tem quatro valores:
`achieved`, `partially_achieved`, `not_achieved` e `not_assessable`. O último é escrito exatamente
nos casos que a proposta chama de anomalia: invocação indeterminada, resposta não recuperável,
inconsistência canônica de runtime.

A separação que a proposta pede — distinguir "o modelo errou" de "a infraestrutura quebrou" — já é
normativa e implementada. `not_achieved` é resultado científico. `not_assessable` é ausência de
resultado. Um estado novo reintroduziria a mesma distinção com outro nome.

O padrão de desenho de dois eixos independentes também já existe, no
[ADR 0013](../adr/0013-bounded-exploration-terminal-semantics.md): `disposition` separado de
`stop_reason`, o estado da investigação separado da causa da parada.

### Os dados parciais já são persistidos

Nada é descartado quando uma Run falha. O ledger é append-only encadeado por hash; `subject.responded`
grava `input_tokens`, `output_tokens` e `tool_calls` em `metadata`; sob policy `raw_encrypted` o
Subject result é persistido como artifact antes da avaliação, e `resume.py` consegue avaliá-lo sem
nova chamada ao provider.

A parte 2 da proposta descreve o comportamento default, não uma capability ausente. **O que falta é
a interface expor isso** em vez de exibir apenas a palavra `failed`. Esse é o achado mais acionável
deste documento: metade do valor pedido existe e está invisível.

### O caminho de refazer já existe

`POST /api/v1/runs/{id}/retries` está implementado e exige `Idempotency-Key` mais uma
AdmissionRecord nova criada depois do terminal da Run de origem. Ele cria outra Run com `retry_of`
declarado. Não tem superfície na UI.

Ponto central para a frustração descrita: essa admissão nova **não é aprovação humana**. O RunSpec
não muda, não existe revision nova para aceitar, não há autoria envolvida. Admissão é resolução de
inventário, workspace e capabilities efetivas — uma operação de máquina. A percepção de "aprovar Run
e spec nova" é atrito de interface, não exigência de contrato: refazer pode ser um clique que
orquestra admit e retry por baixo.

## Correções de vocabulário

Três termos da proposta colidem com significado já reservado.

**"Fork" está reservado e declaradamente ausente.** Aparece em
`docs/contracts/evaluation-checkpoint-v1.md` na lista do que não está implementado, junto com
restore, replay e context extraction, e no backlog pós-MVP do roadmap como "restore, replay e fork
por checkpoint". Reusar a palavra para outro conceito criaria colisão com uma decisão pendente.

**"Sub-Run" e "Run-filha" não existem no modelo.** Uma Run é atômica, ligada a um RunSpec e a uma
AdmissionRecord exatos. Não há hierarquia de Runs. O mecanismo de linhagem existente é `retry_of`,
que cria uma Run irmã com proveniência declarada.

**Três níveis costumam ser confundidos.** RunSpec é a configuração imutável e compilada. Run é uma
tentativa científica sobre um RunSpec e uma admissão exatos. Attempt é uma tentativa **operacional**
de executar aquela Run. Expiração de lease cria attempt novo na mesma Run; Run nova existe apenas por
retry explícito.

## Sobre "fork" a partir do ponto da anomalia

A parte 4 do pedido original — criar uma Run nova preservando o contexto até o ponto anterior à
anomalia — precisa ser lida à luz da distinção acima.

Se ela significa reenviar o transcript registrado para uma execução que continua o trabalho, é o
Caso B: derivável do ledger, dependente do coordinator de suspensão, e melhor resolvido dentro da
mesma Run do que criando outra.

Se ela significa materializar o estado interno de uma Run num ponto arbitrário e ramificar dali, é
restore por checkpoint — que está declaradamente ausente e reservado no backlog pós-MVP junto com
replay e fork.

Em ambos os casos, os tokens e o tempo já consumidos no trecho perdido não retornam. O que pode ser
preservado é o trabalho já registrado, não o custo.

## Continuar a mesma Run: dois casos que não são o mesmo

A intenção do pedido é explícita e legítima: se o contexto, os tokens e o tempo são do usuário, o
produto não deveria impedi-lo de continuar de onde o agente parou, desde que ele consinta e entenda
que o dado perde confiabilidade. A referência dada foi um harness de agente de codificação: quando o
loop para, o usuário manda uma mensagem e o trabalho retoma.

Essa analogia é precisa e vale examiná-la, porque ela nomeia o mecanismo. Um harness desse tipo não
preserva estado do modelo — o modelo é stateless. O harness **reenvia o transcript durável** como
contexto de uma chamada nova. A continuidade é reconstruída a partir de um log, não recuperada de uma
sessão suspensa.

Esse mecanismo já é o que o Evidrun usa. O [ADR 0016](../adr/0016-real-subject-read-tool-and-tracing.md)
decidiu que a continuação não depende de `previous_response_id`: o adapter reenvia o transcript
mínimo delimitado — objective, inventário permitido, function call e function output — a cada round,
porque o provider opera com Responses não persistidas. Continuação por reenvio de transcript não é
capability a inventar; é como o loop de tools funciona hoje.

O que muda entre os dois casos é se existe transcript parcial durável para reenviar.

### Uma Run já é uma sessão de agente

Um mal-entendido a desfazer antes dos casos, porque ele leva a conclusões erradas: `max_turns=1` não
significa uma única chamada ao modelo.

`ResponsesReadAgentAdapter.execute` é um loop: pede ao provider, serve todas as function calls que
vierem, acumula no transcript, reenvia e repete, saindo somente quando o modelo responde sem chamar
tool. Estruturalmente é o loop de um harness de agente. O
[ADR 0016](../adr/0016-real-subject-read-tool-and-tracing.md) é explícito: "rounds internos de
provider e tool permanecem uma única interação do Subject. Eles não aumentam `max_turns`". Os rounds
são limitados por `max_tool_calls`, pelo wall clock iniciado em `run.running` e pelo lease ativo.

`max_turns` conta interações do Subject com o laboratório, não round-trips com o provider. Uma Run é
uma sessão de agente com loop, tools, transcript e terminal — o mesmo formato de um harness de
codificação, com propósito e fronteiras diferentes: allowlist fechada no envelope, ledger append-only
como autoridade, hidden expected fora do alcance do Subject. O Subject é observado, não assistido.

A lacuna real de largura não é o loop: é a quantidade de capabilities. Existe exatamente uma tool
(`read_text`, confinada ao `SubjectEnvelope`) e o adapter recusa qualquer outra configuração. Runtime
genérico de tools e skills continua rejeitado na admissão. Isso é diferente de não haver loop.

### Caso A — invocação sem nenhum round completo: não há de onde continuar

Se a conectividade cai antes de qualquer round produzir resultado durável, não existe transcript
parcial: o Subject não chegou a produzir nada persistido. "Onde o modelo parou" não tem referente.

Aqui refazer é a única opção honesta, e o produto deve dizer isso claramente em vez de oferecer uma
retomada que não retoma nada. O [ADR 0014](../adr/0014-durable-runtime-kernel.md) rejeitou reinvocar
silenciosamente dentro da mesma Run porque isso pode duplicar efeitos ou produzir dois resultados sob
uma única identidade.

Nuance do mesmo caso: se a resposta **foi** gravada e só a avaliação falhou, o sistema já retoma
sozinho. `resume.py` reconstrói o result do artifact cifrado e avalia sem tocar o provider.

### Caso B — interrupção no meio do loop: existe transcript, falta coordinator

O cenário que motivou o pedido — o agente progredindo por rounds, a rede cai por segundos — é
executável hoje, e o material para retomar já é gravado. Cada `tool.called` e `tool.completed`
persiste `arguments_ref` e `result_ref` como artifacts canônicos no ledger, com operation keys
derivadas do `call_id`.

O `_LoopState.transcript` vive em memória e morre com o processo, mas ele é **derivável do ledger** —
que é precisamente como um harness reconstrói contexto. Uma Run que morre no quinto de oito rounds
deixou rastro suficiente para reenviar o transcript delimitado.

Ou seja, a reconstrução de transcript não depende de capability futura. O que falta não é o dado.

O que falta é lifecycle. `not_assessable` hoje só existe acompanhando o evento terminal, e
`terminal.py` fecha o lease sem escrever nada quando a Run já é terminal — `operation_key="run:terminal"`
impede um segundo terminal. O ledger append-only encadeado por hash impede **desfazer** um terminal;
ele não impede acrescentar eventos a uma Run que ainda não terminou. Portanto a pergunta correta não
é como reabrir uma Run terminal, e sim **por que ela foi terminada em vez de suspensa**.

`run.paused` e `run.resumed` já existem como tipos, com payload e phase gates definidos, e estão em
`UNSUPPORTED_RUNTIME_EVENT_TYPES` (`src/evidrun/contracts/runtime/events.py`) porque seus coordinators
não existem. O `AGENTS.md` os mantém reservados por isso. A decisão pendente é operacional, não
conceitual: quem detém o lease de uma Run suspensa, por quanto tempo ela pode ficar assim, e o que
acontece com o wall clock enquanto isso.

Este é o achado central deste documento: a intenção do pedido não é incompatível com a arquitetura —
ela é a razão de existir de eventos que o sistema já modelou e deixou reservados. Falta uma decisão,
não uma permissão.

**Restrição que permanece:** o loop existe e o rastro é durável, mas a suspensão não. Sem coordinator,
uma interrupção de transporte no meio do loop vai direto a terminal, e o terminal não se desfaz.
Promover retomada exige decidir a suspensão — não afrouxar nenhum check de admissão.

O que **também** limita o cenário na prática, e é outra frente: a largura de capabilities. Com uma
única tool de leitura, o trecho de trabalho perdido numa interrupção é pequeno. O incentivo para
retomar cresce junto com a largura do runtime de tools, que continua rejeitado na admissão.

### O que não deve ser prometido em nenhum dos casos

Reconstruir o estado de uma Run em um ponto arbitrário. Bundles são `references_only` e o documento
exato do `SubjectEnvelope` não é recomputável por eles. Reenvio de transcript registrado é diferente
de restore de estado intermediário: o primeiro é derivável do ledger, o segundo não existe.

## Onde o consentimento explícito tem valor

O diálogo de confirmação proposto tem valor real, porém não para autorizar retomada. O que protege o
dado agregado é **marcar a Run resultante**: uma Run refeita depois de anomalia deveria carregar
proveniência distinta de um retry ordinário, para que uma análise sobre repetições possa filtrá-la.

Um detalhe correlato, observado ao analisar a proposta e fora do escopo dela: `max_wall_seconds`
começa no primeiro `run.running` e attempts posteriores herdam o budget restante. Uma Run que falhou
no meio e foi retomada por novo attempt não é rigorosamente irmã das outras em condição de tempo.
Isso afeta comparabilidade em lote e pertence à WS-06, não a este documento.

## Recomendações separadas por natureza

**Sobre contrato vigente, sem ADR:**

- apresentar `not_assessable` como categoria distinta de `not_achieved` na interface, com os eventos
  e métricas parciais já persistidos;
- expor o retry existente como ação de um clique, orquestrando admissão e retry sem apresentar
  contrato ao usuário;
- deixar visível quantos attempts uma Run consumiu, para que um pesquisador possa descartá-la de uma
  análise se quiser rigor máximo.

**Decisões abertas, que exigem ADR sucessor:**

- **Suspensão em vez de terminal para falha de transporte no meio do loop.** Promover
  `run.paused`/`run.resumed` de reservado a suportado, decidindo quem detém o lease de uma Run
  suspensa, por quanto tempo, e o que acontece com o wall clock enquanto isso. É o que torna a
  retomada pedida possível. Não depende de capability nova de execução: o loop e o rastro durável já
  existem.
- **Reconstrução do transcript a partir do ledger.** Hoje o transcript vive apenas em memória no
  adapter. Derivá-lo dos eventos de tool persistidos é o que permite reenviar contexto após
  interrupção, e precisa de contrato próprio para não virar segunda fonte de verdade.
- **Retomada consentida como evidência tipada.** O consentimento explícito do usuário — de que a Run
  retomada pode conter dado não confiável — registrado no ledger junto com a proveniência da
  retomada, para que uma análise agregada possa filtrar essas Runs. Consentir registra; não autoriza
  silêncio.
- **Distinção de proveniência entre retry ordinário e retry após anomalia**, para o Caso A, onde
  refazer é a única opção.

A posição de produto que sustenta as três: o sistema não deve impedir o usuário de continuar com
contexto e tokens que são dele. Deve impedir que uma retomada seja **indistinguível** de uma execução
limpa nos dados. A proteção é proveniência, não proibição.

## Fora deste documento

Restore, replay, fork por checkpoint, bundle portátil, estado intermediário reconstruível, o
coordinator de suspensão e o de turnos, e budget de custo aplicado. Nenhum deles é promovido aqui.
Este documento registra intenção e nomeia a decisão que falta; ele não habilita capability.
