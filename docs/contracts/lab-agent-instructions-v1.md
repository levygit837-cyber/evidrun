---
id: contract-lab-agent-instructions-v1
type: contract
title: Composição das instruções de sistema do Lab Agent v1
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-08-02
updated_at: 2026-08-02
applies_to: schema/lab-agent-instructions@1
sources:
  - docs/adr/0024-lab-agent-native-tool-runtime.md
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/contracts/lab-agent-tools-v1.md
  - docs/contracts/lab-agent-loop-v1.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Composição das instruções de sistema do Lab Agent v1

A instrução de sistema do Lab Agent é montada por composição determinística, não escrita como um texto
por tipo de sessão. Este contrato declara as seções, sua ordem, quais são obrigatórias e quais são
derivadas de fonte executável. Está aceito e ainda não possui runtime.

A instrução **descreve** a fronteira para o modelo cooperar; ela nunca a **implementa**. Todo limite
citado aqui é imposto no executor de tool, conforme o [loop v1](lab-agent-loop-v1.md). Um modelo que
ignore integralmente estas instruções não consegue atravessar nenhuma fronteira.

## Estrutura

O documento final é a concatenação ordenada de três camadas:

| Camada | Quantidade | Origem |
| --- | --- | --- |
| base invariante | exatamente 1 | autorada, idêntica em toda sessão |
| bloco de escopo | exatamente 1 | autorada, selecionada pela forma de sessão |
| bloco de capabilities | exatamente 1 | derivada do catálogo efetivo |

Três instruções independentes por tipo de sessão foram rejeitadas no ADR 0024: uma invariante corrigida
em duas das três é um defeito silencioso. A base compartilhada torna isso impossível.

Um bloco de escopo apenas **estreita**. Ele não concede autoridade, não amplia leitura e não relaxa
proibição da base. A composição é verificável: nenhuma linha de bloco de escopo pode contradizer a
base, e o teste de composição compara as duas.

## Seções obrigatórias da base

| Ordem | Seção | Conteúdo |
| --- | --- | --- |
| 1 | Identidade | quem o agente é e qual é seu papel no laboratório |
| 2 | Fronteira de autoridade | o que ele nunca faz, com a distinção autoridade/capacidade |
| 3 | Vocabulário | termos canônicos e sinônimos proibidos |
| 4 | Regras de tool call | schema exato, verificação antes do efeito, o que fazer ao ser recusado |
| 5 | Regras de evidência | draft não é fato, número exige amostra, citação exige ref |
| 6 | Forma de resposta | como responder, quando propor, quando perguntar |

Nenhuma seção é opcional. A ordem é normativa porque identidade e fronteira precisam preceder qualquer
instrução operacional: um modelo que leia as regras de tool antes da fronteira de autoridade aprende a
mecânica antes do limite.

### Identidade

Declara o agente como copiloto do laboratório, com escopo funcional amplo. Declara explicitamente que
seu limite é de autoridade e não de capacidade, porque essa foi a confusão que o ADR 0018 corrigiu e
uma instrução ambígua a reintroduz.

### Fronteira de autoridade

Enumera o que nenhum caminho produz: decisão de revision, attestation, human review, adjudicação,
grant, efeito externo, escrita no event ledger, mensagem ao Subject, draft apresentado como fato.

Declara o caminho substituto: quando uma ação exige autoridade humana, o agente registra pedido de
aprovação. Uma proibição sem alternativa produz um agente que tenta contornar; com alternativa, produz
um agente que encaminha.

Declara a assimetria de `hidden`: hidden graders e a hipótese do laboratório são invisíveis ao Subject
por desenho, e visíveis ao Lab Agent dentro do que o humano já vê. Sem isso o modelo recusa ajudar a
construir o que é sua função construir.

### Vocabulário

Os termos canônicos vêm de `CONTEXT.md`. A seção declara os sinônimos proibidos porque terminologia
divergente numa proposta produz documento que não compila: `Study` não é "experiment", `Goal` não é
"prompt", `RunSpec` não é "config".

### Regras de tool call

Declara que o schema é estrito e o conjunto de chaves é comparado por igualdade exata. Declara que
scope, sessão e ator nunca são argumentos. Declara a ordem de verificação, para que o modelo entenda
por que uma chamada foi recusada antes de executar.

Declara o comportamento ao ser recusado, e esta é a regra que mais evita desperdício: **ler a
remediação e seguir a ação nomeada, nunca repetir a mesma chamada**. Repetição exata encerra o turno
por `budget.refusal_repeated`.

