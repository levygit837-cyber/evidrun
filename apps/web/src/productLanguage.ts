export interface ProductTerm {
  label: string;
  technicalName: string;
  meaning: string;
}

/**
 * Product-facing names for the canonical v1 contracts.
 *
 * The technical name stays available for audit and support, but it is not the explanation. The
 * label tells a person what the object means in the laboratory workflow.
 */
export const productTerms = {
  study: {
    label: "Study",
    technicalName: "Study",
    meaning: "A investigação que reúne propósito, desenho e execuções relacionadas.",
  },
  studyIntent: {
    label: "Study Purpose",
    technicalName: "StudyIntent",
    meaning: "A pergunta, a hipótese e a decisão que a evidência poderá informar.",
  },
  goal: {
    label: "Agent Task",
    technicalName: "Goal",
    meaning: "O objetivo e os limites que chegam ao agente avaliado.",
  },
  scenario: {
    label: "Scenario",
    technicalName: "Scenario",
    meaning: "Os dados, as condições e as limitações de uma situação avaliada.",
  },
  variant: {
    label: "Variant",
    technicalName: "Variant",
    meaning: "Uma mudança controlada comparada com as demais variações do estudo.",
  },
  evaluationPlan: {
    label: "Evaluation Plan",
    technicalName: "EvaluationPlan",
    meaning: "Os critérios e as etapas usados para avaliar uma execução.",
  },
  runSpec: {
    label: "Execution Plan",
    technicalName: "RunSpec",
    meaning: "A configuração exata e imutável de uma execução antes que ela aconteça.",
  },
  admission: {
    label: "Readiness Check",
    technicalName: "AdmissionRecord",
    meaning: "A checagem técnica que confirma se um plano pode ser executado agora.",
  },
  run: {
    label: "Run",
    technicalName: "Run",
    meaning: "Uma tentativa factual realizada após o plano passar pela verificação técnica de prontidão.",
  },
  evaluationRecord: {
    label: "Recorded Evaluation",
    technicalName: "EvaluationRecord",
    meaning: "Uma avaliação imutável, ancorada na evidência de uma execução.",
  },
  comparison: {
    label: "Comparison",
    technicalName: "Comparison",
    meaning: "A leitura conjunta das execuções e de seus trade-offs.",
  },
  evidenceBundle: {
    label: "Evidence Bundle",
    technicalName: "Evidence Bundle",
    meaning: "O pacote verificável de registros, referências e digests preservados.",
  },
  subjectEnvelope: {
    label: "Subject Context",
    technicalName: "SubjectEnvelope",
    meaning: "A visão mínima e permitida entregue ao agente avaliado.",
  },
} as const satisfies Record<string, ProductTerm>;

export const studyPipelineSteps = [
  { id: 1, label: "Study Design", technicalName: "Study" },
  { id: 2, label: "Execution Plans", technicalName: "RunSpec" },
  { id: 3, label: "Readiness Check", technicalName: "AdmissionRecord" },
  { id: 4, label: "Runs", technicalName: "Run" },
] as const;

export const admissionStateLabels = {
  admitted: "Ready",
  rejected: "Blocked",
  failed: "Check failed",
  unavailable: "Unavailable",
  stale: "Outdated",
} as const;

export const runStatusLabels: Record<string, string> = {
  queued: "Queued",
  preparing: "Preparing",
  running: "Running",
  evaluating: "Evaluating",
  completed: "Completed",
  failed: "Failed",
  budget_exhausted: "Budget exhausted",
  cancelled: "Cancelled",
  guardrail_stopped: "Guardrail stopped",
};

export const navigationAreas = {
  "/create": "Study Builder",
  "/laboratory": "Laboratory",
  "/observability": "Runs",
} as const;
