---
id: contract-lab-agent-tools-v1
type: contract
title: Catálogo de tools do Lab Agent v1
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-08-02
updated_at: 2026-08-02
applies_to: schema/lab-agent-tools@1
sources:
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/adr/0024-lab-agent-native-tool-runtime.md
  - docs/contracts/lab-agent-scope-v1.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Catálogo de tools do Lab Agent v1

Este contrato declara quais tools existem, o que cada uma recebe e devolve, e em qual forma de sessão
cada uma é oferecida. Está aceito e ainda não possui runtime.

Sessões, envelope e enforcement de pertencimento pertencem ao
[escopo v1](lab-agent-scope-v1.md). Loop, budgets e terminais pertencem ao
[loop v1](lab-agent-loop-v1.md). Códigos de recusa pertencem aos
[erros v1](lab-agent-errors-v1.md).

## Princípios do catálogo

O catálogo é **fechado e derivado**. Fechado: uma tool que não está nesta tabela não é oferecida ao
modelo, e uma tool call cujo nome não está no catálogo efetivo é recusada sem execução. Derivado: o
conjunto oferecido é função da forma de sessão, não de configuração por chamada.

Toda tool declara schema estrito: `additionalProperties: false`, campos obrigatórios explícitos e
tetos numéricos declarados. O conjunto de chaves dos argumentos é comparado por igualdade exata, não
por presença dos obrigatórios. Chave desconhecida, chave ausente e tipo divergente são recusa, não
coerção.

Nenhuma tool recebe `workspace_id`, `project_id`, `scope`, `session_id` ou qualquer campo de ator,
autoridade ou classificação como argumento. Esses valores vêm da sessão validada. Declarar um deles
no schema seria oferecer ao modelo um controle que o contrato de escopo nega.

## Tools de leitura

| Tool | Argumentos | Devolve | Não devolve |
| --- | --- | --- | --- |
| `list_projects` | nenhum | `id`, `name`, `created_at` de cada Project do Workspace | contract, Run, evaluation, mensagem, memória |
| `read_contract_revision` | `revision_ref` | documento semântico da revision, `status`, digest | revision de outro Project, conteúdo sem classificação legível |
| `list_runs` | `limit`, `status` opcional | `run_id`, `run_spec_id`, `status`, terminal, timestamps | Run de outro Project |
| `read_run` | `run_id` | lifecycle, terminal cause, refs de spec e admissão | payload de evento bruto não autorizado |
| `read_run_events` | `run_id`, `after_sequence`, `limit` | eventos válidos da Run em ordem de sequência | evento de outra Run, payload classificado sem grant |
| `read_evaluation_records` | `run_id` | vetor de records, dimensões, `source_type` | record de outra Run |
| `read_comparison` | `comparison_id` | variável primária, validade, deltas, refs das Runs | Comparison de outro Project |
| `read_admission` | `admission_id` | decisão, código exato da rejeição, issues, requisitos ausentes | admissão de outro Project |
| `read_capability_catalog` | nenhum | capabilities admitidas **e** rejeições ativas com seus códigos | promessa de capability não implementada |
| `aggregate_metrics` | `metric`, `group_by`, `run_ids` | vetor agregado com `sample_size` por grupo | agregação entre Projects, valor sem amostra |

`read_capability_catalog` é obrigatória e devolve as duas metades. Omitir as rejeições ativas produz
um agente que propõe o impossível: a admissão recusa hoje `max_turns > 1`, budgets de token e custo,
`checkpoint_policy`, progress policy, mais de um stage de evaluation, adjudicação humana verificada,
bounded exploration e todo disclosure diferente de `none`.

`aggregate_metrics` é a única forma de o agente derivar número agregado. Ela existe porque o Lab Agent
não executa código: a agregação é declarativa, computada pelo servidor e devolvida com o tamanho de
amostra. Um resultado sem `sample_size` é inválido, não é resultado parcial.

## Tools de proposta

| Tool | Argumentos | Efeito | Autoridade |
| --- | --- | --- | --- |
| `validate_draft` | `contract_type`, `document` | nenhum; puro | nenhuma |
| `propose_draft` | `contract_type`, `document`, `informed_by` | registra revision `draft` | nenhuma |
| `request_human_approval` | `revision_ref`, `rationale` | registra pedido de aprovação | nenhuma |

`validate_draft` não persiste, não decide e não incrementa nenhuma sequência de revision. Ela usa o
mesmo parser de contrato que a superfície pública usa, portanto sua recusa é o mesmo código que o
humano veria. É pré-requisito de `propose_draft`: uma proposta que não sobrevive à validação não é
apresentada ao humano.

