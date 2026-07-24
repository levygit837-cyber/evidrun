import { describe, expect, it } from "vitest";
import {
  agentReducer,
  initialAgentState,
} from "./agentReducer.js";
import { initialRunState, runReducer } from "./runReducer.js";

describe("reducers determinísticos", () => {
  it("mantém eventos observáveis separados de mensagens do agente", () => {
    const submitted = agentReducer(initialAgentState, {
      type: "submit",
      text: "Verifique a cobertura.",
      preset: "success",
      id: "test",
      time: "11:25",
    });
    const advanced = agentReducer(submitted, {
      type: "advance",
      cursor: 0,
      time: "11:25:10",
    });

    expect(advanced.phase).toBe("running");
    expect(advanced.activity).toHaveLength(1);
    expect(advanced.activity[0].label).toBe("Preparando contexto permitido");
    expect(advanced.messages.at(-1).author).toBe("User");
  });

  it("registra queued até terminal sem fundir job e attempt", () => {
    let state = runReducer(initialRunState, { type: "start" });
    for (let cursor = 0; cursor < 5; cursor += 1) {
      state = runReducer(state, {
        type: "advance",
        cursor,
        time: `11:32:${cursor}`,
      });
    }
    state = runReducer(state, { type: "complete" });

    expect(state.events.map((event) => event.id)).toEqual([
      "queued",
      "preparing",
      "running",
      "evaluating",
      "terminal",
    ]);
    expect(state.jobId).toBe("JOB-STUB-042");
    expect(state.attemptId).toBe("ATTEMPT-STUB-01");
    expect(state.status).toBe("completed");
  });
});
