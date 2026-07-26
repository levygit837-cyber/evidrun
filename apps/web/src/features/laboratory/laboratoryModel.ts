import type { LabUiEvent } from "../../data/contracts";

export type LaboratoryPhase =
  | "empty"
  | "ready"
  | "submitting"
  | "active"
  | "stopping"
  | "completed"
  | "cancelled"
  | "failed"
  | "unavailable";

export type ToolEvent = Extract<LabUiEvent, { type: "tool" }>;
export type MenuOption = { value: string; label: string };
export type ContextItem = { id: string; label: string; kind: "run" | "artifact" };

export const phaseLabels: Record<LaboratoryPhase, string> = {
  empty: "Aguardando pergunta",
  ready: "Pronto para enviar",
  submitting: "Enviando para o adapter Demo",
  active: "Demonstração em andamento",
  stopping: "Cancelando demonstração",
  completed: "Demonstração concluída",
  cancelled: "Demonstração cancelada",
  failed: "Demonstração com falha",
  unavailable: "Laboratory indisponível",
};

/** Phases in which the demo sequence is still producing events. */
export function isRunningPhase(phase: LaboratoryPhase): boolean {
  return phase === "submitting" || phase === "active" || phase === "stopping";
}

export const samplePrompts = [
  "Resuma o contexto desta investigação.",
  "Use ferramentas para inspecionar o Run Demo.",
  "Simule uma falha e permita uma nova tentativa.",
];

/** Textarea auto-growth stays between one row and the composer cap. */
export const TEXTAREA_MIN_HEIGHT_PX = 40;
export const TEXTAREA_MAX_HEIGHT_PX = 160;

export const APPROVAL_OPTIONS: MenuOption[] = [
  { value: "ask", label: "Ask before actions" },
  { value: "read-only", label: "Read-only" },
  { value: "admitted", label: "Allow admitted tools" },
];

export const MODEL_OPTIONS: MenuOption[] = [
  { value: "deepseek-v4-flash", label: "deepseek-v4-flash" },
];

export const REASONING_OPTIONS: MenuOption[] = [
  { value: "low", label: "reasoning: low" },
  { value: "medium", label: "reasoning: medium" },
  { value: "high", label: "reasoning: high" },
  { value: "max", label: "reasoning: max" },
];

export type ContextOptionValue = "run" | "artifact";

export const CONTEXT_OPTIONS: MenuOption[] = [
  { value: "run", label: "Run Demo 018" },
  { value: "artifact", label: "ArtifactRef Demo" },
];

export const CONTEXT_ITEMS: Record<ContextOptionValue, ContextItem> = {
  run: { id: "run-demo-018", label: "Run Demo 018", kind: "run" },
  artifact: { id: "artifact-demo", label: "ArtifactRef Demo", kind: "artifact" },
};
