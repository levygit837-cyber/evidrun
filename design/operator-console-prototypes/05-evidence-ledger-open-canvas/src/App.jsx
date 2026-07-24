import { useCallback, useEffect, useMemo, useState } from "react";
import { X } from "@phosphor-icons/react";
import { AppShell } from "./components/shell/AppShell.jsx";
import { AdaptiveChat } from "./components/chat/AdaptiveChat.jsx";
import { IconButton } from "./components/primitives/Controls.jsx";
import { LabRoute } from "./routes/LabRoute.jsx";
import { ProjectsRoute } from "./routes/ProjectsRoute.jsx";
import { StudyRoute } from "./routes/StudyRoute.jsx";
import { RunsRoute } from "./routes/RunsRoute.jsx";
import { PROJECTS } from "./data/mockData.js";

const VALID_PATHS = new Set(["/", "/projects", "/study", "/runs"]);

function normalizePath(pathname) {
  const path = pathname.length > 1 ? pathname.replace(/\/$/, "") : pathname;
  return VALID_PATHS.has(path) ? path : "/";
}

function routeContext(path, project) {
  if (path === "/") return `Project / ${project.name} · Lab`;
  if (path === "/projects") return `Project / ${project.name}`;
  if (path === "/study") return project.id === "crl" ? "Fixture CRL-CTX-002 / Study" : `Project / ${project.name} · sem Study`;
  return project.id === "crl" ? "Fixture CRL-CTX-002 / Run" : `Project / ${project.name} · sem Run`;
}

function scopeDescription(project) {
  if (project.id === "crl") return "Posso discutir este Project, a Study, a Run selecionada e suas referências. O Chat não entra no SubjectEnvelope.";
  return `${project.name} não possui Study, Run ou evidência registrada. A fixture CRL-CTX-002 permanece separada deste Project.`;
}

function focusRouteStart() {
  requestAnimationFrame(() => {
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    document.getElementById("main-content")?.focus({ preventScroll: true });
  });
}

export function App() {
  const [path, setPath] = useState(() => normalizePath(window.location.pathname));
  const [routeState, setRouteState] = useState(() => window.history.state ?? {});
  const [projects, setProjects] = useState(PROJECTS);
  const [project, setProject] = useState("crl");
  const [chatOpen, setChatOpen] = useState(false);
  const [toast, setToast] = useState("");
  const currentProject = projects.find((item) => item.id === project) ?? projects[0];

  useEffect(() => {
    const onPopState = (event) => {
      setPath(normalizePath(window.location.pathname));
      setRouteState(event.state ?? {});
      focusRouteStart();
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const timeout = setTimeout(() => setToast(""), 3400);
    return () => clearTimeout(timeout);
  }, [toast]);

  const navigate = useCallback((nextPath, state = {}) => {
    const normalized = normalizePath(nextPath);
    if (window.location.pathname !== normalized || JSON.stringify(window.history.state) !== JSON.stringify(state)) {
      window.history.pushState(state, "", normalized);
    }
    setPath(normalized);
    setRouteState(state);
    focusRouteStart();
  }, []);

  const addProject = (newProject) => {
    const id = `project-${Date.now()}`;
    setProjects((current) => [...current, { id, ...newProject, status: "Draft local" }]);
    setProject(id);
    setToast("Project criado apenas no estado local deste protótipo.");
  };

  const route = useMemo(() => {
    if (path === "/projects") return <ProjectsRoute projects={projects} project={project} onProjectChange={setProject} onAddProject={addProject} navigate={navigate} onOpenChat={() => setChatOpen(true)} />;
    if (path === "/study") return <StudyRoute key={routeState.newRevision ? "new" : "existing"} initialNewRevision={Boolean(routeState.newRevision)} onOpenChat={() => setChatOpen(true)} navigate={navigate} project={currentProject} onSelectFixture={() => setProject("crl")} />;
    if (path === "/runs") return <RunsRoute onOpenChat={() => setChatOpen(true)} navigate={navigate} project={currentProject} onSelectFixture={() => setProject("crl")} />;
    return <LabRoute navigate={navigate} onOpenChat={() => setChatOpen(true)} project={currentProject} />;
  }, [path, project, projects, currentProject, navigate, routeState.newRevision]);

  return (
    <>
      <a className="skip-link" href="#main-content">Pular para o conteúdo</a>
      <AppShell
        path={path}
        navigate={navigate}
        project={project}
        projects={projects}
        onProjectChange={setProject}
        onUtility={setToast}
        onOpenChat={() => setChatOpen(true)}
        chatOpen={chatOpen}
      >
        {route}
      </AppShell>

      <AdaptiveChat open={chatOpen} onOpenChange={setChatOpen} routeContext={routeContext(path, currentProject)} scopeKey={currentProject.id} scopeDescription={scopeDescription(currentProject)} />

      {toast ? (
        <div className="toast" role="status">
          <span>{toast}</span>
          <IconButton label="Fechar aviso" icon={X} onClick={() => setToast("")} />
        </div>
      ) : null}
    </>
  );
}
