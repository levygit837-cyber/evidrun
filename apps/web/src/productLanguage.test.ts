import { describe, expect, it } from "vitest";
import {
  admissionStateLabels,
  auditTerm,
  navigationAreas,
  productTerms,
  runStatusLabel,
  studyPipelineSteps,
} from "./productLanguage";

describe("product language", () => {
  it("separates planning, readiness and factual execution", () => {
    expect([
      productTerms.runSpec.label,
      productTerms.admission.label,
      productTerms.run.label,
    ]).toEqual(["Execution Plan", "Readiness Check", "Run"]);
    expect(studyPipelineSteps.map((step) => step.label)).toEqual([
      "Study Design",
      "Execution Plans",
      "Readiness Check",
      "Runs",
    ]);
  });

  it("keeps canonical identifiers available without using them as explanations", () => {
    expect(productTerms.study.technicalName).toBe("Study");
    expect(productTerms.runSpec.technicalName).toBe("RunSpec");
    expect(productTerms.admission.technicalName).toBe("AdmissionRecord");
    expect(productTerms.run.technicalName).toBe("Run");
    expect(productTerms.subjectEnvelope.label).toBe("Subject Context");
  });

  it("translates machine states while preserving their stable keys", () => {
    expect(Object.keys(admissionStateLabels)).toEqual([
      "admitted",
      "rejected",
      "failed",
      "unavailable",
      "stale",
    ]);
    expect(runStatusLabel("running")).toBe("Running");
    expect(runStatusLabel("completed")).toBe("Completed");
    expect(runStatusLabel("future_status")).toBe("future_status");
    expect(runStatusLabel("toString")).toBe("toString");
  });

  it("keeps technical identifiers visible on audit surfaces", () => {
    expect(auditTerm(productTerms.runSpec)).toBe("Execution Plan (RunSpec)");
    expect(auditTerm(productTerms.admission)).toBe("Readiness Check (AdmissionRecord)");
    expect(auditTerm(productTerms.run)).toBe("Run");
  });

  it("keeps routes stable behind natural navigation names", () => {
    expect(navigationAreas).toEqual({
      "/create": "Study Builder",
      "/laboratory": "Laboratory",
      "/observability": "Runs",
    });
  });
});
