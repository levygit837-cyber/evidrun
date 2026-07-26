export type Step = 1 | 2 | 3 | 4;
export type AdmissionState = "admitted" | "rejected" | "failed" | "unavailable" | "stale";
export type DownstreamState = "empty" | "fresh" | "stale";
export type EvaluationDisclosure = "none" | "pre_run";

export interface StudyItem {
  id: string;
  name: string;
}

export interface StudyDraft {
  name: string;
  objective: string;
  hypothesis: string;
  evaluationDisclosure: EvaluationDisclosure;
  scenarios: StudyItem[];
  variants: StudyItem[];
  evaluationModules: StudyItem[];
}

export type StudyCollection = "scenarios" | "variants" | "evaluationModules";

export interface CompiledStudy extends StudyDraft {
  revision: number;
}

export const initialStudy: StudyDraft = {
  name: "Recuperação fundamentada por tool",
  objective: "Comparar a recuperação de contexto entre baseline e candidate.",
  hypothesis: "A variante candidate preserva evidência suficiente para responder com fundamento.",
  evaluationDisclosure: "none",
  scenarios: [{ id: "scenario-1", name: "tool-result pressure" }],
  variants: [
    { id: "variant-1", name: "Full context" },
    { id: "variant-2", name: "Tool-guided context" },
  ],
  evaluationModules: [{ id: "evaluation-1", name: "grounded retrieval" }],
};

export const admissionCopy: Record<AdmissionState, { label: string; tone: "success" | "danger" | "warning" | "neutral" }> = {
  admitted: { label: "admitted", tone: "success" },
  rejected: { label: "rejected", tone: "danger" },
  failed: { label: "failed", tone: "danger" },
  unavailable: { label: "unavailable", tone: "neutral" },
  stale: { label: "stale", tone: "warning" },
};

export const steps: Array<{ id: Step; label: string }> = [
  { id: 1, label: "Study" },
  { id: 2, label: "RunSpecs" },
  { id: 3, label: "Admission" },
  { id: 4, label: "Runs" },
];

export function resultLink(runId: string): string {
  return `#/observability?run=${encodeURIComponent(runId)}`;
}

/**
 * Maps a bootstrap rejection onto the Admission state the interface distinguishes. The backend
 * reports the reason inside the message, so matching is done on substrings in both languages.
 */
export function classifyFailure(error: unknown): AdmissionState {
  const message = error instanceof Error ? error.message.toLowerCase() : "";
  if (message.includes("rejected") || message.includes("rejeitad")) return "rejected";
  if (message.includes("unavailable") || message.includes("indispon")) return "unavailable";
  if (message.includes("stale")) return "stale";
  return "failed";
}
