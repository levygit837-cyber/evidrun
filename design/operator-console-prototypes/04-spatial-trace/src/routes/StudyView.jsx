import {
  ArrowRight,
  Check,
  FileLock,
  GitBranch,
  Notebook,
  ShieldCheck,
  Warning,
} from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";

function StudyScopeGate({ project, linkProps }) {
  return (
    <div className="route route--study route--scope-gated">
      <header className="page-intro">
        <div>
          <span className="section-label">Study</span>
          <h1>{project.study}</h1>
          <p>
            Esta projeção acompanha somente o Project {project.name} e falha fechado quando não há records vinculados.
          </p>
        </div>
        <div className="revision-mark">
          <Notebook size={22} weight="duotone" aria-hidden="true" />
          <span>
            <small>{project.currentStage}</small>
            <strong>Sem vínculo compilado</strong>
          </span>
        </div>
      </header>

      <section className="scope-gate" aria-labelledby="study-scope-gate-title">
        <span className="scope-gate__icon" aria-hidden="true">
          <FileLock size={26} weight="duotone" />
        </span>
        <div className="scope-gate__copy">
          <span className="section-label">Project scoped</span>
          <h2 id="study-scope-gate-title">Nenhuma Admission representada para este Project.</h2>
          <p>
            O stub não possui uma StudyRevision compilada ligada a este Project. RunSpecs e AdmissionRecords de outros escopos permanecem fora desta tela.
          </p>
          <dl className="scope-gate__facts">
            <div>
              <dt>Project</dt>
              <dd className="mono">{project.id}</dd>
            </div>
            <div>
              <dt>Study local</dt>
              <dd>{project.study}</dd>
            </div>
            <div>
              <dt>Próximo gate</dt>
              <dd>{project.nextAction}</dd>
            </div>
          </dl>
          <a {...linkProps("/projects")} className="secondary-button">
            Revisar Project
          </a>
        </div>
        <span className="scope-gate__status">Sem records executáveis</span>
      </section>

      <section className="authority-warning" aria-label="Limite de autoridade humana">
        <ShieldCheck size={22} weight="duotone" aria-hidden="true" />
        <p>
          A ausência de vínculo impede enqueue. Este estado não cria autoridade humana nem uma Run implícita.
        </p>
      </section>
    </div>
  );
}

function AdmissionPanel({ variant, corrected, enqueued, onEnqueue, onCorrect }) {
  const admitted = variant.admission.decision === "admitted";
  return (
    <section className={`admission-panel ${admitted ? "is-admitted" : "is-rejected"}`}>
      <header>
        <span className="admission-panel__geometry" aria-hidden="true">
          {admitted ? <Check size={18} weight="bold" /> : <Warning size={18} weight="fill" />}
        </span>
        <div>
          <small>AdmissionRecord</small>
          <strong>{variant.admission.decision}</strong>
        </div>
        <code>{variant.admission.id}</code>
      </header>
      {admitted ? (
        <p>Capabilities representadas e executáveis coincidem neste harness stub.</p>
      ) : (
        <div className="admission-mismatch">
          <strong>{variant.admission.issue}</strong>
          <dl>
            <div>
              <dt>Solicitado</dt>
              <dd>{variant.admission.requested}</dd>
            </div>
            <div>
              <dt>Suportado</dt>
              <dd>{variant.admission.supported}</dd>
            </div>
          </dl>
        </div>
      )}
      <footer>
        {!admitted ? (
          <button type="button" className="secondary-button" onClick={onCorrect}>
            <GitBranch size={17} aria-hidden="true" />
            {corrected ? "Revisão local criada" : "Corrigir em novo draft"}
          </button>
        ) : null}
        <button
          type="button"
          className="primary-button"
          disabled={!admitted || enqueued}
          onClick={onEnqueue}
        >
          {enqueued ? "Adicionada à fila stub" : "Adicionar à fila stub"}
          <ArrowRight size={17} aria-hidden="true" />
        </button>
      </footer>
    </section>
  );
}

