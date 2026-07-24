import { useState } from "react";
import { Flask, LinkBreak, ShieldCheck } from "@phosphor-icons/react";
import { RUN_TRACE_STAGES } from "../data/mockData.js";
import { useOperator } from "../context/OperatorContext.jsx";
import {
  AgentBoundaryDisclosure,
  Composer,
  ConversationPreview,
  EventInspector,
  ExecutionStatus,
  ObservableActivity,
} from "../components/AgentBlocks.jsx";
import { RunTrace } from "../components/RunTrace.jsx";
import { TechnicalId } from "../components/Primitives.jsx";

export function LabRoute() {
  const { state } = useOperator();
  const [selectedStage, setSelectedStage] = useState("tool-read");
  const currentProject = state.projects.find((project) => project.id === state.currentProjectId);

  if (!state.study) {
    return (
      <div className="route route--lab">
        <header className="study-header">
          <div className="study-header__icon" aria-hidden="true"><LinkBreak size={22} /></div>
          <div>
            <p className="study-header__context">Lab fail-closed</p>
            <h1>Nenhuma Study vinculada</h1>
            <div className="study-header__meta">
              <span>Project: {currentProject?.name}</span>
              <span><ShieldCheck size={16} aria-hidden="true" /> Escopo local isolado</span>
            </div>
          </div>
        </header>

        <section className="scope-empty-state" aria-labelledby="lab-empty-title">
          <div className="scope-empty-state__icon" aria-hidden="true"><LinkBreak size={25} /></div>
          <div>
            <p>Vínculo obrigatório ausente</p>
            <h2 id="lab-empty-title">Nenhuma Study vinculada a {currentProject?.name}.</h2>
            <span>
              O Lab Agent permanece indisponível até este Project receber uma Study por um fluxo
              autorizado. Nenhum evento, evidence ou draft de outro Project é exibido aqui.
            </span>
          </div>
        </section>

        <div className="lab-composer-zone">
          <Composer />
        </div>
      </div>
    );
  }

  return (
    <div className="route route--lab">
      <header className="study-header">
        <div className="study-header__icon" aria-hidden="true"><Flask size={22} /></div>
        <div>
          <p className="study-header__context">Study ativa</p>
          <h1>{state.study.title}</h1>
          <div className="study-header__meta">
            <span>Project: {currentProject?.name}</span>
            <span><ShieldCheck size={16} aria-hidden="true" /> Demonstração local</span>
          </div>
          <div className="study-header__technical-context">
            <span>Cenário <TechnicalId>{state.study.scenario}</TechnicalId></span>
            <span>Variante <TechnicalId>{state.study.variant}</TechnicalId></span>
          </div>
        </div>
      </header>

      <AgentBoundaryDisclosure />

      <RunTrace
        stages={RUN_TRACE_STAGES}
        currentStage="evaluation"
        selectedStage={selectedStage}
        onSelect={setSelectedStage}
      />

      <EventInspector selectedStage={selectedStage} />

      <div className="lab-conversation-zone">
        <ConversationPreview />
        <ObservableActivity />
      </div>

      <div className="lab-composer-zone">
        <ExecutionStatus />
        <Composer />
      </div>
    </div>
  );
}
