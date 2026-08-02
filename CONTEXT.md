# Evidrun

Laboratório local e benchmark-first para transformar hipóteses sobre agentes em experimentos versionados, Runs auditáveis e evidência verificável, onde o humano mantém autoridade sobre aceitação, acesso sensível e efeitos externos.

Este arquivo é a linguagem ubíqua do projeto. A fonte de verdade normativa completa é `docs/product/glossary.md` e os ADRs em `docs/adr/`; quando um termo aqui conflitar com um ADR aceito, o ADR prevalece.

Nas superfícies voltadas a pessoas, o nome natural em inglês aparece primeiro e o identificador técnico fica
entre parênteses quando necessário para auditoria ou suporte. Os identificadores v1 continuam
estáveis em contratos, API, CLI, eventos, banco e bundles.

## Autoria e estrutura

**Workspace**:
Fronteira durável do Control Plane para isolamento de dados, regras locais e futura sincronização.
Contém Projects, mas nunca é o ambiente materializado para uma Run.
_Avoid_: tenant, account

**Project**:
Linha coerente de investigação dentro de um Workspace. Organiza autoria, conversas, memória,
proveniência e Runs relacionadas; não é diretório de filesystem nem instância de agente.
_Avoid_: folder, directory, per-project agent

**Study**:
Raiz de autoria para uma pergunta, hipótese, avaliação, diagnóstico ou exploração; compila uma Run ou uma matriz de Runs.
_Avoid_: experiment, test, trial

**Study Purpose (`StudyIntent`)**:
Propósito e perguntas do laboratório. É a intenção de quem investiga, nunca instrução automática entregue ao Subject.
_Avoid_: prompt, instruction

**Agent Task (`Goal`)**:
Objetivo e limites entregues ao Subject; permanece separado da avaliação e distinto do StudyIntent.
_Avoid_: prompt, objective (isolado)

**Scenario**:
Inputs, condições observáveis, limitações e provenance versionados para uma Run.
_Avoid_: case, test case

**Variant**:
Override tipado sobre um blueprint; variants pré-Run são irmãs de uma mesma comparação.
_Avoid_: version, branch

**Execution Plan (`RunSpec`)**:
Configuração atômica, imutável e compilada de scenario, variant e repetição. Uma Run existe apenas para um RunSpec exato.
_Avoid_: config, settings

## Execução

**Run Environment**:
Ambiente efêmero, admitido e materializado para uma única Run a partir de configuração versionada.
Não é o Workspace do Control Plane e “sandbox” não deve ser usado como sinônimo.
_Avoid_: Workspace, laboratory workspace, sandbox

**Readiness Check (`AdmissionRecord`)**:
Decisão pré-fila que resolve inventário, Run Environment e capabilities efetivas. Nenhuma Run existe antes de uma admissão `admitted` para o RunSpec exato.
_Avoid_: approval, validation

**Run**:
Tentativa ligada a um RunSpec e a um AdmissionRecord exatos.
_Avoid_: test, trial, job

**Subject Agent**:
O sistema sob teste dentro de uma Run. Recebe apenas o SubjectEnvelope. Não confundir com
`authority subject`, que é o conteúdo assinado numa attestation humana (`HumanSubjectEnvelope`,
ADR 0015) e não é um agente.
_Avoid_: model, assistant, SUT, Lab Agent, authority subject

**Lab Agent**:
Copiloto do Control Plane e superfície primária de trabalho do laboratório. Conduz formulação de
hipótese, propõe drafts de qualquer contract de autoria, propõe métricas e graders, explica Runs e
evidência. Não possui autoridade humana: não decide, não aceita, não atesta e não fala com o Subject.
_Avoid_: Subject Agent, assistant

**LabAgentEnvelope**:
Contexto declarado do Lab Agent: Workspace obrigatório, Project e foco opcionais, contracts
visíveis, evidência autorizada por referência, sessão e capabilities efetivas. Nunca contém
credenciais nem concede acesso implícito a outro Project.

**MemoryEntry**:
Entrada de memória operacional do Lab Agent sob isolamento obrigatório de Workspace e escopo
opcional de Project, discriminada por `kind` (`rule`, `preference`, `decision`, `observation`,
`episode`), append-only e promovida por humano. `observation` exige `evidence_refs`; memória não é
evidência e não entra no SubjectEnvelope.
_Avoid_: memory dump, cache, história

**Cue**:
Pergunta que uma MemoryEntry responde, escrita como o usuário perguntaria. É o campo de descoberta,
não palavra-chave. Anti-cue declara o que a entrada não cobre.
_Avoid_: keyword, tag, label

**Agent Inventory**:
Requisitos de runner, provider, tools, skills e runtime de uma Run.
_Avoid_: dependencies, requirements

**Resolved Agent Inventory**:
Snapshot hasheado do que a admissão realmente resolveu. Inventário não prova uso.

**Subject Context (`SubjectEnvelope`)**:
Visão mínima compilada por allowlist fechada, entregue ao Subject. Sem StudyIntent, hipótese, plan completo, chats, hidden graders ou credenciais.
_Avoid_: contexto irrestrito, payload, prompt

**Checkpoint**:
Marco validado e ancorado no ledger. Não significa restore nem replay.
_Avoid_: snapshot, savepoint, restore point

## Contexto

**Context Policy**:
Regra de seleção, ordem, truncamento ou transformação de contexto.

**Context Plan**:
Candidatos e decisões considerados antes da montagem do contexto.

**Context Snapshot**:
Entrada de contexto efetivamente entregue numa invocação.
_Avoid_: prompt, input

**Context Diff**:
Diferença classificada entre dois Context Snapshots.

