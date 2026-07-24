import { Plugs } from "@phosphor-icons/react";
import { LabAgentPanel } from "../components/agent/LabAgentPanel.jsx";
import { SurfaceHeader } from "../components/primitives/SurfaceHeader.jsx";
import { WorkflowBoard } from "../components/workflow/WorkflowBoard.jsx";

export function LabRoute({
  project,
  activeRevision,
  onCorrectRevision,
  onNavigate,
  agentState,
  onAgentDispatch,
  composerState,
  onComposerStateChange,
}) {
  return (
    <div className="route-stack">
      <SurfaceHeader
        eyebrow="Lab"
        title={project.name}
        description={`Estudo: ${project.study}`}
        action={
          <div className="workspace-disclosure">
            <Plugs aria-hidden="true" size={19} />
            <div>
              <span>Workspace</span>
              <strong>Integration pending</strong>
            </div>
          </div>
        }
      />
      <WorkflowBoard
        activeRevision={activeRevision}
        onCorrectRevision={onCorrectRevision}
        onNavigate={onNavigate}
      />
      <LabAgentPanel
        state={agentState}
        dispatch={onAgentDispatch}
        composerState={composerState}
        onComposerStateChange={onComposerStateChange}
        projectName={project.name}
      />
    </div>
  );
}
