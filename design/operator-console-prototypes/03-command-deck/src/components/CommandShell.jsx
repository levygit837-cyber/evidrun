import {
  BoundingBox,
  CaretDown,
  ChatCenteredDots,
  FileMagnifyingGlass,
  Folder,
  Notebook,
  PlayCircle,
} from "@phosphor-icons/react";
import { routeItems } from "../data/mockData.js";
import { LocalDataFlag } from "./ui.jsx";

const routeIcons = {
  lab: ChatCenteredDots,
  projects: Folder,
  study: Notebook,
  runs: PlayCircle,
};

function RouteLink({ item, active, onNavigate, mobile = false }) {
  const Icon = routeIcons[item.id];
  return (
    <a
      aria-label={item.label}
      aria-current={active ? "page" : undefined}
      className={mobile ? "mobile-nav__link" : "command-nav__link"}
      data-active={active}
      href={`#/${item.id}`}
      onClick={() => onNavigate(item.id)}
      title={item.label}
    >
      <Icon aria-hidden="true" size={mobile ? 21 : 18} weight={active ? "fill" : "regular"} />
      <span>{item.label}</span>
    </a>
  );
}

export function CommandShell({ children, route, navigate, projects, projectLocked, selectedProjectId, onProjectChange }) {
  return (
    <div className="app-shell">
      <header className="command-bar">
        <a className="brand-lockup" href="#/lab" onClick={() => navigate("lab")} aria-label="Command Deck, ir para Lab">
          <span className="brand-lockup__mark" aria-hidden="true">
            <BoundingBox size={20} weight="duotone" />
          </span>
          <span className="brand-lockup__name">Command Deck</span>
        </a>

        <div className="project-switcher">
          <FileMagnifyingGlass aria-hidden="true" size={16} />
          <label htmlFor="global-project">Project</label>
          <span className="project-switcher__control">
            <select
              disabled={projectLocked}
              id="global-project"
              title={projectLocked ? "Study e Runs estão vinculados ao Project Release Integrity nesta demonstração" : undefined}
              value={selectedProjectId}
              onChange={(event) => onProjectChange(event.target.value)}
            >
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            <CaretDown aria-hidden="true" size={12} />
          </span>
        </div>

        <nav className="command-nav" aria-label="Navegação principal">
          {routeItems.map((item) => (
            <RouteLink
              active={route === item.id}
              item={item}
              key={item.id}
              onNavigate={navigate}
            />
          ))}
        </nav>

        <LocalDataFlag compact />
      </header>

      {children}

      <nav className="mobile-nav" aria-label="Navegação principal móvel">
        {routeItems.map((item) => (
          <RouteLink
            active={route === item.id}
            item={item}
            key={item.id}
            mobile
            onNavigate={navigate}
          />
        ))}
      </nav>
    </div>
  );
}
