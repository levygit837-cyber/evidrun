import { useEffect, useReducer, useRef, useState } from "react";
import {
  ArrowRight,
  ChartLineUp,
  ChatsCircle,
  FileText,
  PaperPlaneTilt,
  PencilSimple,
  ShieldCheck,
} from "@phosphor-icons/react";
import { agentInitialState, agentReducer } from "../state/agentState.js";
import { AgentExchange, LedgerCursor } from "../components/agent/AgentBlocks.jsx";
import { Button, Notice, SegmentedControl, StatusBadge } from "../components/primitives/Controls.jsx";

const AGENT_PRESETS = [
  { value: "idle", label: "Idle" },
  { value: "running", label: "Running" },
  { value: "success", label: "Success" },
  { value: "failure", label: "Failure" },
];

export function LabRoute({ navigate, onOpenChat, project }) {
  const [experience, setExperience] = useState("first-use");
  const [draft, setDraft] = useState("");
  const [agent, dispatch] = useReducer(agentReducer, agentInitialState);
  const inputRef = useRef(null);

  useEffect(() => {
    if (agent.phase !== "running") return undefined;
    const timeout = setTimeout(() => {
      if (agent.step < 2) dispatch({ type: "ADVANCE" });
      else dispatch({ type: "SUCCEED" });
    }, 620);
    return () => clearTimeout(timeout);
  }, [agent.phase, agent.step, agent.requestId]);

  useEffect(() => {
    if (agent.phase === "success" || agent.phase === "failure") inputRef.current?.focus();
  }, [agent.phase]);

  const submit = () => {
    const prompt = draft.trim();
    if (!prompt) return;
    dispatch({ type: "SUBMIT", prompt });
    setDraft("");
    setExperience("returning");
  };

  const switchExperience = (value) => {
    setExperience(value);
    if (value === "returning" && agent.phase === "idle") dispatch({ type: "PRESET", phase: "success" });
  };

  return (
    <div className="route route--lab">
      <header className="route-header route-header--lab">
        <div>
          <span className="route-kicker">Lab</span>
          <h1>{experience === "first-use" ? "O que você quer investigar?" : "Evidência em contexto"}</h1>
          <p>{experience === "first-use" ? "Converse, localize referências ou transforme uma intenção em draft de Study." : "Retome a conversa sem misturar Chat com o contexto do Subject Agent."}</p>
        </div>
        <SegmentedControl
          label="Estado da experiência Lab"
          value={experience}
          onChange={switchExperience}
          options={[{ value: "first-use", label: "Primeiro uso" }, { value: "returning", label: "Retorno" }]}
        />
      </header>

      <div className={`lab-layout ${experience === "first-use" ? "is-first-use" : ""}`}>
        <section className="lab-main" aria-label="Conversa e intenção">
          {experience === "first-use" ? (
            <div className="lab-first-use">
              <div className="lab-first-use__principles">
                <article><ChatsCircle size={22} aria-hidden="true" /><strong>Converse</strong><span>Chat contextual acompanha o trabalho.</span></article>
                <ArrowRight className="lab-first-use__flow-arrow" size={18} aria-hidden="true" />
                <article><PencilSimple size={22} aria-hidden="true" /><strong>Gere um draft</strong><span>O Lab Agent propõe, sem aceitar.</span></article>
                <ArrowRight className="lab-first-use__flow-arrow" size={18} aria-hidden="true" />
                <article><ShieldCheck size={22} aria-hidden="true" /><strong>Revise como humano</strong><span>Autoridade exige adapter confiável.</span></article>
              </div>
              <Notice compact title="Demonstração local">
                O backend é um stub determinístico. Nenhum provider, repositório ou adapter de autoridade é chamado.
              </Notice>
            </div>
          ) : (
            <AgentExchange prompt={agent.prompt} phase={agent.phase} step={agent.step} />
          )}

          <section className="lab-composer" aria-labelledby="lab-composer-label">
            {agent.phase === "running" ? <LedgerCursor /> : null}
            <div className="lab-composer__label-row">
              <label id="lab-composer-label" htmlFor="lab-intent">Conversa e intenção</label>
              <StatusBadge tone="neutral">Lab Agent · Draft only</StatusBadge>
            </div>
            <textarea
              ref={inputRef}
              id="lab-intent"
              rows={3}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submit();
                }
              }}
              placeholder="Descreva uma hipótese, uma Run ou a evidência que procura"
              aria-describedby="lab-composer-hint"
            />
            <div className="lab-composer__footer">
              <button type="button" className="project-context-chip" onClick={() => navigate("/projects")}>
                <FileText size={17} aria-hidden="true" /> {project.name} <ArrowRight size={15} aria-hidden="true" />
              </button>
              <Button variant="primary" icon={PaperPlaneTilt} disabled={!draft.trim() || agent.phase === "running"} onClick={submit}>Enviar</Button>
            </div>
            <p id="lab-composer-hint">Enter envia. Shift+Enter cria nova linha. Chat e intent input são complementares.</p>
          </section>
        </section>

        {project.id === "crl" ? (
          <aside className="lab-context" aria-label="Contexto da evidência">
            <div className="lab-context__heading">
              <div><ChartLineUp size={21} aria-hidden="true" /><h2>Referência registrada</h2></div>
              <StatusBadge tone="info">CRL-CTX-002</StatusBadge>
            </div>
            <h3>Preservação da causa-raiz em logs longos</h3>
            <p>Fixture canônica com execução local capturada. Os valores abaixo pertencem somente a essa referência.</p>
            <div className="comparison-mini" aria-label="Comparação conhecida da fixture">
              <div><span>head-truncation</span><strong>0.0</strong></div>
              <div className="comparison-mini__delta"><span>delta</span><strong>1.0</strong></div>
              <div className="is-selected"><span>tail-preservation</span><strong>1.0</strong></div>
            </div>
            <dl className="context-facts">
              <div><dt>SubjectEnvelope</dt><dd>Chat excluído</dd></div>
              <div><dt>Authority</dt><dd>indisponível</dd></div>
              <div><dt>Persistência</dt><dd>nenhuma neste stub</dd></div>
            </dl>
            <Button variant="secondary" onClick={onOpenChat}>Abrir Chat contextual</Button>
          </aside>
        ) : (
          <aside className="lab-context" aria-label="Contexto do Project">
            <div className="lab-context__heading">
              <div><FileText size={21} aria-hidden="true" /><h2>Project selecionado</h2></div>
              <StatusBadge tone="warning">sem evidência</StatusBadge>
            </div>
            <h3>{project.name}</h3>
            <p>{project.description}</p>
            <Notice compact title="Escopo preservado">Nenhuma Study, Run ou evidência está vinculada. CRL-CTX-002 permanece uma fixture separada.</Notice>
            <dl className="context-facts">
              <div><dt>Study</dt><dd>não vinculada</dd></div>
              <div><dt>Run</dt><dd>não vinculada</dd></div>
              <div><dt>Persistência</dt><dd>estado React local</dd></div>
            </dl>
            <Button variant="secondary" onClick={onOpenChat}>Abrir Chat contextual</Button>
          </aside>
        )}
      </div>

      <footer className="demo-presets">
        <span>Estados do agente</span>
        <SegmentedControl
          compact
          label="Preset do agente"
          value={agent.phase}
          onChange={(phase) => { setExperience("returning"); dispatch({ type: "PRESET", phase }); }}
          options={AGENT_PRESETS}
        />
      </footer>
      <div className="sr-only" aria-live="polite">Estado do Lab Agent: {agent.phase}</div>
    </div>
  );
}