`propose_draft` herda `project_id` da sessão. O documento nunca declara decisão, aceitação,
attestation, authority ou `status` diferente de `draft`. O campo `informed_by` é obrigatório na
assinatura e pode ser vazio enquanto memória operacional não existir.

`request_human_approval` preserva scope e digest do draft e não preenche decisão. Ela não é uma
decisão adiada: é o registro de que o agente terminou sua parte.

## Tools que não existem por decisão explícita

| Tool ausente | Por quê |
| --- | --- |
| `admit_run_spec` | criaria `AdmissionRecord`, que é record persistido; o agente explica rejeições, não as provoca |
| `accept_revision`, `decide_revision` | é autoridade humana; nenhum caminho do Lab Agent alcança decisão |
| `append_event` | o Lab Agent nunca escreve no event ledger |
| `run_python`, `execute_code` | superfície de execução no Control Plane, sem modelo de isolamento, policy ou auditoria |
| `read_artifact_bytes` | `ArtifactRef` identifica conteúdo e não concede acesso; leitura classificada exige grant próprio |
| `enqueue_run`, `cancel_run` | efeito de execução; pertence ao humano pela superfície pública |
| `read_subject_envelope` | envelope do Subject é do Execution Plane e não é insumo de autoria |
| `search_all_projects` | não existe retrieval cross-Project; navegação usa `list_projects` |

Esta tabela é normativa. Acrescentar uma tool aqui exige ADR sucessor, não uma decisão de
implementação.

## Disponibilidade por forma de sessão

| Tool | General | Project | Focused |
| --- | --- | --- | --- |
| `list_projects` | sim | sim | sim |
| `read_capability_catalog` | sim | sim | sim |
| `read_contract_revision` | não | sim | sim, estreitada ao foco |
| `list_runs` | não | sim | sim, estreitada ao foco |
| `read_run`, `read_run_events` | não | sim | sim, estreitada ao foco |
| `read_evaluation_records` | não | sim | sim, estreitada ao foco |
| `read_comparison` | não | sim | sim, estreitada ao foco |
| `read_admission` | não | sim | sim, estreitada ao foco |
| `aggregate_metrics` | não | sim | sim, estreitada ao foco |
| `validate_draft` | não | sim | sim |
| `propose_draft` | não | sim | sim |
| `request_human_approval` | não | sim | sim |

General chat oferece exatamente duas tools. Isso é a materialização da regra do ADR 0021: navegação
do Workspace não é leitura implícita de todos os Projects. O agente em General chat pode ajudar a
escolher onde trabalhar e explicar o que o produto suporta; para ler conteúdo ou propor draft, o
humano entra numa Project chat.

Focused chat oferece o mesmo conjunto de Project chat. O foco **estreita** a leitura normal ao Study,
Run ou Comparison declarado; nunca amplia, e nunca alcança entidade de outro Project.

## Rastro de uso

Toda chamada registra sessão, scope efetivo, nome da tool, digest dos argumentos, refs solicitadas,
refs efetivamente devolvidas e resultado. O rastro é do Control Plane e vive fora do event ledger: o
ledger é a autoridade da Run e o Lab Agent não escreve nele.

Refs solicitadas e refs devolvidas são campos separados de propósito. A diferença entre os dois
conjuntos é a evidência de que o enforcement recusou algo, e é o que permite ao humano ver o que o
agente tentou ler.

## Provas mínimas

- tool fora do catálogo efetivo é recusada sem execução e sem revelar que existe em outro escopo;
- chave desconhecida, chave ausente e tipo divergente são recusados por igualdade exata de schema;
- `project_id` presente nos argumentos não sobrepõe o scope da sessão;
- General chat oferece exatamente `list_projects` e `read_capability_catalog`;
- `read_capability_catalog` inclui as rejeições ativas com os códigos reais da admissão;
- `aggregate_metrics` nunca devolve grupo sem `sample_size` e nunca cruza Projects;
- `validate_draft` não persiste nada e devolve o mesmo código que a superfície pública devolveria;
- `propose_draft` recusa documento que não passou por validação;
- draft registrado permanece sem decisão e herda o Project da sessão;
- `informed_by` é presente e vazio enquanto memória não existir;
- nenhuma tool alcança `decide_contract_revision`, `append_event` ou criação de `AdmissionRecord`;
- o rastro distingue refs solicitadas de refs devolvidas.
