import {
  BookOpen,
  Database,
  FileText,
  FolderOpen,
  House,
  Plus,
  ShieldWarning,
} from "@phosphor-icons/react";
import brandLockup from "../../assets/evidrun-logo.png";
import { Button } from "../primitives/Controls.jsx";

const NAVIGATION = [
  { path: "/", label: "Lab", icon: House },
  { path: "/projects", label: "Projetos", icon: FolderOpen },
  { path: "/study", label: "Study & Admission", icon: FileText },
  { path: "/runs", label: "Runs & Evidence", icon: Database },
];

export function Sidebar({ path, navigate, project, projects, onProjectChange }) {
  return (
    <aside className="sidebar" aria-label="Navegação principal">
      <div className="brand-lockup">
        <img src={brandLockup} alt="EvidRun Operator Console" />
      </div>

      <div className="sidebar__project">
        <label htmlFor="project-switcher">Project</label>
        <select id="project-switcher" value={project} onChange={(event) => onProjectChange(event.target.value)}>
          {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      </div>

      <nav className="sidebar__nav">
        {NAVIGATION.map(({ path: itemPath, label, icon: Icon }) => (
          <button
            type="button"
            key={itemPath}
            className={path === itemPath ? "is-active" : ""}
            aria-current={path === itemPath ? "page" : undefined}
            onClick={() => navigate(itemPath)}
          >
            <Icon aria-hidden="true" size={20} weight="regular" />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <Button variant="primary" icon={Plus} className="sidebar__new-study" onClick={() => navigate("/study", { newRevision: true })}>
        Nova Study
      </Button>

      <section className="system-status" aria-labelledby="system-status-title">
        <div className="system-status__heading">
          <BookOpen size={17} aria-hidden="true" />
          <h2 id="system-status-title">Stub local</h2>
        </div>
        <dl>
          <div><dt>Backend</dt><dd>determinístico</dd></div>
          <div><dt>Worker</dt><dd>simulado</dd></div>
          <div><dt>Provider</dt><dd>não chamado</dd></div>
          <div className="is-unavailable"><dt><ShieldWarning size={15} aria-hidden="true" />Authority</dt><dd>indisponível</dd></div>
        </dl>
      </section>
    </aside>
  );
}

export const mobileNavigation = NAVIGATION;
