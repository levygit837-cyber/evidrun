import {
  CaretDown,
  CheckCircle,
  Flask,
  FolderSimple,
  Folders,
  Notebook,
  PlayCircle,
  Selection,
} from "@phosphor-icons/react";
import { ROUTES, STUB_DATE, STUB_TIMEZONE } from "../data/mockData.js";
import { useOperator } from "../context/OperatorContext.jsx";
import { RouteLink } from "../context/RouterContext.jsx";

const mobileIcons = {
  "/": Flask,
  "/projects": Folders,
  "/study": Notebook,
  "/runs": PlayCircle,
};

export function CommandRail() {
  const { state, dispatch } = useOperator();

  return (
    <>
      <header className="command-rail">
        <RouteLink to="/" className="brand-lockup" aria-label="EvidRun, ir ao Lab">
          <span className="brand-lockup__mark" aria-hidden="true">
            <Selection size={29} weight="regular" />
          </span>
          <span className="brand-lockup__name">EvidRun</span>
          <span className="brand-lockup__product">Operator Console</span>
        </RouteLink>

        <nav className="desktop-nav" aria-label="Navegação principal">
          {ROUTES.map((route) => (
            <RouteLink
              key={route.path}
              to={route.path}
              className="desktop-nav__link"
              activeClassName="is-active"
            >
              {route.label}
            </RouteLink>
          ))}
        </nav>

        <label className="project-switcher">
          <span className="sr-only">Project atual</span>
          <FolderSimple size={19} aria-hidden="true" />
          <select
            aria-label="Trocar Project"
            value={state.currentProjectId}
            onChange={(event) =>
              dispatch({ type: "PROJECT_SELECT", projectId: event.target.value })
            }
          >
            {state.projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
          <CaretDown size={15} aria-hidden="true" />
        </label>

        <details className="system-readiness">
          <summary>
            <CheckCircle size={17} weight="bold" aria-hidden="true" />
            <span>Stub local pronto</span>
          </summary>
          <div className="system-readiness__panel">
            <strong>Demonstração determinística</strong>
            <span>{STUB_DATE}</span>
            <span>{STUB_TIMEZONE}</span>
            <span>Sem provider, credencial ou efeito externo.</span>
          </div>
        </details>
      </header>

      <nav className="mobile-nav" aria-label="Navegação principal móvel">
        {ROUTES.map((route) => {
          const Icon = mobileIcons[route.path];
          return (
            <RouteLink
              key={route.path}
              to={route.path}
              className="mobile-nav__link"
              activeClassName="is-active"
            >
              <Icon size={21} aria-hidden="true" />
              <span>{route.shortLabel}</span>
            </RouteLink>
          );
        })}
      </nav>
    </>
  );
}
