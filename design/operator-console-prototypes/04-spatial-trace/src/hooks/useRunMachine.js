import { useCallback, useEffect, useReducer, useRef } from "react";
import { eventsForPhase } from "../data/stubData.js";

export const initialRunState = {
  phase: "idle",
  events: [],
  sequence: 0,
};

export function runReducer(state, action) {
  switch (action.type) {
    case "START":
      return {
        phase: "queued",
        events: eventsForPhase("queued"),
        sequence: state.sequence + 1,
      };
    case "ADVANCE":
      return {
        ...state,
        phase: action.phase,
        events: eventsForPhase(action.phase),
      };
    case "PREVIEW":
      return {
        ...state,
        phase: action.phase,
        events: action.phase === "idle" ? [] : eventsForPhase(action.phase),
      };
    case "RESET":
      return initialRunState;
    default:
      return state;
  }
}

export function useRunMachine() {
  const [state, dispatch] = useReducer(runReducer, initialRunState);
  const timers = useRef([]);

  const clearTimers = useCallback(() => {
    timers.current.forEach((timer) => window.clearTimeout(timer));
    timers.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  const start = useCallback(() => {
    clearTimers();
    dispatch({ type: "START" });
    [
      [360, "preparing"],
      [760, "running"],
      [1260, "evaluating"],
      [1760, "completed"],
    ].forEach(([delay, phase]) => {
      timers.current.push(
        window.setTimeout(() => dispatch({ type: "ADVANCE", phase }), delay),
      );
    });
  }, [clearTimers]);

  const preview = useCallback(
    (phase) => {
      clearTimers();
      dispatch({ type: "PREVIEW", phase });
    },
    [clearTimers],
  );

  return { state, start, preview };
}