**Context Mount**:
Inclusão explícita de conhecimento ou sessão anterior no contexto.

## Evidência

**Event**:
Observação append-only da execução; o event ledger é a autoridade normativa da Run.
_Avoid_: log, message

**Artifact**:
Conteúdo identificado por digest e metadata.
_Avoid_: file, blob, output

**ArtifactRef**:
Referência a um Artifact por identidade de conteúdo. Não possui locator de storage e não concede acesso, montagem, exportação ou leitura.
_Avoid_: path, URL, locator, link

**Artifact Access Grant**:
Autorização, separada da identidade, que limita consumer, finalidade, operações, classification e prazo de acesso a um Artifact.
_Avoid_: permission, ACL

**Progress Artifact**:
Resumo provisório, derivado e append-only ancorado a uma boundary alcançada (checkpoint ou intervalo de turnos do Subject). Não é inventário de arquivos nem segunda fonte de verdade.
_Avoid_: summary, report, memory dump

**Audit Evidence Bundle (`Evidence Bundle audit`)**:
Pacote verificável de records, refs e digests. Não promete todos os blobs, restore nem replay.
_Avoid_: export, archive, backup

**Portable Evidence Bundle (`Evidence Bundle portable`)**:
Perfil futuro de bundle com blobs autorizados e manifest de completude para uso offline declarado.

## Avaliação e autoridade

**Evaluation Plan (`EvaluationPlan`)**:
Dimensões, stages, gates, disclosure, blinding e agregação opcional de uma avaliação.
_Avoid_: rubric, criteria

**Recorded Evaluation (`EvaluationRecord`)**:
Resultado vetorial, ancorado e append-only produzido por grader, judge ou humano; correção cria novo record.
_Avoid_: result, score, grade

**Grader**:
Avaliador versionado que produz um EvaluationRecord.
_Avoid_: Grade, scorer, judge

**Comparison**:
Leitura pareada de Runs e seus trade-offs.
_Avoid_: benchmark, ranking, diff

**Human review**:
Avaliação humana primária declarada como stage do EvaluationPlan.

**Human adjudication**:
Decisão humana posterior sobre precedência entre records existentes, sem sobrescrita.
_Avoid_: override, correction

**Human Attestation**:
Evidência tipada de verificação humana que cobre principal, ação e conteúdo exatos; sem adapter confiável a operação falha fechada.
_Avoid_: signature, approval, token

**Repository Fixture Authority**:
Importa aceitação de fixture legado por caminho interno dedicado; é explicitamente não humana.
_Avoid_: human authority, admin

**Execution Revision Set**:
Conjunto fechado e ordenado da Study e de todas as revisions necessárias para compilá-la, escopado
a um Project e identificado por digest canônico.
_Avoid_: latest revisions, mutable draft collection, sandbox package

**Execution Trust Record**:
Record imutável que liga um RunSpec exato a um Execution Revision Set e declara se esse conjunto foi
ou não confirmado por autoridade humana. Não descreve isolamento do Run Environment.
_Avoid_: approval, sandbox, admission, authority token

**ReviewPackage**:
Projeção legível do Execution Revision Set, das diferenças e das condições efetivas que uma pessoa
precisa revisar. Não é attestation nem concede autoridade por si só.
_Avoid_: approval bundle, Evidence Bundle

**ReviewTarget**:
Documento canônico mínimo que liga o digest do Execution Revision Set aos digests ordenados de todos
os RunSpecs revisados. É a identidade semântica; não é o relatório visual.
_Avoid_: ReviewPackage bytes, PDF digest, approval

**Bounded exploration result**:
Resultado em dois eixos, disposition operacional e stop reason factual; nenhum é pass/fail nem score.
_Avoid_: pass/fail, outcome, verdict

## Conversas

**General chat**:
Sessão do Lab Agent escopada ao Workspace, sem Project ou foco. Pode navegar identidades de Projects,
mas não recebe acesso implícito ao conteúdo de todos eles.
_Avoid_: global chat

**Project chat**:
Sessão do Lab Agent escopada a exatamente um Project, que também pode usar regras e preferências do
Workspace pai. Não lê outro Project e não representa um agente próprio daquele Project.

**Focused chat**:
Sessão de Project adicionalmente estreitada a um Study, Run ou Comparison pertencente ao mesmo
Project.

**Lab Agent turn**:
Uma mensagem do humano e todo o trabalho do agente até um terminal nomeado. Pode conter várias idas ao
provider e várias tool calls. Não é turno do Subject e não produz Event de Run.
_Avoid_: turno do Subject, round-trip, request

**Lab Agent tool catalog**:
Conjunto fechado de tools oferecido a uma sessão, derivado da sua forma. Tool ausente do catálogo
efetivo é recusada sem execução; acrescentar tool ao catálogo normativo exige ADR sucessor.
_Avoid_: plugin, function registry, skill

**Lab Agent refusal**:
Recusa por código estável em uma das etapas de verificação, sempre com remediação acionável endereçada
ao modelo. Alvo fora do escopo é indistinguível de alvo inexistente.
_Avoid_: erro genérico, exception, denial

**Composed system instruction**:
Instrução de sistema montada por base invariante, um bloco de escopo e um bloco de capabilities
derivado do catálogo efetivo. Descreve a fronteira para o modelo cooperar; nunca a implementa.
_Avoid_: prompt, template, persona

**Lab Agent tool trace**:
Registro de Control Plane de cada tool call, com scope efetivo, refs solicitadas e refs devolvidas
separadas. Vive fora do event ledger e nunca é Event, bundle ou evidência de Run.
_Avoid_: log, event, audit event
