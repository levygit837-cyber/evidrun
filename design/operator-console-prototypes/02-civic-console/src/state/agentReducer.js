import { observableSequence } from "../data/mockData.js";

export const initialAgentState = {
  phase: "idle",
  preset: "success",
  cursor: 3,
  activity: observableSequence.slice(0, 4).map((event, index) => ({
    ...event,
    time: `11:24:${String(10 + index * 2).padStart(2, "0")}`,
  })),
  messages: [
    {
      id: "seed-user",
      author: "User",
      text: "Compare as variantes e identifique respostas sem cobertura de fonte.",
      time: "11:24",
    },
    {
      id: "seed-agent",
      author: "Lab Agent",
      text: "Draft: a revisão precisa incluir a cobertura de fontes exigida antes da admissão.",
      time: "11:24",
      draft: true,
    },
  ],
  error: null,
};

export const emptyAgentState = {
  phase: "idle",
  preset: "idle",
  cursor: -1,
  activity: [],
  messages: [],
  error: null,
};

export function agentReducer(state, action) {
  switch (action.type) {
    case "set-preset":
      return { ...state, preset: action.preset };
    case "submit":
      return {
        ...state,
        phase: action.preset === "idle" ? "idle" : "running",
        cursor: -1,
        activity: [],
        error: null,
        messages: [
          ...state.messages,
          {
            id: `user-${action.id}`,
            author: "User",
            text: action.text,
            time: action.time,
          },
        ],
      };
    case "advance": {
      const event = observableSequence[action.cursor];
      if (!event) return state;
      return {
        ...state,
        cursor: action.cursor,
        activity: [...state.activity, { ...event, time: action.time }],
      };
    }
    case "succeed":
      return {
        ...state,
        phase: "success",
        messages: [
          ...state.messages,
          {
            id: `agent-${action.id}`,
            author: "Lab Agent",
            text: "Draft: crie uma nova StudyRevision com cobertura de fontes autorizadas e execute o preflight novamente.",
            time: action.time,
            draft: true,
          },
        ],
      };
    case "fail":
      return {
        ...state,
        phase: "failure",
        error: "A demonstração local interrompeu a captura. Nenhuma Run foi criada.",
      };
    case "reset":
      return { ...initialAgentState, preset: state.preset };
    default:
      return state;
  }
}

export function nextAgentCursor(state) {
  return state.cursor + 1;
}

export const agentSequenceLength = observableSequence.length;
