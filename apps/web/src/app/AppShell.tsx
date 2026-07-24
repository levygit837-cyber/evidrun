import { useEffect, useMemo, useState } from "react";
import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ChevronDown,
  CirclePlus,
  FlaskConical,
  Hexagon,
  RadioTower,
} from "lucide-react";
import { api } from "../api/client";
import { useBackendRuntime } from "./BackendRuntimeProvider";
import { Button, StatusIndicator } from "../ui/primitives";

const routeNames: Record<string, string> = {
  "/laboratory": "Laboratory",
  "/create": "Create",
  "/observability": "Observability",
};

export function AppShell() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const { state: backendState, restart } = useBackendRuntime();
  const provider = useQuery({
    queryKey: ["provider", "default"],
    queryFn: api.defaultProvider,
    enabled: backendState.status === "ready",
  });
  const [platform, setPlatform] = useState("browser");

  useEffect(() => {
    void window.evidrunDesktop?.getAppInfo().then((info) => setPlatform(info.platform));
  }, []);

  const healthTone = useMemo(() => {
    if (backendState.status === "ready") return "success" as const;
    if (backendState.status === "failed") return "danger" as const;
    return "warning" as const;
  }, [backendState.status]);

  return (
    <div className={`app-shell platform-${platform}`}>
      <aside className="app-sidebar" aria-label="Navegação principal">
        <div className="app-brand">
          <Hexagon aria-hidden="true" size={16} fill="currentColor" />
          <strong>EVIDRUN</strong>
        </div>

        <div className="sidebar-label">Áreas</div>
        <nav className="sidebar-nav">
          <Link to="/create" activeProps={{ className: "active" }}>
            <CirclePlus aria-hidden="true" size={16} />
            <span>Create</span>
          </Link>
          <Link to="/laboratory" activeProps={{ className: "active" }}>
            <FlaskConical aria-hidden="true" size={16} />
            <span>Laboratory</span>
          </Link>
          <Link to="/observability" activeProps={{ className: "active" }}>
            <Activity aria-hidden="true" size={16} />
            <span>Observability</span>
          </Link>
        </nav>

        <div className="sidebar-project">
          <span className="sidebar-label">Projeto</span>
          <button type="button" aria-label="Projeto atual">
            <span>Context Reliability Lab</span>
            <ChevronDown aria-hidden="true" size={14} />
          </button>
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
            <div>
              <dt>Health</dt>
              <dd>
                <StatusIndicator tone={healthTone} label={backendState.status} />
              </dd>
            </div>
          </dl>
        </div>

        <footer className="sidebar-footer">
          {backendState.status === "failed" ? (
            <Button variant="quiet" size="small" onClick={() => void restart()}>
              Tentar novamente
            </Button>
          ) : null}
          <span>Evidrun desktop · local-first</span>
        </footer>
      </aside>

      <section className="app-main">
        <header className="app-topbar">
          <div className="topbar-context">
            <RadioTower aria-hidden="true" size={15} />
            <strong>{routeNames[pathname] ?? "Evidrun"}</strong>
          </div>
          <div className="topbar-runtime">
            <StatusIndicator tone={healthTone} label={`Backend ${backendState.status}`} />
            <span className="topbar-separator" aria-hidden="true" />
            <code>{provider.data?.model ?? "provider pendente"}</code>
          </div>
        </header>
        <main className="app-workspace">
          <Outlet />
        </main>
      </section>
    </div>
  );
}
