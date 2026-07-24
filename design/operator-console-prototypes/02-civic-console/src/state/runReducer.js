import { runPhases } from "../data/mockData.js";

export const initialRunState = {
  status: "idle",
  cursor: -1,
  events: [],
  jobId: null,
  attemptId: null,
  outcome: null,
  autoAdvance: false,
};

export function runReducer(state, action) {
  switch (action.type) {
    case "start":
      return {
        status: "running",
        cursor: -1,
        events: [],
        jobId: "JOB-STUB-042",
        attemptId: "ATTEMPT-STUB-01",
        outcome: null,
        autoAdvance: true,
      };
    case "advance": {
      const phase = runPhases[action.cursor];
      if (!phase) return state;
      return {
        ...state,
        cursor: action.cursor,
        events: [...state.events, { ...phase, time: action.time }],
      };
    }
    case "complete":
      return { ...state, status: "completed", outcome: "completed", autoAdvance: false };
    case "fail":
      return {
        ...state,
        status: "failed",
        outcome: "failed",
        autoAdvance: false,
        events: state.events.some((event) => event.id === "terminal")
          ? state.events
          : [
              ...state.events,
              {
                ...runPhases[runPhases.length - 1],
                label: "Terminal",
                detail: "Falha determinística registrada no stub.",
                time: action.time,
              },
            ],
      };
    case "preset-running":
      return {
        status: "running",
        cursor: 2,
        events: runPhases.slice(0, 3).map((phase, index) => ({
          ...phase,
          time: `11:3${index}`,
        })),
        jobId: "JOB-STUB-041",
        attemptId: "ATTEMPT-STUB-01",
        outcome: null,
        autoAdvance: false,
      };
    case "preset-failed":
      return {
        status: "failed",
        cursor: 4,
        events: runPhases.map((phase, index) => ({
          ...phase,
          detail:
            phase.id === "terminal"
              ? "Falha determinística registrada no stub."
              : phase.detail,
          time: `11:4${index}`,
        })),
        jobId: "JOB-STUB-040",
        attemptId: "ATTEMPT-STUB-02",
        outcome: "failed",
        autoAdvance: false,
      };
    case "preset-completed":
      return {
        status: "completed",
        cursor: 4,
        events: runPhases.map((phase, index) => ({
          ...phase,
          time: `11:5${index}`,
        })),
        jobId: "JOB-STUB-039",
        attemptId: "ATTEMPT-STUB-01",
        outcome: "completed",
        autoAdvance: false,
      };
    case "reset":
      return initialRunState;
    default:
      return state;
  }
}

export const runSequenceLength = runPhases.length;
