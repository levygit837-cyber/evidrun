import { useCallback, useEffect, useMemo, useState } from "react";
import { AdaptiveChatDock } from "./components/chat/AdaptiveChatDock.jsx";
import { ProjectScopeLock } from "./components/primitives/ProjectScopeLock.jsx";
import { OperatorShell } from "./components/shell/OperatorShell.jsx";
import {
  initialProjects,
  initialRevisions,
  studyContext,
} from "./data/mockData.js";
import { LabRoute } from "./routes/LabRoute.jsx";
import { ProjectsRoute } from "./routes/ProjectsRoute.jsx";
import { RunsRoute } from "./routes/RunsRoute.jsx";
import { StudyRoute } from "./routes/StudyRoute.jsx";
import {
  agentReducer,
  emptyAgentState,
  initialAgentState,
} from "./state/agentReducer.js";

const validPaths = new Set(["/", "/projects", "/study", "/runs"]);
const primaryProjectId = initialProjects[0].id;
const emptyComposerState = { value: "", sourceSelected: false };

function normalizePath(pathname) {
  const clean = pathname.replace(/\/+$/, "") || "/";
  return validPaths.has(clean) ? clean : "/";
}

function useHistoryRoute() {
  const [path, setPath] = useState(() => normalizePath(window.location.pathname));

  useEffect(() => {
    const handlePopState = () => setPath(normalizePath(window.location.pathname));
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback(
    (nextPath) => {
      const normalized = normalizePath(nextPath);
      if (normalized === path) return;
      window.history.pushState({}, "", normalized);
      setPath(normalized);
      window.requestAnimationFrame(() => {
        document.getElementById("main-content")?.focus({ preventScroll: true });
      });
    },
    [path],
  );

  return [path, navigate];
}

export function App() {
  const [path, navigate] = useHistoryRoute();
  const [projects, setProjects] = useState(initialProjects);
  const [currentProjectId, setCurrentProjectId] = useState(initialProjects[0].id);
  const [revisions, setRevisions] = useState(initialRevisions);
  const [activeRevisionId, setActiveRevisionId] = useState(initialRevisions[0].id);
  const [chatState, setChatState] = useState("dock");
  const [agentStatesByProject, setAgentStatesByProject] = useState(() => ({
    [primaryProjectId]: initialAgentState,
  }));
  const [composerStatesByProject, setComposerStatesByProject] = useState(() => ({
    [primaryProjectId]: emptyComposerState,
  }));

  const currentProject =
    projects.find((project) => project.id === currentProjectId) ?? projects[0];
  const activeRevision =
    revisions.find((revision) => revision.id === activeRevisionId) ?? revisions[0];
  const hasCurrentFixture = currentProject.hasRuntimeFixture === true;
  const currentAgentState =
    agentStatesByProject[currentProjectId] ??
    (hasCurrentFixture ? initialAgentState : emptyAgentState);
  const currentComposerState =
    composerStatesByProject[currentProjectId] ?? emptyComposerState;

  const dispatchAgent = useCallback(
    (action) => {
      setAgentStatesByProject((current) => {
        const base =
          current[currentProjectId] ??
          (hasCurrentFixture ? initialAgentState : emptyAgentState);
        return {
          ...current,
          [currentProjectId]: agentReducer(base, action),
        };
      });
    },
    [currentProjectId, hasCurrentFixture],
  );

  const updateComposerState = useCallback(
    (patch) => {
      setComposerStatesByProject((current) => ({
        ...current,
        [currentProjectId]: {
          ...emptyComposerState,
          ...current[currentProjectId],
          ...patch,
        },
      }));
    },
    [currentProjectId],
  );

  const createLocalRevision = useCallback(() => {
    setRevisions((current) => {
      const existing = current.find((revision) => revision.id === "REV-STUB-L03");
      if (existing) return current;
      return [
        {
          id: "REV-STUB-L03",
          label: "Revisão local 3",
          objective:
            "Identificar respostas sem cobertura e exigir referências autorizadas antes da admissão.",
          sourceCoverage: true,
          compiled: false,
          admission: "pending",
          isLocal: true,
        },
        ...current,
      ];
    });
    setActiveRevisionId("REV-STUB-L03");
    navigate("/study");
  }, [navigate]);

  const updateActiveRevision = useCallback(
    (patch) => {
      setRevisions((current) =>
        current.map((revision) =>
          revision.id === activeRevisionId ? { ...revision, ...patch } : revision,
        ),
      );
    },
    [activeRevisionId],
  );

  const compileActiveRevision = useCallback(() => {
    setRevisions((current) =>
      current.map((revision) =>
        revision.id === activeRevisionId
          ? {
              ...revision,
              compiled: true,
              admission: revision.sourceCoverage ? "admitted" : "rejected",
            }
          : revision,
      ),
    );
  }, [activeRevisionId]);

  const route = useMemo(() => {
    if (path === "/projects") {
      return (
        <ProjectsRoute
          projects={projects}
          currentProjectId={currentProjectId}
          onSelectProject={setCurrentProjectId}
          onCreateProject={({ name, intent }) => {
            const project = {
              id: `project-local-${projects.length + 1}`,
              name,
              intent,
              study: "Study ainda não criada",
              scenario: null,
              hasRuntimeFixture: false,
              stage: "intent",
              nextAction: "Escrever a primeira StudyRevision.",
            };
            setProjects((current) => [...current, project]);
            setCurrentProjectId(project.id);
          }}
        />
      );
    }

    if (!hasCurrentFixture) {
      const surface = path === "/study" ? "Study" : path === "/runs" ? "Runs" : "Lab";
      return (
        <ProjectScopeLock
          project={currentProject}
          surface={surface}
          onNavigate={navigate}
        />
      );
    }

    if (path === "/study") {
      return (
        <StudyRoute
          revisions={revisions}
          activeRevision={activeRevision}
          onSelectRevision={setActiveRevisionId}
          onUpdateRevision={updateActiveRevision}
          onCreateRevision={createLocalRevision}
          onCompile={compileActiveRevision}
          onNavigate={navigate}
        />
      );
    }

    if (path === "/runs") {
      return (
        <RunsRoute
          canStart={activeRevision.admission === "admitted"}
          activeRevision={activeRevision}
        />
      );
    }

    return (
      <LabRoute
        project={currentProject}
        activeRevision={activeRevision}
        onCorrectRevision={createLocalRevision}
        onNavigate={navigate}
        agentState={currentAgentState}
        onAgentDispatch={dispatchAgent}
        composerState={currentComposerState}
        onComposerStateChange={updateComposerState}
      />
    );
  }, [
    activeRevision,
    compileActiveRevision,
    createLocalRevision,
    currentAgentState,
    currentComposerState,
    currentProject,
    currentProjectId,
    dispatchAgent,
    hasCurrentFixture,
    navigate,
    path,
    projects,
    revisions,
    updateActiveRevision,
    updateComposerState,
  ]);

  return (
    <OperatorShell
      currentPath={path}
      onNavigate={navigate}
      project={currentProject}
      chat={
        <AdaptiveChatDock
          state={chatState}
          onStateChange={setChatState}
          messages={currentAgentState.messages}
          projectName={currentProject.name}
        />
      }
    >
      {route}
    </OperatorShell>
  );
}
