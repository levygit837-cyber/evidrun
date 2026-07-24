export const routeItems = [
  { id: "lab", label: "Lab", description: "Rascunhar com contexto autorizado" },
  { id: "projects", label: "Projects", description: "Delimitar escopo e fluxo" },
  { id: "study", label: "Study", description: "Compilar e admitir RunSpecs" },
  { id: "runs", label: "Runs", description: "Executar stub e ler evidência" },
];

export const initialProjects = [
  {
    id: "project-release-integrity",
    name: "Release Integrity",
    summary: "Investiga regressões observáveis após deploy sem ampliar o envelope autorizado.",
    workspace: "workspace-local-evidrun",
    currentStage: "admission",
  },
  {
    id: "project-provider-boundary",
    name: "Provider Boundary",
    summary: "Valida a fronteira local de provider com registros reproduzíveis e sem credenciais persistidas.",
    workspace: "workspace-local-evidrun",
    currentStage: "study",
  },
  {
    id: "project-bundle-inspection",
    name: "Bundle Inspection",
    summary: "Examina referências intencionais do bundle sem prometer portabilidade ou replay.",
    workspace: "workspace-local-audit",
    currentStage: "evidence",
  },
];

export const workflowStages = [
  {
    id: "scope",
    label: "Project scope",
    short: "Escopo delimitado",
    status: "complete",
    happened: "Project Release Integrity foi associado ao workspace local.",
    blocked: "Nada bloqueia a edição do Study draft.",
    next: "Revisar o objetivo e preparar uma StudyRevision.",
  },
  {
    id: "study",
    label: "Study draft",
    short: "Revisão draft-003",
    status: "complete",
    happened: "A matriz foi definida com um cenário e duas variantes.",
    blocked: "A revisão ainda é um draft mutável.",
    next: "Compilar RunSpecs imutáveis para preflight.",
  },
  {
    id: "compile",
    label: "Compile",
    short: "2 RunSpecs",
    status: "complete",
    happened: "A StudyRevision gerou dois RunSpecs distintos.",
    blocked: "Nenhuma Run existe nesta etapa.",
    next: "Avaliar capabilities e disclosure na Admission.",
  },
  {
    id: "admission",
    label: "Admission",
    short: "Posição atual",
    status: "current",
    happened: "O preflight local está pronto para os dois RunSpecs.",
    blocked: "Uma variante pode ser rejeitada quando uma capability obrigatória falta.",
    next: "Admitir o RunSpec exato ou corrigir o draft e recompilar.",
  },
  {
    id: "queue",
    label: "Queue",
    short: "Ainda não criada",
    status: "pending",
    happened: "Nenhum job foi criado por esta demonstração.",
    blocked: "AdmissionRecord admitido é obrigatório antes da Run.",
    next: "Enfileirar apenas RunSpecs admitidos.",
  },
  {
    id: "evidence",
    label: "Evidence",
    short: "Após terminal",
    status: "pending",
    happened: "Ainda não há evento terminal nesta trilha.",
    blocked: "Evidência depende de uma Run válida e de records canônicos.",
    next: "Executar, avaliar e verificar o bundle de referências.",
  },
];

export const studyRevisions = [
  {
    id: "studyrev-release-integrity-003",
    label: "draft-003",
    state: "draft",
    objective: "Diagnosticar uma possível regressão após deploy usando apenas o log autorizado.",
    note: "Revisão editável. Ainda não é um RunSpec.",
  },
  {
    id: "studyrev-release-integrity-002",
    label: "draft-002",
    state: "superseded",
    objective: "Comparar duas estratégias de leitura do mesmo contexto autorizado.",
    note: "Mantida para inspeção local. Não será recompilada nesta sessão.",
  },
];

export const runSpecs = [
  {
    id: "runspec-deployment-log-summary-001",
    variant: "summary-first",
    repetition: 1,
    model: "deepseek-v4-flash",
    capture: "text",
  },
  {
    id: "runspec-deployment-log-evidence-001",
    variant: "evidence-first",
    repetition: 1,
    model: "deepseek-v4-flash",
    capture: "text",
  },
];

export const labSequence = [
  "Preparando contexto",
  "Lendo input autorizado",
  "Tool call: read_text",
  "Tool result recebido",
  "Resposta capturada",
];

export const authorizedExcerpt = [
  "23:14:09 deploy release-2026.07.23 iniciou",
  "23:16:42 endpoint /health retornou latência acima do baseline",
  "23:18:03 rollback candidate registrado pelo stub local",
];

export const runEventPhases = [
  { id: "event-run-queued-001", label: "Queued", record: "AdmissionRecord admitido" },
  { id: "event-run-preparing-001", label: "Preparing", record: "RunRecord criado" },
  { id: "event-subject-invoked-001", label: "Running", record: "SubjectEnvelope digest registrado" },
  { id: "event-evaluation-recorded-001", label: "Evaluating", record: "EvaluationRecord anexado" },
  { id: "event-run-completed-001", label: "Terminal", record: "RunRecord terminal completed" },
];

export const evidenceRefs = [
  { id: "artifact-subject-response-001", kind: "subject_response", digest: "sha256:8f2c...6a10" },
  { id: "artifact-evaluation-summary-001", kind: "evaluation_summary", digest: "sha256:24ae...10dc" },
  { id: "artifact-event-ledger-001", kind: "event_ledger", digest: "sha256:c830...19b2" },
];

export const comparisonRows = [
  { label: "Context order", left: "Resumo antes do log", right: "Log antes do resumo" },
  { label: "Capture mode", left: "text", right: "text" },
  { label: "Terminal", left: "completed", right: "completed" },
  { label: "Interpretação", left: "Exige leitura humana", right: "Exige leitura humana" },
];
