import { RefusalError } from "../../api/client";
import type { TriageErrorCode } from "../../generated/contracts";
import { admissionStateLabels, studyPipelineSteps } from "../../productLanguage";

export type Step = (typeof studyPipelineSteps)[number]["id"];
export type AdmissionState = "admitted" | "rejected" | "failed" | "unavailable" | "stale";
export type DownstreamState = "empty" | "fresh" | "stale";
export type EvaluationDisclosure = "none" | "pre_run";

/**
 * The Admission state each named refusal maps to.
 *
 * Partial on purpose: only codes the Create corridor can actually surface are listed, and an
 * unlisted code is handled as `failed` rather than silently gaining a state.
 */
export const ADMISSION_STATE_BY_CODE: Partial<Record<TriageErrorCode, AdmissionState>> = {
  "admit.rejected": "rejected",
  "admit.run_spec_not_found": "failed",
  "admit.inventory_not_persistible": "unavailable",
  "register.storage_unavailable": "unavailable",
  "decide.human_authority_unavailable": "unavailable",
  "compile.dependency_not_accepted": "rejected",
  "compile.revision_not_found": "failed",
  "enqueue.admission_not_admitted": "rejected",
};

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
  admitted: { label: admissionStateLabels.admitted, tone: "success" },
  rejected: { label: admissionStateLabels.rejected, tone: "danger" },
  failed: { label: admissionStateLabels.failed, tone: "danger" },
  unavailable: { label: admissionStateLabels.unavailable, tone: "neutral" },
  stale: { label: admissionStateLabels.stale, tone: "warning" },
};

export const steps: ReadonlyArray<{ id: Step; label: string; technicalName: string }> =
  studyPipelineSteps;

export function resultLink(runId: string): string {
  return `#/observability?run=${encodeURIComponent(runId)}`;
}

/**
 * Map a refusal onto the Admission state the interface distinguishes.
 *
 * The code decides; the message is only text for the human. A code this console does not know
 * falls into `failed`, the declared safe state — never into an optimistic one by omission.
 */
export function classifyFailure(error: unknown): AdmissionState {
  const code = error instanceof RefusalError ? error.triage?.code : undefined;
  return code ? (ADMISSION_STATE_BY_CODE[code] ?? "failed") : "failed";
}
