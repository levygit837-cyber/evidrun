---
id: adr-0024
type: adr
title: Runtime nativo de tool calling para o Lab Agent
status: accepted
authority: normative
volatility: timeless
owner: product
created_at: 2026-08-02
updated_at: 2026-08-02
applies_to: lab-agent-runtime
sources:
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/adr/0016-real-subject-read-tool-and-tracing.md
  - docs/contracts/lab-agent-scope-v1.md
  - docs/contracts/triage-error.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Contexto

O ADR 0018 deu ao Lab Agent escopo funcional amplo e o ADR 0021 fixou um único papel com sessões
hierárquicas. O contrato de escopo v1 definiu envelope, formas de sessão e enforcement de tool. O que
nenhum deles decidiu é **como o loop executa**: qual mecanismo de tool calling, quem valida os
argumentos, o que acontece quando o modelo erra, e como o produto impede que uma proposta plausível
falhe depois no compilador.

Três fatos do repositório motivam esta decisão.

O primeiro é que o loop do Subject existe e **não é reutilizável**.
`ResponsesReadAgentAdapter.execute` exige `SubjectEnvelope`, exige um `ToolTraceSink` que é o event
ledger, deriva o teto de `envelope.budgets.max_tool_calls` e valida que existe exatamente uma
capability resolvida. Cada um desses quatro é acoplamento ao Execution Plane. O Lab Agent tem
proibição dura de escrever no ledger, portanto reusar aquele adapter violaria o ADR 0018 na primeira
chamada de tool.

O segundo é que **o compilador e a admissão já são um avaliador determinístico de propostas**.
`compile.controlled_slots_mismatch` recusa uma comparação controlada que não isola sua variável
primária; `compile.confounder_missing` recusa um estudo exploratório sem confounders declarados. Uma
proposta que atravessa a revisão humana e só falha no compile consome o recurso mais escasso do
produto, que é a atenção de quem investiga.

O terceiro é que **o catálogo de rejeições ativas é grande e não está exposto a nenhum agente**. A
admissão recusa hoje `max_turns > 1`, budgets de token e custo, `checkpoint_policy`, progress policy,
mais de um stage de evaluation, adjudicação humana verificada, bounded exploration e todo disclosure
diferente de `none`. Um copiloto que ignora essa lista propõe experimentos impossíveis com aparência
competente.

# Decisão

## Runtime nativo, sem framework de agentes

O loop do Lab Agent é escrito no repositório sobre `ProviderPort` e os extractors de resposta já
existentes. Nenhum framework de orquestração de agentes entra como dependência.

A razão não é preferência de estilo. As invariantes que este produto precisa provar — escopo imposto
no repository, budget verificado antes do efeito, recusa indistinguível de inexistência, rastro de
cada leitura — são exatamente as que um framework generaliza para longe. Uma invariante que só vale
se a biblioteca não mudar de comportamento não é verificável.

O padrão de laço é o mesmo do adapter do Subject, adotado como **forma** e não como import: enviar o
transcript limitado, servir as tool calls, ou aceitar a resposta terminal. Três decisões separadas.

## O executor da tool é a única fronteira

O scope efetivo entra em toda tool a partir da sessão validada. Argumento produzido pelo modelo nunca
o substitui, amplia ou reinterpreta. Um `project_id` presente nos argumentos de uma tool call é
tratado como erro do modelo, não como pedido.

Isto materializa a regra do contrato de escopo v1: o prompt nunca é a fronteira de isolamento. Uma
instrução de sistema descreve a fronteira para o modelo cooperar; ela não a implementa.

## Verificação antes do efeito, em ordem fixa

Toda tool call atravessa a mesma sequência, e cada etapa recusa antes de a seguinte rodar:

1. a tool existe no catálogo efetivo daquela sessão;
2. o budget de tool calls do turno não está esgotado;
3. os argumentos casam exatamente com o schema declarado;
4. as refs resolvem dentro do scope da sessão;
5. a classification é legível sem grant.

A ordem é normativa. Verificar budget depois de executar registraria um efeito que o contrato nega, e
validar ref antes de argumento produziria erro no campo errado.

## Recusa nomeada, indistinguível e instrutiva

Toda recusa do Lab Agent é um código estável na mesma família de contrato dos erros de triagem, com
tabelas totais de status HTTP e exit code. Nenhuma borda deduz causa por texto.

Duas propriedades são normativas e específicas deste agente:

**Alvo fora do scope é indistinguível de alvo inexistente.** Um Project irmão, um Study de outro
Workspace e um id que nunca existiu produzem o mesmo código e a mesma forma de payload. Confirmar
existência por diferença de erro é exfiltração de metadata.

**A recusa devolvida ao modelo carrega remediação acionável.** O modelo é um consumidor da mensagem
de erro, não só o humano. Uma recusa que apenas nega convida à repetição; uma recusa que nomeia a
próxima ação válida encerra a tentativa. Isso é o que impede laço de tool call sem introduzir
heurística de detecção de laço.

## Repetição é terminal, não é tentativa infinita

Duas tool calls idênticas — mesma tool, mesmos argumentos, mesmo resultado de recusa — dentro do
mesmo turno encerram o turno por budget, com terminal observável. O produto não tenta adivinhar
intenção nem reescrever o pedido do modelo.

