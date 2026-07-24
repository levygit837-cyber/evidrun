export const ROUTES = [
  { path: "/", label: "Lab", shortLabel: "Lab" },
  { path: "/projects", label: "Projects", shortLabel: "Projects" },
  { path: "/study", label: "Study", shortLabel: "Study" },
  { path: "/runs", label: "Runs", shortLabel: "Runs" },
];

export const PROJECTS = [
  {
    id: "project-release-integrity-stub",
    name: "Release Integrity",
    intent: "Investigar regressões de deploy sem misturar hipótese, execução e evidência.",
    study: "Diagnóstico de regressões após deploy",
    linkedStudyId: "study:stub-release-integrity",
    workspace: "Workspace local não vinculado",
  },
  {
    id: "project-context-drift-stub",
    name: "Context Drift",
    intent: "Comparar como variantes preservam contexto autorizado ao longo de uma tarefa.",
    study: "Nenhuma Study vinculada",
    linkedStudyId: null,
    workspace: "Integration pending",
  },
  {
    id: "project-provider-gate-stub",
    name: "Provider Gate",
    intent: "Validar capabilities antes de admitir uma RunSpec em ambiente local.",
    study: "Nenhuma Study vinculada",
    linkedStudyId: null,
    workspace: "Integration pending",
  },
];

export const PROJECT_STAGES = [
  {
    id: "intent",
    label: "Intenção",
    description: "Delimita o problema e o escopo lógico do Project.",
    record: "Project draft local",
  },
  {
    id: "revision",
    label: "Revisão",
    description: "Uma StudyRevision registra alterações sem sobrescrever a anterior.",
    record: "StudyRevision stub-03",
  },
  {
    id: "admission",
    label: "Admission",
    description: "Cada RunSpec recebe seu próprio AdmissionRecord antes de qualquer Run.",
    record: "2 preflights locais",
  },
  {
    id: "run",
    label: "Run",
    description: "Run, job e attempt permanecem entidades separadas no stub.",
    record: "Nenhuma Run canônica",
  },
  {
    id: "evaluation",
    label: "Avaliação",
    description: "EvaluationRecords são append-only; este protótipo mostra somente exemplos locais.",
    record: "Evaluation draft",
  },
  {
    id: "comparison",
    label: "Comparação",
    description: "Variantes ficam em justaposição, sem transformar diferença visual em veredito.",
    record: "Comparison draft",
  },
];

export const RUN_TRACE_STAGES = [
  { id: "context", label: "Contexto" },
  { id: "subject", label: "Subject" },
  { id: "tool-read", label: "Leitura da tool" },
  { id: "evaluation", label: "Avaliação" },
  { id: "evidence", label: "Evidência" },
];

export const ACTIVITY_SEQUENCE = [
  {
    id: "prepare",
    type: "status",
    label: "Preparando contexto autorizado",
    summary: "Somente objective e context deste stub entram na preparação.",
    timestamp: "09:16:02",
  },
  {
    id: "read",
    type: "status",
    label: "Lendo input autorizado",
    summary: "Arquivo de demonstração local identificado pela allowlist.",
    timestamp: "09:16:03",
  },
  {
    id: "call",
    type: "tool-call",
    label: "Chamada de tool: read_text",
    summary: "Argumento permitido: deploy-summary.stub.txt",
    ref: "event:stub-run-ri-0723-a:tool-call-01",
    timestamp: "09:16:04",
  },
  {
    id: "result",
    type: "tool-result",
    label: "Resultado da tool capturado",
    summary: "Trecho autorizado: falha surgiu após a troca do bundle de release.",
    ref: "event:stub-run-ri-0723-a:tool-result-01",
    timestamp: "09:16:05",
  },
  {
    id: "response",
    type: "status",
    label: "Resposta capturada",
    summary: "Draft local disponível para revisão humana; nenhuma aceitação foi inferida.",
    ref: "event:stub-run-ri-0723-a:subject-responded-01",
    timestamp: "09:16:06",
  },
];

export const INITIAL_MESSAGES = [
  {
    id: "message-user-seed",
    role: "user",
    body: "O que mudou depois do deploy?",
    time: "09:16",
  },
  {
    id: "message-agent-seed",
    role: "agent",
    body: "O trecho autorizado aponta para uma mudança no bundle de release. Isto é um draft do Lab Agent, não uma decisão aceita.",
    time: "09:16",
  },
];

export const STUDY_REVISIONS = [
  {
    id: "study-revision-stub-03",
    label: "Revisão 03",
    status: "draft",
    objective: "Comparar duas estratégias de leitura dos logs autorizados depois do deploy.",
    scenario: "deployment-log-trace",
    repetitions: 1,
    runSpecs: [
      {
        id: "runspec-summary-first-stub-03",
        variant: "summary-first",
        admission: "rejected",
        reason: "Disclosure pre_run não é executável pelo runner ativo. Crie uma revisão com disclosure none.",
      },
      {
        id: "runspec-evidence-first-stub-03",
        variant: "evidence-first",
        admission: "admitted",
        reason: "Capabilities obrigatórias representadas e disponíveis neste stub.",
      },
    ],
  },
  {
    id: "study-revision-stub-02",
    label: "Revisão 02",
    status: "superseded",
    objective: "Ler o resumo do deploy em uma única variante.",
    scenario: "deployment-log-trace",
    repetitions: 1,
    runSpecs: [
      {
        id: "runspec-summary-first-stub-02",
        variant: "summary-first",
        admission: "rejected",
        reason: "Inventário do agente não declara a capture mode exigida.",
      },
      {
        id: "runspec-evidence-first-stub-02",
        variant: "evidence-first",
        admission: "rejected",
        reason: "Inventário do agente não declara a capture mode exigida.",
      },
    ],
  },
];

export const CORRECTED_REVISION = {
  id: "study-revision-stub-04",
  label: "Revisão 04",
  status: "draft local",
  objective: "Comparar duas estratégias com disclosure none e input local autorizado.",
  scenario: "deployment-log-trace",
  repetitions: 1,
  runSpecs: [
    {
      id: "runspec-summary-first-stub-04",
      variant: "summary-first",
      admission: "admitted",
      reason: "AdmissionRecord local admitiu o RunSpec exato com disclosure none.",
    },
    {
      id: "runspec-evidence-first-stub-04",
      variant: "evidence-first",
      admission: "admitted",
      reason: "AdmissionRecord local admitiu o RunSpec exato com disclosure none.",
    },
  ],
};

export const RUN_PHASES = [
  { id: "queued", label: "Queued", event: "run.queued" },
  { id: "preparing", label: "Preparando", event: "subject.invoked" },
  { id: "running", label: "Executando", event: "subject.responded" },
  { id: "evaluating", label: "Avaliando", event: "evaluation.recorded" },
  { id: "terminal", label: "Terminal", event: "run.completed" },
];

export const RUN_VARIANTS = [
  {
    id: "summary-first",
    title: "summary-first",
    disposition: "Draft capturado",
    detail: "Começa pelo resumo autorizado e preserva as refs do evento.",
  },
  {
    id: "evidence-first",
    title: "evidence-first",
    disposition: "Draft capturado",
    detail: "Começa pelo trecho autorizado e produz um resumo depois.",
  },
];

export const STUB_DATE = "23 jul 2026";
export const STUB_TIMEZONE = "America/Asuncion";