### Regras de evidência

Declara três distinções que o produto vende:

- **draft não é fato**: toda proposta é apresentada como proposta, com o contrato exato que seria
  registrado;
- **número exige amostra**: valor agregado sem `sample_size` não é resultado, e o agente não computa
  número por conta própria;
- **afirmação sobre execução exige ref**: `run:`, `event:` ou `artifact:`; sem ref, é hipótese e é
  declarada como hipótese.

### Forma de resposta

Declara que perguntar é preferível a assumir quando falta a variável primária, a comparação ou o
critério de sucesso. Declara que a resposta precede a justificativa. Declara que limitação conhecida é
dita, não omitida.

## Blocos de escopo

| Forma | O bloco declara |
| --- | --- |
| General chat | navegação do Workspace; leitura de conteúdo e proposta não existem aqui; caminho para entrar numa Project chat |
| Project chat | trabalho completo no Project exato; regras do Workspace pai visíveis; nenhum Project irmão |
| Focused chat | mesmo limite de Project chat, estreitado à entidade em foco; foco nunca amplia |

O bloco de General chat é o mais importante de redigir bem. Ele oferece exatamente duas tools, e um
modelo que não entenda isso passa o turno tentando ler conteúdo e colecionando recusas. O bloco declara
a limitação como **direção**, não como falta: navegar e escolher onde trabalhar é a tarefa daquele
escopo.

## Bloco de capabilities derivado

O bloco de capabilities é gerado do catálogo de tools efetivo daquela sessão e do catálogo de
capabilities do produto. Ele nunca é redigido à mão.

Contém três partes:

| Parte | Origem | Por quê |
| --- | --- | --- |
| tools oferecidas | catálogo efetivo da sessão | prompt e executor não podem divergir |
| capabilities admitidas | catálogo do produto | o que um experimento pode declarar |
| rejeições ativas com códigos | checks de admissão | o que a admissão recusa hoje |

A terceira parte é a que impede a falha mais custosa. A admissão recusa hoje `max_turns > 1`, budgets
de token e custo, `checkpoint_policy`, progress policy, mais de um stage de evaluation, adjudicação
humana verificada, bounded exploration e todo disclosure diferente de `none`. Um agente que ignore
essa lista propõe experimentos impossíveis com aparência competente, e o humano descobre no compile.

Derivação é a invariante: se a lista fosse autorada, ela envelheceria no primeiro patch que mudasse um
check, e a divergência ensinaria o modelo a pedir o que não existe.

## Raciocínio entre turnos

O agente não possui estado oculto entre turnos além do histórico da própria sessão. Não existe
scratchpad persistido, cadeia de pensamento armazenada nem memória implícita.

O que substitui isso é explícito e auditável:

| Necessidade | Mecanismo |
| --- | --- |
| verificar uma suposição sobre execução | ler Run, eventos, evaluation records |
| verificar uma suposição sobre número | `aggregate_metrics`, com amostra |
| verificar uma suposição sobre validade de proposta | `validate_draft`, antes de propor |
| verificar o que o produto suporta | `read_capability_catalog` |

A instrução declara isso como método: **antes de afirmar, verificar com a tool correspondente**. Uma
suposição que nenhuma tool pode verificar é declarada como suposição.

Isto é o que dá ao agente uma forma de pensar sobre um problema sem executar código. O raciocínio
acontece no laço, contra o repository, e cada passo deixa rastro. Um interpretador embutido daria a
mesma capacidade sem rastro e sem fronteira, e foi rejeitado no ADR 0024.

## Sanitização

A instrução composta nunca contém credencial, segredo, conteúdo `sensitive` ou `restricted`, conteúdo
de outro Project, mensagem de outra sessão, nem valor de variável de ambiente.

O digest da instrução composta é registrado por turno. Duas sessões com o mesmo scope e o mesmo
catálogo produzem o mesmo digest; trocar de Project produz outro documento e outro digest.

## Provas mínimas

- a composição contém exatamente uma base, um bloco de escopo e um bloco de capabilities;
- as seis seções obrigatórias da base estão presentes e na ordem declarada;
- nenhum bloco de escopo contradiz uma proibição da base;
- o bloco de General chat não anuncia tool que o catálogo não oferece naquela forma;
- o bloco de capabilities lista exatamente as tools do catálogo efetivo, sem divergência;
- o bloco de capabilities inclui as rejeições ativas com os códigos reais;
- a instrução composta não contém credencial nem conteúdo classificado;
- o digest é estável para mesmo scope e catálogo, e muda ao trocar de Project.
