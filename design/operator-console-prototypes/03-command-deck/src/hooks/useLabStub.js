import { useCallback, useEffect, useReducer, useRef } from "react";
import { labSequence } from "../data/mockData.js";

const initialState = {
  demoMode: "success",
  execution: "idle",
  stageIndex: -1,
  userMessage: "",
  agentMessage: "",
  thinkingOpen: false,
  toolResult: null,
};

function reducer(state, action) {
  switch (action.type) {
    case "SET_MODE":
      return { ...initialState, demoMode: action.mode };
    case "START":
      return {
        ...state,
        execution: "active",
        stageIndex: 0,
        userMessage: action.message,
        agentMessage: "",
        thinkingOpen: false,
        toolResult: null,
      };
    case "ADVANCE":
      return { ...state, stageIndex: action.stageIndex };
    case "COMPLETE":
      return {
        ...state,
        execution: action.outcome,
        stageIndex: labSequence.length - 1,
        agentMessage: action.agentMessage,
        toolResult: action.toolResult,
      };
    case "TOGGLE_THINKING":
      return { ...state, thinkingOpen: !state.thinkingOpen };
    default:
      return state;
  }
}

const OUTCOMES = {
  success: {
    outcome: "success",
    agentMessage:
      "O stub encontrou um sinal de latência após o deploy. A resposta está limitada ao trecho autorizado e precisa de validação humana antes de virar conclusão.",
    toolResult: "excerpt",
  },
  empty: {
    outcome: "empty",
    agentMessage:
      "O input autorizado não contém registros suficientes para sustentar uma hipótese. Amplie o contexto somente por um novo draft e nova Admission.",
    toolResult: "empty",
  },
  failure: {
    outcome: "failure",
    agentMessage:
      "A leitura do stub falhou antes da resposta. Nenhum resultado foi promovido a evidência e a execução permanece demonstrativa.",
    toolResult: "failure",
  },
};

export function useLabStub() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const timersRef = useRef([]);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  const send = useCallback(
    (message) => {
      const trimmed = message.trim();
      if (!trimmed || state.execution === "active") return false;

      clearTimers();
      dispatch({ type: "START", message: trimmed });

      for (let index = 1; index < labSequence.length; index += 1) {
        timersRef.current.push(
          window.setTimeout(() => {
            dispatch({ type: "ADVANCE", stageIndex: index });
          }, index * 260),
        );
      }

      timersRef.current.push(
        window.setTimeout(() => {
          dispatch({ type: "COMPLETE", ...OUTCOMES[state.demoMode] });
        }, labSequence.length * 260),
      );
      return true;
    },
    [clearTimers, state.demoMode, state.execution],
  );

  return {
    state,
    send,
    setDemoMode: (mode) => {
      clearTimers();
      dispatch({ type: "SET_MODE", mode });
    },
    toggleThinking: () => dispatch({ type: "TOGGLE_THINKING" }),
  };
}
