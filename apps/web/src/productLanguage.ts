export interface ProductTerm {
  label: string;
  technicalName: string;
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
  },
  studyDesign: {
    label: "Study Design",
    technicalName: "Study",
  },
  studyVersion: {
    label: "Study Version",
    technicalName: "StudyRevision",
  },
  studyIntent: {
    label: "Study Purpose",
    technicalName: "StudyIntent",
  },
  goal: {
    label: "Agent Task",
    technicalName: "GoalRevision",
  },
  scenario: {
    label: "Scenario",
    technicalName: "ScenarioRevision",
  },
  variant: {
    label: "Variant",
    technicalName: "VariantSpec",
  },
  evaluationPlan: {
    label: "Evaluation Plan",
    technicalName: "EvaluationPlanRevision",
  },
  runSpec: {
    label: "Execution Plan",
    technicalName: "RunSpec",
  },
  admission: {
    label: "Readiness Check",
    technicalName: "AdmissionRecord",
  },
  run: {
    label: "Run",
    technicalName: "Run",
  },
  evaluationRecord: {
    label: "Recorded Evaluation",
    technicalName: "EvaluationRecord",
  },
  comparison: {
    label: "Comparison",
    technicalName: "Comparison",
  },
  evidenceBundle: {
    label: "Audit Evidence Bundle",
    technicalName: "Evidence Bundle audit",
  },
  subjectEnvelope: {
    label: "Subject Context",
    technicalName: "SubjectEnvelope",
  },
} as const satisfies Record<string, ProductTerm>;

export const studyPipelineSteps = [
  {
    id: 1,
    label: productTerms.studyDesign.label,
    technicalName: productTerms.studyDesign.technicalName,
  },
  {
    id: 2,
    label: `${productTerms.runSpec.label}s`,
    technicalName: productTerms.runSpec.technicalName,
  },
  {
    id: 3,
    label: productTerms.admission.label,
    technicalName: productTerms.admission.technicalName,
  },
  { id: 4, label: `${productTerms.run.label}s`, technicalName: productTerms.run.technicalName },
] as const;

export function auditTerm(term: ProductTerm): string {
  return term.label === term.technicalName
    ? term.label
    : `${term.label} (${term.technicalName})`;
}

export const admissionStateLabels = {
  admitted: "Ready",
  rejected: "Blocked",
  failed: "Check failed",
  unavailable: "Unavailable",
  stale: "Outdated",
} as const;

const runStatusLabels = {
  queued: "Queued",
  preparing: "Preparing",
  running: "Running",
  evaluating: "Evaluating",
  completed: "Completed",
  failed: "Failed",
  budget_exhausted: "Budget exhausted",
  cancelled: "Cancelled",
  guardrail_stopped: "Guardrail stopped",
} as const;

export function runStatusLabel(status: string): string {
  return Object.hasOwn(runStatusLabels, status)
    ? runStatusLabels[status as keyof typeof runStatusLabels]
    : status;
}

export const navigationAreas = {
  "/create": "Study Builder",
  "/laboratory": "Laboratory",
  "/observability": "Runs",
} as const;
