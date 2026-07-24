import { useState } from "react";
import {
  ArrowRight,
  Check,
  FileMagnifyingGlass,
  FloppyDisk,
  GridFour,
  Notebook,
  PlayCircle,
  ShieldCheck,
  ShieldWarning,
} from "@phosphor-icons/react";
import { runSpecs, studyRevisions } from "../data/mockData.js";
import {
  Definition,
  LocalDataFlag,
  PageIntro,
  SectionHeader,
  SegmentedControl,
  StatusLabel,
} from "../components/ui.jsx";

export function StudyRoute({ navigate }) {
  const [revisionId, setRevisionId] = useState(studyRevisions[0].id);
  const selectedRevision = studyRevisions.find((revision) => revision.id === revisionId) ?? studyRevisions[0];
  const [objective, setObjective] = useState(selectedRevision.objective);
  const [saved, setSaved] = useState(false);
  const [admissionState, setAdmissionState] = useState("admitted");
  const [enqueueMessage, setEnqueueMessage] = useState("");

  const changeRevision = (nextId) => {
    const nextRevision = studyRevisions.find((revision) => revision.id === nextId);
    setRevisionId(nextId);
    setObjective(nextRevision?.objective ?? "");
    setSaved(false);
  };

  const saveDraft = () => {
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  };

  return (
    <div className="route-page">
      <PageIntro
        action={<LocalDataFlag />}
        description="Edite uma StudyRevision, confira a matriz e só enfileire RunSpecs que passaram pela Admission."
        icon={Notebook}
        kicker="Release Integrity"
        title="Study"
      />

      <div className="study-grid">
        <section className="draft-editor">
          <SectionHeader
            action={
              <select aria-label="Selecionar revisão" onChange={(event) => changeRevision(event.target.value)} value={revisionId}>
                {studyRevisions.map((revision) => (
                  <option key={revision.id} value={revision.id}>{revision.label} ({revision.state})</option>
                ))}
              </select>
            }
            description="A revisão continua mutável até uma nova compilação."
            title="StudyRevision draft"
          />
          <div className="field">
            <label htmlFor="study-objective">Objetivo</label>
            <textarea id="study-objective" onChange={(event) => setObjective(event.target.value)} rows={4} value={objective} />
            <p className="field__help">{selectedRevision.note}</p>
          </div>
          <div className="draft-editor__footer">
            <span className="mono">{selectedRevision.id}</span>
            <button className="secondary-button" onClick={saveDraft} type="button">
              {saved ? <Check aria-hidden="true" size={17} /> : <FloppyDisk aria-hidden="true" size={17} />}
              {saved ? "Salvo em React state" : "Salvar draft"}
            </button>
          </div>
        </section>

        <section className="matrix-panel">
          <SectionHeader
            description="deployment-log-trace x 2 variantes x 1 repetição"
            title="Matriz de execução"
          />
          <div className="matrix-visual" aria-label="Matriz cenário por variantes por repetições">
            <div className="matrix-visual__axis matrix-visual__axis--scenario">
              <FileMagnifyingGlass aria-hidden="true" size={18} />
              <span>Cenário</span>
              <strong className="mono">deployment-log-trace</strong>
            </div>
            <ArrowRight aria-hidden="true" className="matrix-visual__arrow" size={18} />
            <div className="matrix-visual__variants">
              <div><span>Variante</span><strong className="mono">summary-first</strong><small>repetição 1</small></div>
              <div><span>Variante</span><strong className="mono">evidence-first</strong><small>repetição 1</small></div>
            </div>
          </div>
        </section>
      </div>

      <section className="compile-section">
        <SectionHeader
          action={<StatusLabel status="complete">2 RunSpecs compilados</StatusLabel>}
          description="StudyRevision e RunSpec permanecem records distintos."
          title="Compile preview"
        />
        <div className="compile-preview">
          <div className="compile-preview__code">
            <header><GridFour aria-hidden="true" size={17} /> Saída determinística</header>
            <pre>{`scenario: deployment-log-trace\nvariants:\n  - summary-first\n  - evidence-first\nrepetitions: 1\nmax_wall_seconds: 90\nstop_condition: goal_complete`}</pre>
          </div>
          <dl className="compile-preview__summary">
            <Definition label="Provider" value="cliproxyapi-local" />
            <Definition label="Model" value="deepseek-v4-flash" mono />
            <Definition label="Reasoning" value="max" mono />
            <Definition label="Disclosure" value="none" mono />
          </dl>
        </div>
      </section>

      <section className="admission-section">
        <SectionHeader
          action={
            <SegmentedControl
              compact
              label="Demonstração de decisão da Admission"
              onChange={(value) => {
                setAdmissionState(value);
                setEnqueueMessage("");
              }}
              options={[
                { value: "admitted", label: "Admitida" },
                { value: "rejected", label: "Rejeitada" },
              ]}
              value={admissionState}
            />
          }
          description="Preflight automático do stub. Nenhuma decisão humana é alegada."
          title="Admission por RunSpec"
        />

        <div className="admission-table">
          {runSpecs.map((spec, index) => (
            <article className="admission-row" key={spec.id}>
              <div className="admission-row__identity">
                {admissionState === "admitted" ? (
                  <ShieldCheck aria-hidden="true" size={22} weight="duotone" />
                ) : (
                  <ShieldWarning aria-hidden="true" size={22} weight="duotone" />
                )}
                <div><strong>{spec.variant}</strong><span className="mono">{spec.id}</span></div>
              </div>
              <dl>
                <Definition label="Capabilities" value={admissionState === "admitted" ? "compatíveis" : index === 0 ? "read_text indisponível" : "disclosure incompatível"} />
                <Definition label="Interaction" value="1" mono />
                <Definition label="Capture" value={spec.capture} mono />
              </dl>
              <StatusLabel status={admissionState}>{admissionState === "admitted" ? "Admitted" : "Rejected"}</StatusLabel>
            </article>
          ))}
        </div>

        <div className={`admission-gate admission-gate--${admissionState}`} aria-live="polite">
          <div>
            {admissionState === "admitted" ? <ShieldCheck aria-hidden="true" size={20} /> : <ShieldWarning aria-hidden="true" size={20} />}
            <p>
              <strong>{admissionState === "admitted" ? "Gate liberado para este stub" : "Enqueue bloqueado"}</strong>
              <span>
                {admissionState === "admitted"
                  ? "Cada RunSpec exato possui um AdmissionRecord admitido antes de qualquer Run."
                  : "Capability obrigatória ausente ou disclosure não executável. Corrija o draft e compile novos RunSpecs."}
              </span>
            </p>
          </div>
          <button
            className="primary-button"
            disabled={admissionState === "rejected"}
            onClick={() => setEnqueueMessage("Fila de demonstração preparada para 2 RunSpecs admitidos.")}
            type="button"
          >
            <PlayCircle aria-hidden="true" size={18} weight="fill" /> Enqueue Stub
          </button>
        </div>
        {enqueueMessage ? (
          <div className="inline-confirmation" role="status">
            <Check aria-hidden="true" size={16} />
            {enqueueMessage}
            <button onClick={() => navigate("runs")} type="button">Abrir Runs</button>
          </div>
        ) : null}
      </section>
    </div>
  );
}