export function StudyView({ project, study, linkProps }) {
  const [corrected, setCorrected] = useState(false);
  const [enqueued, setEnqueued] = useState(false);
  const reduceMotion = useReducedMotion();

  if (!study) {
    return <StudyScopeGate project={project} linkProps={linkProps} />;
  }

  return (
    <div className="route route--study">
      <header className="page-intro">
        <div>
          <span className="section-label">Study</span>
          <h1>{study.name}</h1>
          <p>Revise, compile e inspecione a admissão antes de permitir qualquer Run nova.</p>
        </div>
        <div className="revision-mark">
          <Notebook size={22} weight="duotone" aria-hidden="true" />
          <span>
            <small>{study.revision.status}</small>
            <strong>{study.revision.label}</strong>
          </span>
        </div>
      </header>

      <section className="compile-preview" aria-labelledby="compile-title">
        <header>
          <div>
            <span className="section-label">Compile preview</span>
            <h2 id="compile-title">Um scenario abre duas trajetórias.</h2>
          </div>
          <code>{study.scenario}</code>
        </header>
        <div className="compile-equation" aria-label="Scenario multiplicado por variantes e repetições">
          <span>
            <small>scenario</small>
            <strong>1</strong>
          </span>
          <i aria-hidden="true">×</i>
          <span>
            <small>variants</small>
            <strong>{study.variants.length}</strong>
          </span>
          <i aria-hidden="true">×</i>
          <span>
            <small>repetições</small>
            <strong>{study.repetitions}</strong>
          </span>
          <i aria-hidden="true">=</i>
          <span className="compile-equation__result">
            <small>RunSpecs</small>
            <strong>2</strong>
          </span>
        </div>
        <div className="variant-fork">
          <span className="variant-fork__origin" aria-hidden="true">
            <GitBranch size={20} weight="fill" />
          </span>
          {study.variants.map((variant, index) => (
            <motion.article
              key={variant.id}
              className="variant-branch"
              initial={reduceMotion ? false : { opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: reduceMotion ? 0 : index * 0.08 }}
            >
              <header>
                <div>
                  <small>Variant</small>
                  <h3>{variant.name}</h3>
                </div>
                <FileLock size={22} weight="duotone" aria-hidden="true" />
              </header>
              <p>{variant.intent}</p>
              <dl>
                <div>
                  <dt>RunSpec</dt>
                  <dd className="mono">{variant.runSpec.id}</dd>
                </div>
                <div>
                  <dt>max_turns</dt>
                  <dd>{variant.runSpec.maxTurns}</dd>
                </div>
                <div>
                  <dt>capture</dt>
                  <dd>{variant.runSpec.captureMode}</dd>
                </div>
              </dl>
              <AdmissionPanel
                variant={variant}
                corrected={corrected}
                enqueued={enqueued && variant.admission.decision === "admitted"}
                onCorrect={() => setCorrected(true)}
                onEnqueue={() => setEnqueued(true)}
              />
            </motion.article>
          ))}
        </div>
      </section>

      <AnimatePresence>
        {corrected ? (
          <motion.section
            className="draft-correction"
            aria-label="Nova revisão local corrigida"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 5 }}
          >
            <span className="draft-correction__icon" aria-hidden="true">
              <Notebook size={22} weight="fill" />
            </span>
            <div>
              <small>StudyRevision draft local</small>
              <h2>Correção preparada sem reescrever o record rejeitado.</h2>
              <p>
                <code>max_turns: 1</code> substitui o valor incompatível em uma nova revisão ainda não compilada.
              </p>
            </div>
            <span className="draft-correction__status">Pronta para compilar</span>
          </motion.section>
        ) : null}
      </AnimatePresence>

      <section className="authority-warning" aria-label="Limite de autoridade humana">
        <ShieldCheck size={22} weight="duotone" aria-hidden="true" />
        <p>
          Este draft não registra aceitação humana. Autoridade exige um HumanAttestationRecord verificado fora deste protótipo.
        </p>
      </section>
    </div>
  );
}
