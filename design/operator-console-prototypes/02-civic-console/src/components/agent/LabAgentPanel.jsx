import { useEffect } from "react";
import {
  agentSequenceLength,
  nextAgentCursor,
} from "../../state/agentReducer.js";
import { ConversationFeed } from "./ConversationFeed.jsx";
import { EvidenceComposer } from "./EvidenceComposer.jsx";
import { RegistrationProgress } from "./RegistrationProgress.jsx";

function eventTime(cursor) {
  return `11:25:${String(10 + cursor * 2).padStart(2, "0")}`;
}

export function LabAgentPanel({
  state,
  dispatch,
  composerState,
  onComposerStateChange,
  projectName,
}) {
  useEffect(() => {
    if (state.phase !== "running") return undefined;

    const next = nextAgentCursor(state);
    if (state.preset === "running" && next >= 3) return undefined;

    if (state.preset === "failure" && next >= 3) {
      const timer = window.setTimeout(() => dispatch({ type: "fail" }), 220);
      return () => window.clearTimeout(timer);
    }

    if (next >= agentSequenceLength) {
      const timer = window.setTimeout(
        () =>
          dispatch({
            type: "succeed",
            id: "local",
            time: "11:25",
          }),
        220,
      );
      return () => window.clearTimeout(timer);
    }

    const timer = window.setTimeout(
      () =>
        dispatch({
          type: "advance",
          cursor: next,
          time: eventTime(next),
        }),
      220,
    );
    return () => window.clearTimeout(timer);
  }, [dispatch, state]);

  return (
    <section className="lab-agent-panel" aria-labelledby="lab-agent-heading">
      <div className="agent-panel-toolbar">
        <div>
          <h2 id="lab-agent-heading">Lab Agent</h2>
          <p>Composer local para drafts e pedidos de revisão.</p>
        </div>
        <label className="preset-control">
          Preset
          <select
            aria-label="Preset do agente"
            value={state.preset}
            onChange={(event) =>
              dispatch({ type: "set-preset", preset: event.target.value })
            }
          >
            <option value="idle">Idle</option>
            <option value="running">Running</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
          </select>
        </label>
      </div>

      <ConversationFeed state={state} />
      <RegistrationProgress phase={state.phase} cursor={state.cursor} />
      <EvidenceComposer
        disabled={state.phase === "running"}
        projectName={projectName}
        value={composerState.value}
        onValueChange={(value) => onComposerStateChange({ value })}
        sourceSelected={composerState.sourceSelected}
        onSourceSelectedChange={(sourceSelected) =>
          onComposerStateChange({ sourceSelected })
        }
        onSubmit={(text) =>
          dispatch({
            type: "submit",
            text,
            preset: state.preset,
            id: Date.now(),
            time: "11:25",
          })
        }
      />
    </section>
  );
}