Recusa repetida indica prompt insuficiente ou catálogo mal descrito. Ambos são defeitos do produto,
corrigidos na composição de instruções e no catálogo, não em tolerância de runtime.

## Proposta é validada antes de ser apresentada

O Lab Agent não apresenta draft que ele não validou. A validação usa o mesmo parser do domínio que a
superfície pública usa, é pura e não persiste nada. Um draft que não sobrevive à validação volta ao
modelo como recusa nomeada, com o campo culpado.

Isto é o que torna o copiloto útil em vez de conversacional: a proposta que chega ao humano já
satisfaz as invariantes que o produto sabe verificar sozinho.

## O Lab Agent explica rejeições, nunca as provoca

Ler uma admissão existente e explicar seu código exato é leitura autorizada. Solicitar uma admissão
nova não é: `AdmissionRecord` é record persistido, e produzir efeito persistido para descobrir uma
resposta transforma diagnóstico em escrita.

Quando o humano quer saber se um RunSpec seria admitido, o caminho é o humano pedir a admissão pela
superfície pública. O agente explica o resultado.

## Instruções de sistema são compostas, e capabilities são derivadas

A instrução de sistema é montada por composição: uma base invariante idêntica em toda sessão, mais
exatamente um bloco de escopo, mais um bloco de capabilities.

O bloco de capabilities é **derivado do catálogo de tools efetivo daquela sessão**, não redigido à
mão. Prompt escrito à mão e catálogo executável divergem, e a divergência ensina o modelo a pedir o
que não existe.

A base invariante nunca é sobrescrita por bloco de escopo. Um bloco de escopo estreita o que o agente
pode fazer; nenhum bloco pode conceder autoridade, ampliar leitura ou relaxar uma proibição do
ADR 0018.

## Raciocínio sobre dados é agregação tipada, não execução

O Lab Agent não executa código. Ele pede agregação declarativa — métrica, agrupamento, janela — e o
servidor computa determinísticamente e devolve o vetor com o tamanho de amostra.

Um interpretador embutido daria ao Control Plane uma superfície de execução que o produto não modela,
não isola e não audita, para resolver um problema que uma tool tipada resolve. E preserva a
invariante que importa: o agente nunca produz um número por conta própria para depois apresentá-lo
como fato. Todo número vem do repository, com proveniência e amostra.

# Alternativas

**Framework de agentes de terceiros.** Rejeitado. Move para fora do repositório exatamente as
fronteiras que este produto precisa provar, e torna cada invariante dependente do comportamento não
versionado de uma biblioteca.

**Reusar `ResponsesReadAgentAdapter`.** Rejeitado. Seus quatro acoplamentos ao Execution Plane
(`SubjectEnvelope`, sink do ledger, budget do envelope, capability única) tornariam a reutilização uma
violação do ADR 0018, não uma economia.

**Escopo imposto por instrução de sistema.** Rejeitado pelo ADR 0021 e reafirmado aqui: uma ref
inventada ou uma tool mal chamada atravessaria a fronteira.

**Detecção heurística de laço.** Rejeitada. Contar similaridade de tentativas cria um limite que
ninguém pode declarar. Recusa determinística com remediação, mais terminal por repetição exata,
produz o mesmo efeito com regra legível.

**Interpretador Python confinado para análise.** Rejeitado nesta decisão. Superfície de execução no
Control Plane exigiria modelo de isolamento, policy e auditoria próprios; agregação tipada entrega o
caso de uso real sem nenhum deles. Um ADR sucessor pode revisitar se aparecer um caso que agregação
declarativa não expresse.

**Três instruções de sistema independentes por tipo de sessão.** Rejeitado. Uma invariante corrigida
em duas das três é um defeito silencioso; composição com base compartilhada torna isso impossível.

**Permitir que o agente chame `admit` para ler a rejeição.** Rejeitado. Cria record persistido para
obter informação, o que confunde diagnóstico com escrita.

# Consequências

O Lab Agent ganha runtime executável sem framework, e cada invariante do ADR 0018 passa a ter um
ponto de imposição nomeado: catálogo, budget, schema, scope, classification.

A superfície de teste adversarial cresce e é o preço declarado do escopo amplo. Todo caminho novo
precisa provar que não produziu autoridade, não vazou entre Projects, não escreveu no ledger e não
apresentou draft como fato.

O storage de chat atual não satisfaz este ADR. `ChatSessionRow` mantém `scope_type` e `scope_id`
anuláveis, sem enum, sem chave estrangeira e sem validação de pertencimento; `create_chat_session`
aceita os dois como texto livre. A listagem de sessões não filtra por Workspace. Migrar para o shape
tipado é pré-requisito do runtime, não trabalho posterior.

Memória operacional continua fora deste ADR. Duas obrigações permanecem para não fechar a porta: o
catálogo de tools aceita capability nova sem mudar assinatura, e todo draft declara `informed_by`
desde a primeira versão, ainda que vazio.

O provider default do ADR 0008 é reusado sem alteração. A presença do provider no Control Plane não
promove nenhuma capability do Subject e não altera o que a admissão aceita.
