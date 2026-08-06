import type { LabUiEvent } from "../../data/contracts";

export type LaboratoryPhase =
  | "empty"
  | "ready"
  | "submitting"
  | "active"
  | "stopping"
  | "completed"
  | "proposed"
  | "exhausted"
  | "cancelled"
  | "failed"
  | "unavailable";

/** Os seis terminais nomeados do laço, mapeados um a um para a fase da UI.
 *
 * Mapa explícito, nunca busca de substring no rótulo. `budget_exhausted` e `repeated_refusal`
 * contêm nem "cancel" nem "fail", então uma heurística de texto os classificava como `completed` —
 * e o contrato do laço proíbe apresentar turno parcial como completo. `proposed` também precisa de
 * fase própria: o contrato exige que a UI distinga explicação de proposta, porque draft tem
 * caminho humano de aceitação e resposta não.
 *
 * Terminal novo no backend cai em `undefined` aqui e o chamador falha explícito, em vez de virar
 * conclusão silenciosa.
 */
export const PHASE_BY_TERMINAL: Record<string, LaboratoryPhase> = {
  answered: "completed",
  proposed: "proposed",
  budget_exhausted: "exhausted",
  repeated_refusal: "exhausted",
  provider_failed: "failed",
  cancelled: "cancelled",
};

export type ToolEvent = Extract<LabUiEvent, { type: "tool" }>;
export type MenuOption = { value: string; label: string };
export type ContextItem = { id: string; label: string; kind: "run" | "artifact" };

export const phaseLabels: Record<LaboratoryPhase, string> = {
  empty: "Aguardando pergunta",
  ready: "Pronto para enviar",
  submitting: "Enviando ao Lab Agent",
  active: "Turno em andamento",
  stopping: "Cancelando o turno",
  completed: "Turno concluído",
  proposed: "Draft proposto para decisão humana",
  exhausted: "Turno encerrado por teto; trabalho parcial",
  cancelled: "Turno cancelado",
  failed: "Turno recusado ou com falha",
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
