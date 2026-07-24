export const agentInitialState = {
  phase: "idle",
  step: 0,
  prompt: "",
  failure: null,
  requestId: 0,
};

export function agentReducer(state, action) {
  switch (action.type) {
    case "SUBMIT":
      return {
        phase: "running",
        step: 0,
        prompt: action.prompt,
        failure: null,
        requestId: state.requestId + 1,
      };
    case "ADVANCE":
      return state.phase === "running" ? { ...state, step: Math.min(state.step + 1, 2) } : state;
    case "SUCCEED":
      return { ...state, phase: "success", step: 2, failure: null };
    case "FAIL":
      return { ...state, phase: "failure", failure: "O stub interrompeu a sequência antes de criar um draft." };
    case "PRESET":
      if (action.phase === "idle") return { ...agentInitialState, requestId: state.requestId + 1 };
      if (action.phase === "running") return { ...state, phase: "running", step: 1, prompt: "Inspecione referências autorizadas.", failure: null, requestId: state.requestId + 1 };
      if (action.phase === "failure") return { ...state, phase: "failure", step: 1, prompt: "Inspecione referências autorizadas.", failure: "Falha determinística de leitura no stub local.", requestId: state.requestId + 1 };
      return { ...state, phase: "success", step: 2, prompt: "Compare os registros autorizados e prepare um draft.", failure: null, requestId: state.requestId + 1 };
    default:
      return state;
  }
}
