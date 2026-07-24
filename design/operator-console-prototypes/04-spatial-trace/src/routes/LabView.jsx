import { ArrowRight, BoundingBox, ChatCircleDots, ShieldCheck } from "@phosphor-icons/react";
import { TracePath } from "../components/TracePath.jsx";

export function LabView({ project, hasBoundStudy, linkProps }) {
  return (
    <div className="route route--lab">
      <header className="page-intro page-intro--lab">
        <div>
          <span className="section-label">Lab</span>
          <h1>Seu experimento continua no mesmo lugar.</h1>
          <p>
            Mova-se do contexto até a evidência sem misturar draft, admissão e execução.
          </p>
        </div>
        <a {...linkProps(hasBoundStudy ? "/study" : "/projects")} className="primary-button">
          {hasBoundStudy ? "Resolver Admission" : "Abrir escopo do Project"}
          <ArrowRight size={17} aria-hidden="true" />
        </a>
      </header>

      <section className="scope-band" aria-label="Resumo do contexto atual">
        <div className="scope-band__scope">
          <BoundingBox size={22} weight="fill" aria-hidden="true" />
          <span>
            <small>Escopo atual</small>
            <strong>{project.name}</strong>
          </span>
        </div>
        <div className="scope-band__workflow">
          <ShieldCheck size={22} weight="fill" aria-hidden="true" />
          <span>
            <small>Workflow ativo</small>
            <strong>{project.study}</strong>
          </span>
        </div>
        <div className="scope-band__next">
          <span>Próxima ação</span>
          <strong>{project.nextAction}</strong>
        </div>
      </section>

      <div className="lab-spatial-grid">
        <section className="lab-trace-surface" aria-labelledby="lab-trace-title">
          <div className="section-heading">
            <div>
              <h2 id="lab-trace-title">Traço ativo</h2>
              <p>O detalhe acompanha somente o estágio em foco.</p>
            </div>
            <span className="stub-stamp">estado stub local</span>
          </div>
          <TracePath activeStage={project.currentStage} linkProps={linkProps} />
        </section>

        <aside className="lab-agent-entry" aria-labelledby="lab-agent-title">
          <ChatCircleDots size={30} weight="duotone" aria-hidden="true" />
          <div>
            <h2 id="lab-agent-title">Lab Agent lateral</h2>
            <p>
              Abra o Chat na borda direita. O thread persiste ao navegar e só cria drafts locais.
            </p>
          </div>
          <span>Composer funcional</span>
        </aside>
      </div>

      <section className="boundary-note" aria-label="Fronteira de autoridade">
        <strong>Fronteira de autoridade</strong>
        <p>
          Texto no Chat não registra aceitação humana e nunca entra no SubjectEnvelope desta demonstração.
        </p>
      </section>
    </div>
  );
}
