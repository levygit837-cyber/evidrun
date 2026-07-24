export const studyContext = {
  name: "Respostas com fontes insuficientes",
  scenario: "source-grounding-check",
  variants: ["direct-answer", "evidence-first"],
  repetitions: 1,
  date: "23 jul 2026",
  timezone: "America/Asuncion",
};

export const initialProjects = [
  {
    id: "project-stub-retrieval",
    name: "Retrieval Quality",
    intent: "Comparar respostas com e sem cobertura de fontes autorizadas.",
    study: studyContext.name,
    scenario: studyContext.scenario,
    hasRuntimeFixture: true,
    stage: "admission",
    nextAction: "Corrigir a revisão e recompilar os RunSpecs.",
  },
  {
    id: "project-stub-disclosure",
    name: "Disclosure Boundary",
    intent: "Verificar o limite de disclosure antes da execução.",
    study: "Disclosure pre-run controlado",
    scenario: "disclosure-boundary-review",
    hasRuntimeFixture: false,
    stage: "revision",
    nextAction: "Revisar o SubjectEnvelope compilado.",
  },
  {
    id: "project-stub-evidence",
    name: "Bundle Integrity",
    intent: "Inspecionar referências intencionais de um bundle local.",
    study: "Manifesto de evidência mínimo",
    scenario: "bundle-manifest-audit",
    hasRuntimeFixture: false,
    stage: "evaluation",
    nextAction: "Ler a avaliação anterior.",
  },
];

export const workflowStages = [
  { id: "intent", label: "Intent", description: "Escopo e objetivo do Project." },
  { id: "revision", label: "StudyRevision", description: "Draft versionado para compilação." },
  { id: "admission", label: "Admission", description: "Compatibilidade antes de qualquer Run." },
  { id: "run", label: "Run", description: "Execução criada somente após admissão." },
  { id: "evaluation", label: "Evaluation", description: "Leitura append-only da resposta." },
  { id: "comparison", label: "Comparison", description: "Variantes justapostas, sem ranking inventado." },
];

export const initialRevisions = [
  {
    id: "REV-STUB-002",
    label: "Revisão 2",
    objective: "Identificar respostas que não sustentam afirmações com fontes autorizadas.",
    sourceCoverage: false,
    compiled: true,
    admission: "rejected",
    isLocal: false,
  },
  {
    id: "REV-STUB-001",
    label: "Revisão 1",
    objective: "Comparar respostas diretas e orientadas por evidência.",
    sourceCoverage: true,
    compiled: true,
    admission: "admitted",
    isLocal: false,
  },
];

export const observableSequence = [
  {
    id: "context",
    kind: "progress",
    label: "Preparando contexto permitido",
    detail: "Resumo público da etapa",
  },
  {
    id: "authorized-input",
    kind: "progress",
    label: "Lendo entrada autorizada",
    detail: "Demonstração local",
  },
  {
    id: "tool-call",
    kind: "tool-call",
    label: "Chamada de ferramenta",
    detail: "read_text",
  },
  {
    id: "tool-result",
    kind: "tool-result",
    label: "Resultado capturado",
    detail: "Trecho local autorizado: cobertura de fontes ausente.",
  },
  {
    id: "response",
    kind: "response",
    label: "Resposta capturada",
    detail: "Draft local",
  },
];

export const runPhases = [
  { id: "queued", label: "Queued", detail: "Job local aguardando claim." },
  { id: "preparing", label: "Preparing", detail: "RunSpec exato e AdmissionRecord conferidos." },
  { id: "running", label: "Running", detail: "Uma interação determinística em execução." },
  { id: "evaluating", label: "Evaluating", detail: "EvaluationRecord local sendo anexado." },
  { id: "terminal", label: "Terminal", detail: "Lifecycle encerrado no stub." },
];
