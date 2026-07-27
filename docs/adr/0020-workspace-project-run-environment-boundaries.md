---
id: adr-0020
type: adr
title: Separar Workspace, Project e Run Environment
status: accepted
authority: normative
volatility: timeless
owner: product
created_at: 2026-07-27
updated_at: 2026-07-27
applies_to: control-plane-scopes-and-run-environment
sources:
  - docs/adr/0002-control-plane-and-execution-plane.md
  - docs/adr/0009-study-run-contract-composition.md
  - docs/contracts/agent-inventory-workspace-v1.md
  - docs/product/charter.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Contexto

O domínio usava “workspace” para duas coisas diferentes: a fronteira durável onde o usuário organiza
o laboratório e o ambiente descrito por `WorkspaceTemplateRevision` para executar uma Run. Também
não estava claro se Project era somente uma pasta de Runs, uma fronteira de contexto ou a identidade
de um Lab Agent. Essa sobrecarga torna fácil montar dados do laboratório no Subject, criar isolamento
apenas aparente ou fazer configurações mutáveis alterarem Runs sem entrar no RunSpec.

# Decisão

## Workspace pertence ao Control Plane

Workspace é a raiz durável de isolamento local. Ele contém Projects, regras do laboratório,
preferências e futuras configurações explícitas de sincronização. Criar um Workspace cria somente
essa fronteira de dados: não provisiona filesystem, container, processo, credencial nem ambiente de
execução.

O isolamento de Workspace é obrigatório em repositories e serviços. Ele não pode depender de uma
instrução de prompt, de um filtro aplicado somente na UI ou de confiança no modelo.

## Project é uma linha de investigação

Project é uma fronteira filha de Workspace para uma linha coerente de investigação. Ele organiza a
autoria e a proveniência de Studies, contracts e revisions, conversas, memória escopada e as Runs
derivadas de seus RunSpecs. Uma Run continua pertencendo a um RunSpec exato; sua relação com Project
é resolvida pela Study revision, não por um campo mutável adicionado depois.

Project não é diretório de filesystem, mount, ambiente de execução, ACL multiusuário nem instância
persistente de agente. “Project Room” pode ser a projeção de interface dessa fronteira, sem criar um
novo agregado de domínio.

Leitura ou reutilização entre Projects é negada por padrão. Uma capacidade futura de importar,
copiar ou comparar entre Projects precisa ser explícita, autorizada e preservar proveniência; ela não
nasce de uma consulta ampla do Lab Agent.

## Run Environment pertence ao Execution Plane

Run Environment é o ambiente efêmero admitido e materializado para uma única Run a partir de
configuração versionada. O schema público v1 mantém os nomes `WorkspaceTemplateRevision` e
`RunSpec.workspace` para não quebrar documentos, digests e bundles existentes, mas a linguagem de
produto e arquitetura usa **Run Environment** para esse conceito. “Workspace de execução” permanece
apenas como nome de compatibilidade do schema v1.

O Workspace do Control Plane nunca é montado automaticamente no Run Environment. Somente inputs e
capabilities declarados, resolvidos e admitidos podem alcançar o SubjectEnvelope.

Quando existir um contrato de policy de Workspace, a configuração efetiva será a interseção:

```text
Workspace policy ceiling
  ∩ Run Environment Template solicitado pelo RunSpec
  ∩ capabilities reais do runtime
  -> AdmissionRecord
  -> Run Environment efetivo
```

Até existir esse contrato e um adapter que aplique cada opção, não há toggle oculto de Workspace ou
Project que altere execução. Capacidade ausente, incompatível ou não verificável rejeita a admissão.

O preset seguro inicial para um adapter isolado é efêmero por Run, aceita somente inputs exatos do
Scenario, mounts read-only, nenhuma write zone, nenhum secret, efeitos externos negados, network
`denied` ou `provider_only` quando explicitamente admitida, snapshot desabilitado e cleanup
`discard`. Essa é uma decisão de arquitetura para adapters futuros, não uma alegação de que o runtime
`in_process` atual oferece sandbox forte. Enquanto não houver isolamento verificável, a UI e a API
devem descrevê-lo como `in_process`, não como sandbox seguro.

## Identidade por nome é escopada e não ambígua

O nome de Workspace é único no datastore local. O nome de Project é único somente dentro de seu
Workspace pai; Workspaces diferentes podem conter Projects de mesmo nome. Comparação de identidade
usa uma chave canônica derivada por Unicode NFKC, trim, colapso de whitespace e casefold, enquanto a
forma de exibição preserva capitalização e caracteres significativos.

Criação duplicada falha com conflito. Não existe `get-or-create`, reaproveitamento silencioso nem
renome automático durante migration. A garantia final é uma constraint do storage, não apenas uma
checagem anterior à escrita.

# Alternativas rejeitadas

- Usar Workspace também para o ambiente de uma Run: mistura dados duráveis do laboratório com bytes
  e capabilities entregues ao Subject.
- Tratar Project como pasta ou coleção passiva de Runs: perde a fronteira de autoria, proveniência,
  conversa e retrieval necessária ao produto.
- Criar um sandbox ao criar Workspace ou Project: provisiona recursos antes de existir RunSpec e
  AdmissionRecord e deixa configuração de execução fora do documento versionado.
- Tornar nomes de Project globalmente únicos: cria restrição sem benefício de isolamento e impede a
  mesma linha de investigação em Workspaces independentes.
- Guardar opções executáveis como preferências mutáveis e implícitas: duas Runs com o mesmo RunSpec
  poderiam receber ambientes diferentes sem evidência da mudança.

# Consequências

O Control Plane ganha uma hierarquia simples e estável: Workspace contém Projects; Project contém o
contexto de uma linha de investigação; Study/RunSpec continuam sendo a origem versionada das Runs. O
Execution Plane materializa um Run Environment somente depois de admissão.

A superfície pública de Workspace/Project precisa de normalização única, constraints, migration com
auditoria de colisão e erros tipados. A eventual implementação de sandbox precisa provar suas
capabilities na admissão; renomear `WorkspaceTemplateRevision` fica reservado a uma versão nova do
contrato, não a uma edição incompatível do v1.
