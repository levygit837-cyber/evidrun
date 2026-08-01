import { useEffect, useMemo, useState } from "react";
import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  CirclePlus,
  FlaskConical,
  Hexagon,
  type LucideIcon,
} from "lucide-react";
import { api } from "../api/client";
import { navigationAreas } from "../productLanguage";
import { useBackendRuntime } from "./BackendRuntimeProvider";
import { RuntimeAlert } from "./RuntimeAlert";
import { planeTone } from "./runtimeStatus";
import { Button, StatusIndicator } from "../ui/primitives";

const routeIcons: Record<string, LucideIcon> = {
  "/create": CirclePlus,
  "/laboratory": FlaskConical,
  "/observability": Activity,
};

export function AppShell() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const { state: backendState, executor, restart, restartExecutor } = useBackendRuntime();
  const provider = useQuery({
    queryKey: ["provider", "default"],
    queryFn: api.defaultProvider,
    enabled: backendState.status === "ready",
  });
  const [platform, setPlatform] = useState(() =>
    navigator.userAgent.includes("Mac") ? "darwin" : "browser",
  );

  useEffect(() => {
    void window.evidrunDesktop?.getAppInfo().then((info) => setPlatform(info.platform));
  }, []);

  // Two planes, two tones. ADR 0002 and ADR 0014 keep them apart because the failures differ:
  // a dead executor stalls the queue while evidence stays readable, a dead backend takes
  // reading away. Collapsing them into one health light would hide which happened.
  const controlTone = useMemo(() => planeTone(backendState.status), [backendState.status]);
  const executionTone = useMemo(() => planeTone(executor.status), [executor.status]);
  const RouteIcon = routeIcons[pathname] ?? Hexagon;
  const routeName = navigationAreas[pathname as keyof typeof navigationAreas] ?? "Evidrun";

  return (
    <div className={`app-shell platform-${platform}`}>
      <a className="app-skip-link" href="#main-content">Skip to Main Content</a>
      <aside className="app-sidebar" aria-label="Navegação principal">
        <div className="app-brand">
          <Hexagon aria-hidden="true" size={16} fill="currentColor" />
          <strong>EVIDRUN</strong>
        </div>

        <div className="sidebar-label">Áreas</div>
        <nav className="sidebar-nav">
          <Link
            to="/create"
            aria-label={navigationAreas["/create"]}
            title={navigationAreas["/create"]}
            data-tooltip={navigationAreas["/create"]}
            activeProps={{ className: "active" }}
          >
            <CirclePlus aria-hidden="true" size={16} />
            <span>{navigationAreas["/create"]}</span>
          </Link>
          <Link
            to="/laboratory"
            aria-label={navigationAreas["/laboratory"]}
            title={navigationAreas["/laboratory"]}
            data-tooltip={navigationAreas["/laboratory"]}
            activeProps={{ className: "active" }}
          >
            <FlaskConical aria-hidden="true" size={16} />
            <span>{navigationAreas["/laboratory"]}</span>
          </Link>
          <Link
            to="/observability"
            aria-label={navigationAreas["/observability"]}
            title={navigationAreas["/observability"]}
            data-tooltip={navigationAreas["/observability"]}
            activeProps={{ className: "active" }}
          >
            <Activity aria-hidden="true" size={16} />
            <span>{navigationAreas["/observability"]}</span>
          </Link>
        </nav>

        <div className="sidebar-project">
          <span className="sidebar-label">Projeto</span>
          <div
            className="sidebar-project-current"
            aria-label="Projeto atual: Context Reliability Lab"
          >
            Context Reliability Lab
          </div>
        </div>

        <div className="sidebar-system">
          <span className="sidebar-label">Sistema</span>
          <dl>
            <div>
              <dt>Provider</dt>
              <dd title={provider.data?.id}>{provider.data?.id ?? "indisponível"}</dd>
            </div>
            <div>
              <dt>Authority</dt>
              <dd className="text-danger">indisponível</dd>
            </div>
            {/* `aria-label` rather than `title`: a title on a non-interactive element is not
                reachable by keyboard or touch, and the short visible labels need the context. */}
            <div>
              <dt aria-label="Control Plane, a API local">Control</dt>
              <dd>
                <StatusIndicator shape="glyph" tone={controlTone} label={backendState.status} />
              </dd>
            </div>
            <div>
              <dt aria-label="Execution Plane, o executor durável de Runs">Execution</dt>
              <dd>
                <StatusIndicator shape="glyph" tone={executionTone} label={executor.status} />
              </dd>
            </div>
          </dl>
        </div>

        <footer className="sidebar-footer">
          {backendState.status === "failed" ? (
            <Button variant="quiet" size="small" onClick={() => void restart()}>
              Reiniciar backend
            </Button>
          ) : null}
          {backendState.status !== "failed" && executor.status === "failed" ? (
            <Button variant="quiet" size="small" onClick={() => void restartExecutor()}>
              Reiniciar executor
            </Button>
          ) : null}
          <span>Evidrun desktop · local-first</span>
        </footer>
      </aside>

      <section className="app-main">
        <header className="app-topbar">
          <div className="topbar-context">
            <RouteIcon aria-hidden="true" size={15} />
            <strong>{routeName}</strong>
          </div>
          <div className="topbar-runtime">
            <StatusIndicator shape="glyph" tone={controlTone} label={`Control ${backendState.status}`} />
            <StatusIndicator shape="glyph" tone={executionTone} label={`Execution ${executor.status}`} />
            <span className="topbar-separator" aria-hidden="true" />
            <code>{provider.data?.model ?? "provider pendente"}</code>
          </div>
        </header>
        <main className="app-workspace" id="main-content">
          <RuntimeAlert />
          <Outlet />
        </main>
      </section>
    </div>
  );
}
