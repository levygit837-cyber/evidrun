import { RUN_PHASES } from "../data/mockData.js";

export const runInitialState = {
  preset: "completed",
  phaseIndex: 4,
  status: "completed",
  runId: "run_019f9100...ae5e5",
  jobId: "job_019f9100...4b72",
  attemptId: "attempt_01",
  exported: false,
  digest: null,
  generation: 0,
};

export function runReducer(state, action) {
  switch (action.type) {
    case "START":
      return {
        ...runInitialState,
        preset: "progressing",
        phaseIndex: 0,
        status: RUN_PHASES[0],
        runId: "demo:run-stub-admitted",
        jobId: "demo:job-stub-01",
        attemptId: "demo:attempt-01",
        generation: state.generation + 1,
      };
    case "ADVANCE": {
      const nextIndex = Math.min(state.phaseIndex + 1, RUN_PHASES.length - 1);
      return {
        ...state,
        phaseIndex: nextIndex,
        status: RUN_PHASES[nextIndex],
      };
    }
    case "PRESET":
      if (action.preset === "loading") return { ...state, preset: "loading", status: "loading", exported: false, digest: null, generation: state.generation + 1 };
      if (action.preset === "failed") return { ...state, preset: "failed", status: "failed", phaseIndex: 2, exported: false, digest: null, generation: state.generation + 1 };
      if (action.preset === "live") return { ...state, preset: "live", status: "evaluating", phaseIndex: 3, runId: "demo:run-live-read-text", jobId: "demo:job-live-01", attemptId: "demo:attempt-live-01", exported: false, digest: null, generation: state.generation + 1 };
      return { ...runInitialState, generation: state.generation + 1 };
    case "EXPORTED":
      return { ...state, exported: true, digest: action.digest };
    default:
      return state;
  }
}
