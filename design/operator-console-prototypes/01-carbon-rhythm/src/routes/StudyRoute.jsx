import { useMemo, useState } from "react";
import {
  ArrowRight,
  Check,
  FileMagnifyingGlass,
  GitBranch,
  LinkBreak,
  Notebook,
  ShieldCheck,
  ShieldWarning,
  X,
} from "@phosphor-icons/react";
import { useOperator } from "../context/OperatorContext.jsx";
import { useRouter } from "../context/RouterContext.jsx";
import { Button, BoundaryNote, RouteHeading, TechnicalId } from "../components/Primitives.jsx";

function AdmissionRow({ runSpec }) {
  const admitted = runSpec.admission === "admitted";
  const Icon = admitted ? ShieldCheck : ShieldWarning;

  return (
    <article className={`admission-row admission-row--${runSpec.admission}`}>
      <div className="admission-row__icon" aria-hidden="true"><Icon size={23} weight="bold" /></div>
      <div>
        <p>AdmissionRecord · {runSpec.variant}</p>
        <h3>{admitted ? "Admitted" : "Rejected"}</h3>
        <TechnicalId>{runSpec.id}</TechnicalId>
      </div>
      <p className="admission-row__reason">{runSpec.reason}</p>
      <span className="admission-row__shape" aria-label={admitted ? "admitted" : "rejected"}>
        {admitted ? <Check size={18} weight="bold" aria-hidden="true" /> : <X size={18} weight="bold" aria-hidden="true" />}
      </span>
    </article>
  );
}

