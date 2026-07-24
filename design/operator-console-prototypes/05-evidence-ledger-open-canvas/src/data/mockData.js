export const PROJECTS = [
  {
    id: "crl",
    name: "Context Reliability Lab",
    description: "Escopo lógico para avaliações de preservação de contexto.",
    status: "Study ativa",
  },
  {
    id: "handoff",
    name: "Handoff Trace Study",
    description: "Demonstração local para continuidade entre agentes.",
    status: "Draft local",
  },
  {
    id: "citation",
    name: "Citation Boundary Review",
    description: "Escopo de exemplo para referências e disclosure.",
    status: "Sem Runs",
  },
];

export const WORKFLOW_NODES = [
  {
    id: "revision",
    type: "StudyRevision",
    label: "Revisão aceita",
    secondary: "crl-ctx-002-context-policy · rev 1",
    status: "accepted",
    detail: "Versão authored e aceita pelo import dedicado da fixture canônica.",
    ref: "artifact:study-revision-crl-ctx-002-r1",
  },
  {
    id: "spec-head",
    type: "RunSpec",
    label: "head-truncation",
    secondary: "rspec_019f9100...3947c",
    status: "compiled",
    detail: "RunSpec compilado a partir da revisão exata para uma repetição.",
    ref: "artifact:runspec-head-truncation",
  },
  {
    id: "admission-head",
    type: "AdmissionRecord",
    label: "Preflight admitido",
    secondary: "adm_019f9100...77c547",
    status: "admitted",
    detail: "Decisão pré-run para o RunSpec head-truncation exato.",
    ref: "artifact:admission-head-truncation",
  },
  {
    id: "run-head",
    type: "Run",
    label: "Run concluída",
    secondary: "run_019f9100...96ac9",
    status: "completed",
    detail: "A Run existe somente após a Admission admitida. Job e attempt permanecem separados.",
    ref: "run:run_019f9100...96ac9",
  },
  {
    id: "eval-head",
    type: "EvaluationRecord",
    label: "Score 0.0",
    secondary: "eval_019f9100...61b0",
    status: "recorded",
    detail: "Avaliação registrada para head-truncation na fixture CRL-CTX-002.",
    ref: "artifact:evaluation-head-truncation",
  },
  {
    id: "spec-tail",
    type: "RunSpec",
    label: "tail-preservation",
    secondary: "rspec_019f9100...09fd4",
    status: "compiled",
    detail: "RunSpec compilado a partir da mesma revisão, com variante distinta.",
    ref: "artifact:runspec-tail-preservation",
  },
  {
    id: "admission-tail",
    type: "AdmissionRecord",
    label: "Preflight admitido",
    secondary: "adm_019f9100...160304",
    status: "admitted",
    detail: "Decisão pré-run para o RunSpec tail-preservation exato.",
    ref: "artifact:admission-tail-preservation",
  },
  {
    id: "run-tail",
    type: "Run",
    label: "Run concluída",
    secondary: "run_019f9100...ae5e5",
    status: "completed",
    detail: "Execução capturada pela fixture. Não implica replay nem portabilidade.",
    ref: "run:run_019f9100...ae5e5",
  },
  {
    id: "eval-tail",
    type: "EvaluationRecord",
    label: "Score 1.0",
    secondary: "eval_019f9100...cc01f5",
    status: "recorded",
    detail: "Avaliação registrada para tail-preservation na fixture CRL-CTX-002.",
    ref: "artifact:evaluation-tail-preservation",
  },
  {
    id: "comparison",
    type: "Comparison",
    label: "Delta 1.0",
    secondary: "cmp_019f9100...e0996",
    status: "recorded",
    detail: "Comparação controlada convergindo as duas EvaluationRecords.",
    ref: "artifact:comparison-crl-ctx-002",
  },
];

export const REVISIONS = [
  {
    id: "rev-004",
    label: "rev-004 · fixture",
    state: "accepted fixture",
    objective: "Avaliar se uma política de preservação mantém a causa-raiz em logs longos.",
  },
  {
    id: "rev-003",
    label: "rev-003 · anterior",
    state: "superseded",
    objective: "Comparar truncamento de logs sob um único cenário determinístico.",
  },
];

