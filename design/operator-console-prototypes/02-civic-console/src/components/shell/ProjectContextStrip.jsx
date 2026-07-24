import {
  CalendarBlank,
  CaretDown,
  Code,
  FolderOpen,
  Notebook,
  Plugs,
  ShieldCheck,
} from "@phosphor-icons/react";
import { studyContext } from "../../data/mockData.js";

export function ProjectContextStrip({ project }) {
  return (
    <header className="context-strip">
      <div className="context-primary">
        <div className="context-item context-project">
          <FolderOpen aria-hidden="true" size={18} />
          <span className="context-label">Project</span>
          <strong>{project.name}</strong>
        </div>
        <div className="context-item context-study">
          <Notebook aria-hidden="true" size={18} />
          <span className="context-label">Estudo</span>
          <span>{project.study}</span>
        </div>
      </div>

      <div className="context-meta">
        <div className="context-item context-scenario">
          <Code aria-hidden="true" size={18} />
          <span className="mono">{project.scenario ?? "Sem cenário ativo"}</span>
        </div>
        <div className="context-item context-demo">
          <ShieldCheck aria-hidden="true" size={18} />
          <span>Demonstração local</span>
        </div>
        <div className="context-item context-date">
          <CalendarBlank aria-hidden="true" size={18} />
          <span>{studyContext.date}</span>
        </div>
        <details className="context-disclosure">
          <summary>
            <Plugs aria-hidden="true" size={18} />
            <span>Prontidão do sistema</span>
            <CaretDown aria-hidden="true" className="summary-caret" size={14} />
          </summary>
          <div className="context-popover">
            <strong>Stub determinístico local</strong>
            <span>Sem provider, persistência externa ou autoridade humana.</span>
            <span>Workspace: Integration pending.</span>
          </div>
        </details>
      </div>
    </header>
  );
}