export function StudyRoute() {
  const { state, dispatch } = useOperator();
  const { navigate } = useRouter();
  const [compiled, setCompiled] = useState(true);
  const revision = state.study?.revisions.find(
    (item) => item.id === state.study.selectedRevisionId,
  );
  const allAdmitted = useMemo(
    () => revision?.runSpecs.every((runSpec) => runSpec.admission === "admitted"),
    [revision],
  );
  const currentProject = state.currentProject;

  if (!state.study) {
    return (
      <div className="route route--study">
        <RouteHeading
          eyebrow="StudyRevision"
          title="Nenhuma Study vinculada"
          description="Este Project não pode compilar RunSpecs ou produzir AdmissionRecords até possuir uma Study vinculada."
        />

        <section className="scope-empty-state" aria-labelledby="study-empty-title">
          <div className="scope-empty-state__icon" aria-hidden="true"><LinkBreak size={25} /></div>
          <div>
            <p>Project selecionado</p>
            <h2 id="study-empty-title"><strong>{currentProject?.name}</strong></h2>
            <span>
              Nenhuma revisão, AdmissionRecord ou identificador do Project Release Integrity é
              reutilizado neste escopo.
            </span>
          </div>
        </section>

        <BoundaryNote tone="warning">
          Fail-closed: sem Study vinculada não há compile, correção, enqueue ou Run.
        </BoundaryNote>
      </div>
    );
  }

  const enqueue = () => {
    if (!allAdmitted) return;
    dispatch({ type: "STUDY_ENQUEUE" });
    navigate("/runs");
  };

  return (
    <div className="route route--study">
      <RouteHeading
        eyebrow="StudyRevision"
        title={state.study.title}
        description="Edite uma revisão local, compile RunSpecs e verifique cada AdmissionRecord antes de enfileirar."
      >
        <label className="revision-select">
          <Notebook size={18} aria-hidden="true" />
          <span className="sr-only">Revisão ativa</span>
          <select
            aria-label="Selecionar StudyRevision"
            value={state.study.selectedRevisionId}
            onChange={(event) =>
              dispatch({ type: "STUDY_SELECT_REVISION", revisionId: event.target.value })
            }
          >
            {state.study.revisions.map((item) => (
              <option key={item.id} value={item.id}>{item.label} · {item.status}</option>
            ))}
          </select>
        </label>
      </RouteHeading>

      <BoundaryNote>
        StudyRevision e RunSpec são registros distintos. O Lab Agent não fornece aceitação humana.
      </BoundaryNote>

      <div className="study-layout">
        <section className="revision-editor" aria-labelledby="revision-editor-title">
          <header className="section-heading-inline">
            <div>
              <p>Draft editor stub</p>
              <h2 id="revision-editor-title">{revision?.label}</h2>
            </div>
            <TechnicalId>{revision?.id}</TechnicalId>
          </header>

          <label htmlFor="study-objective">Objective</label>
          <textarea
            id="study-objective"
            rows={5}
            value={revision?.objective ?? ""}
            onChange={(event) =>
              dispatch({ type: "STUDY_UPDATE_OBJECTIVE", objective: event.target.value })
            }
          />
          <p className="field-help">Alterações ficam apenas no estado React deste protótipo.</p>

          <div className="study-formula" aria-label="Cenário vezes variantes vezes repetições">
            <div>
              <span>Cenário</span>
              <TechnicalId>{revision?.scenario}</TechnicalId>
            </div>
            <span aria-hidden="true">×</span>
            <div>
              <span>Variantes</span>
              <strong>{revision?.runSpecs.length}</strong>
              <small>summary-first, evidence-first</small>
            </div>
            <span aria-hidden="true">×</span>
            <div>
              <span>Repetições</span>
              <strong>{revision?.repetitions}</strong>
            </div>
            <ArrowRight size={19} aria-hidden="true" />
            <div className="study-formula__result">
              <span>RunSpecs</span>
              <strong>{(revision?.runSpecs.length ?? 0) * (revision?.repetitions ?? 0)}</strong>
            </div>
          </div>

          <div className="revision-editor__actions">
            <Button variant="secondary" onClick={() => setCompiled(true)}>
              <FileMagnifyingGlass size={18} aria-hidden="true" /> Compilar preview
            </Button>
            {!allAdmitted ? (
              <Button variant="ghost" onClick={() => dispatch({ type: "STUDY_CORRECT_REVISION" })}>
                <GitBranch size={18} aria-hidden="true" /> Criar revisão corrigida
              </Button>
            ) : null}
          </div>
        </section>

        <section className="compile-preview" aria-labelledby="compile-preview-title">
          <header className="section-heading-inline">
            <div>
              <p>Compile preview</p>
              <h2 id="compile-preview-title">Admission por RunSpec</h2>
            </div>
            <span>{compiled ? "Atualizado localmente" : "Aguardando compile"}</span>
          </header>

          {compiled ? (
            <div className="admission-list">
              {revision?.runSpecs.map((runSpec) => (
                <AdmissionRow key={runSpec.id} runSpec={runSpec} />
              ))}
            </div>
          ) : null}

          {!allAdmitted ? (
            <BoundaryNote tone="warning" className="admission-gate-note">
              Enqueue bloqueado: ao menos um RunSpec foi rejeitado. Corrija o disclosure em uma nova revisão.
            </BoundaryNote>
          ) : (
            <BoundaryNote tone="positive" className="admission-gate-note">
              Dois RunSpecs admitidos pelo preflight local. Nenhuma Run foi criada ainda.
            </BoundaryNote>
          )}

          {state.study.notice ? <p className="study-notice" role="status">{state.study.notice}</p> : null}

          <div className="compile-preview__footer">
            <p id="enqueue-reason">
              {allAdmitted
                ? "A próxima ação cria somente Runs stub enfileiradas."
                : "Disponível quando todos os AdmissionRecords estiverem admitted."}
            </p>
            <Button
              variant="primary"
              disabled={!allAdmitted}
              aria-describedby="enqueue-reason"
              onClick={enqueue}
            >
              Enfileirar {revision?.runSpecs.length ?? 0} RunSpecs
              <ArrowRight size={18} aria-hidden="true" />
            </Button>
          </div>
        </section>
      </div>
    </div>
  );
}