export const PREFLIGHTS = {
  "head-truncation": {
    decision: "rejected",
    issue: "unsupported_execution_contract",
    requested: "max_turns=3",
    supported: "max_turns=1",
    explanation: "O runner ativo admite uma única interação. Este RunSpec solicita três turnos.",
    admissionId: "adm_preview_head_019f",
  },
  "tail-preservation": {
    decision: "admitted",
    issue: null,
    requested: "max_turns=1",
    supported: "max_turns=1",
    explanation: "As capabilities obrigatórias estão disponíveis para este RunSpec exato.",
    admissionId: "adm_preview_tail_019f",
  },
};

export const CRL_EVENTS = [
  { id: 1, type: "run.queued", phase: "Queue", ref: "event:evt-crl-01", time: "22:03:08" },
  { id: 2, type: "run.preparing", phase: "Preparation", ref: "event:evt-crl-02", time: "22:03:08" },
  { id: 3, type: "context.composed", phase: "Preparation", ref: "event:evt-crl-03", time: "22:03:08" },
  { id: 4, type: "run.running", phase: "Subject", ref: "event:evt-crl-04", time: "22:03:08" },
  { id: 5, type: "subject.invoked", phase: "Subject", ref: "event:evt-crl-05", time: "22:03:08" },
  { id: 6, type: "subject.responded", phase: "Subject", ref: "event:evt-crl-06", time: "22:03:08" },
  { id: 7, type: "run.evaluating", phase: "Evaluation", ref: "event:evt-crl-07", time: "22:03:08" },
  { id: 8, type: "evaluation.completed", phase: "Evaluation", ref: "event:evt-crl-08", time: "22:03:08" },
  { id: 9, type: "run.completed", phase: "Terminal", ref: "event:evt-crl-09", time: "22:03:08" },
];

export const ILLUSTRATIVE_EVENTS = [
  { id: 1, type: "run.queued", phase: "Queue", ref: "event:demo-01" },
  { id: 2, type: "run.preparing", phase: "Preparation", ref: "event:demo-02" },
  { id: 3, type: "context.composed", phase: "Preparation", ref: "event:demo-03" },
  { id: 4, type: "run.running", phase: "Subject", ref: "event:demo-04" },
  { id: 5, type: "subject.invoked", phase: "Subject", ref: "event:demo-05" },
  { id: 6, type: "tool.called · read_text", phase: "Subject", ref: "event:demo-06" },
  { id: 7, type: "tool.completed", phase: "Subject", ref: "event:demo-07" },
  { id: 8, type: "subject.responded", phase: "Subject", ref: "event:demo-08" },
  { id: 9, type: "run.evaluating", phase: "Evaluation", ref: "event:demo-09" },
];

export const STUB_EVENTS = [
  { id: 1, type: "run.queued", phase: "Queue", ref: "event:demo-stub-01" },
  { id: 2, type: "run.preparing", phase: "Preparation", ref: "event:demo-stub-02" },
  { id: 3, type: "context.composed", phase: "Preparation", ref: "event:demo-stub-03" },
  { id: 4, type: "run.running", phase: "Subject", ref: "event:demo-stub-04" },
  { id: 5, type: "subject.invoked", phase: "Subject", ref: "event:demo-stub-05" },
  { id: 6, type: "subject.responded", phase: "Subject", ref: "event:demo-stub-06" },
  { id: 7, type: "run.evaluating", phase: "Evaluation", ref: "event:demo-stub-07" },
  { id: 8, type: "evaluation.completed", phase: "Evaluation", ref: "event:demo-stub-08" },
  { id: 9, type: "run.completed", phase: "Terminal", ref: "event:demo-stub-09" },
];

export const RUN_PHASES = ["queued", "preparing", "running", "evaluating", "terminal"];

export const INITIAL_CHAT_MESSAGES = [
  {
    id: "context",
    role: "agent",
    text: "Posso discutir este Project, a Study, a Run selecionada e suas referências. O Chat não entra no SubjectEnvelope.",
  },
];
