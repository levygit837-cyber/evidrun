import type { Run } from "../../types";

export function executionTrustText(trust: Run["execution_trust"]): {
  label: string;
  explanation: string;
} {
  if (trust.status === "not_recorded") {
    return { label: "Não registrado", explanation: "Trust legado não inferido" };
  }
  if (trust.kind === "verified_revision_set") {
    return {
      label: "Verificada",
      explanation: "Revisions confirmadas por autoridade humana",
    };
  }
  if (trust.kind === "unverified_revision_set") {
    return {
      label: "Não verificada",
      explanation: "Sem confirmação humana das revisions",
    };
  }
  return { label: "Inválido", explanation: "Record de trust incompleto" };
}

export function isolationText(isolation: string): string {
  return isolation === "not_recorded" ? "Não registrado" : isolation;
}
