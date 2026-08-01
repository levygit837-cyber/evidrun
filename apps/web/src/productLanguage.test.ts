import { describe, expect, it } from "vitest";
import {
  admissionStateLabels,
  navigationAreas,
  productTerms,
  runStatusLabels,
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
    expect(runStatusLabels.running).toBe("Running");
    expect(runStatusLabels.completed).toBe("Completed");
  });

  it("keeps routes stable behind natural navigation names", () => {
    expect(navigationAreas).toEqual({
      "/create": "Study Builder",
      "/laboratory": "Laboratory",
      "/observability": "Runs",
    });
  });
});
