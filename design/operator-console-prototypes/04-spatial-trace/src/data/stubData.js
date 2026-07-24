export const DEMO_NOTICE =
  "Demonstração local com dados stub. Nenhum registro nesta interface é evidência canônica.";

export const projectsSeed = [
  {
    id: "stub-project-retrieval-quality",
    name: "Retrieval Quality",
    description: "Avalia se respostas citam material suficiente e autorizado.",
    study: "Respostas com fontes insuficientes",
    currentStage: "admission",
    nextAction: "Corrigir o limite de interações da variante direct-answer",
    tone: "active",
    recordProfile: "retrieval-quality",
  },
  {
    id: "stub-project-context-drift",
    name: "Context Drift Review",
    description: "Compara como instruções persistem depois de compactações simuladas.",
    study: "Deriva após compactação",
    currentStage: "revision",
    nextAction: "Revisar o draft local antes de compilar",
    tone: "quiet",
    recordProfile: null,
  },
  {
    id: "stub-project-tool-permission",
    name: "Tool Permission Audit",
    description: "Inspeciona pedidos de ferramenta sem conceder autoridade humana.",
    study: "Fronteiras de ferramentas locais",
    currentStage: "evidence",
    nextAction: "Inspecionar referências do bundle stub",
    tone: "terminal",
    recordProfile: null,
  },
];

export const study = {
  projectId: "stub-project-retrieval-quality",
  recordProfile: "retrieval-quality",
  id: "stub-study-source-grounding",
  name: "Respostas com fontes insuficientes",
  revision: {
    id: "stub-revision-07",
    label: "Revisão local 07",
    status: "compilada",
    updatedAt: "23 jul 2026, 09:40 PYT",
  },
  scenario: "source-grounding-check",
  repetitions: 1,
  run: {
    id: "stub-run-evidence-first",
    variant: "evidence-first",
  },
  variants: [
    {
      id: "stub-variant-direct-answer",
      name: "direct-answer",
      intent: "Responder diretamente com o contexto permitido.",
      runSpec: {
        id: "stub-runspec-direct-01",
        maxTurns: 3,
        captureMode: "text",
      },
      admission: {
        id: "stub-admission-direct-rejected",
        decision: "rejected",
        issue: "max_turns incompatível",
        requested: "3 interações",
        supported: "1 interação",
      },
    },
    {
      id: "stub-variant-evidence-first",
      name: "evidence-first",
      intent: "Ler um trecho local autorizado antes de responder.",
      runSpec: {
        id: "stub-runspec-evidence-01",
        maxTurns: 1,
        captureMode: "text",
      },
      admission: {
        id: "stub-admission-evidence-admitted",
        decision: "admitted",
        issue: null,
        requested: "1 interação",
        supported: "1 interação",
      },
    },
  ],
};

export const workflowStages = [
  { id: "intent", label: "Intento", route: "/projects", short: "Escopo do Project" },
  { id: "revision", label: "StudyRevision", route: "/study", short: "Draft versionado" },
  { id: "runspec", label: "RunSpecs", route: "/study", short: "2 specs compilados" },
  { id: "admission", label: "Admissions", route: "/study", short: "1 admitido, 1 rejeitado" },
  { id: "run", label: "Runs", route: "/runs", short: "Execução stub local" },
  { id: "evaluation", label: "Avaliações", route: "/runs", short: "Registros append-only" },
  { id: "evidence", label: "Evidência", route: "/runs", short: "Bundle references-only" },
];

export const comparisonStub = [
  {
    variant: "direct-answer",
    disposition: "sem Run",
    observation: "AdmissionRecord rejeitado pelo limite de interações.",
    geometry: "outline",
  },
  {
    variant: "evidence-first",
    disposition: "terminal stub",
    observation: "EvaluationRecord local aponta presença de referência autorizada.",
    geometry: "filled",
  },
];

export const authorizedExcerpt =
  "StudyRevision: respostas precisam distinguir afirmação, referência e limite de acesso.";

export const runPhaseOrder = [
  "queued",
  "preparing",
  "running",
  "evaluating",
  "completed",
];

export const runPhaseLabels = {
  idle: "Pronta",
  queued: "Na fila",
  preparing: "Preparando",
  running: "Executando",
  evaluating: "Avaliando",
  completed: "Terminal",
  failed: "Falhou",
};

export function eventsForPhase(phase) {
  const base = [
    {
      type: "run.queued",
      label: "Run admitida entrou na fila stub",
      kind: "lifecycle",
    },
  ];

  if (phase === "queued") return base;

  base.push({
    type: "attempt.prepared",
    label: "Job e attempt locais foram preparados",
    kind: "operation",
  });
  if (phase === "preparing") return base;

  base.push(
    {
      type: "subject.invoked",
      label: "Subject stub recebeu objective e context permitidos",
      kind: "subject",
    },
    {
      type: "tool.called",
      label: "read_text solicitado no harness demonstrativo",
      kind: "tool",
    },
    {
      type: "tool.completed",
      label: "Trecho local autorizado retornado",
      kind: "tool",
    },
    {
      type: "subject.responded",
      label: "Resposta textual stub capturada",
      kind: "subject",
    },
  );
  if (phase === "running") return base;

  base.push({
    type: "evaluation.completed",
    label: "EvaluationRecord stub anexado",
    kind: "evaluation",
  });
  if (phase === "evaluating") return base;

  base.push({
    type: phase === "failed" ? "run.failed" : "run.completed",
    label:
      phase === "failed"
        ? "Falha local encerrada sem expor exceção sensível"
        : "Run stub alcançou estado terminal",
    kind: "terminal",
  });
  return base;
}
