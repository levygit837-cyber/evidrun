import { useEffect, useReducer } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { AdaptiveChat } from "./components/AdaptiveChat.jsx";
import { CommandShell } from "./components/CommandShell.jsx";
import { initialProjects } from "./data/mockData.js";
import { useHashRoute } from "./hooks/useHashRoute.js";
import { LabRoute } from "./routes/LabRoute.jsx";
import { ProjectsRoute } from "./routes/ProjectsRoute.jsx";
import { RunsRoute } from "./routes/RunsRoute.jsx";
import { StudyRoute } from "./routes/StudyRoute.jsx";

const initialProjectState = {
  projects: initialProjects,
  selectedProjectId: initialProjects[0].id,
};

function projectReducer(state, action) {
  switch (action.type) {
    case "SELECT_PROJECT":
      return state.projects.some((project) => project.id === action.projectId)
        ? { ...state, selectedProjectId: action.projectId }
        : state;
    case "CREATE_PROJECT": {
      const duplicateCount = state.projects.filter((project) => project.id.startsWith(action.project.id)).length;
      const project = duplicateCount
        ? { ...action.project, id: `${action.project.id}-${duplicateCount + 1}` }
        : action.project;
      return {
        projects: [...state.projects, project],
        selectedProjectId: project.id,
      };
    }
    default:
      return state;
  }
}

function RouteContent({ route, navigate, projectState, dispatchProjects }) {
  if (route === "projects") {
    return (
      <ProjectsRoute
        onCreateProject={(project) => dispatchProjects({ type: "CREATE_PROJECT", project })}
        onProjectChange={(projectId) => dispatchProjects({ type: "SELECT_PROJECT", projectId })}
        projects={projectState.projects}
        selectedProjectId={projectState.selectedProjectId}
      />
    );
  }
  if (route === "study") return <StudyRoute navigate={navigate} />;
  if (route === "runs") return <RunsRoute />;
  return <LabRoute />;
}

export function App() {
  const { route, navigate } = useHashRoute();
  const reduceMotion = useReducedMotion();
  const [projectState, dispatchProjects] = useReducer(projectReducer, initialProjectState);

  useEffect(() => {
    const routeUsesReleaseIntegrity = route === "study" || route === "runs";
    if (routeUsesReleaseIntegrity && projectState.selectedProjectId !== initialProjects[0].id) {
      dispatchProjects({ type: "SELECT_PROJECT", projectId: initialProjects[0].id });
    }
  }, [projectState.selectedProjectId, route]);

  return (
    <CommandShell
      navigate={navigate}
      onProjectChange={(projectId) => dispatchProjects({ type: "SELECT_PROJECT", projectId })}
      projects={projectState.projects}
      projectLocked={route === "study" || route === "runs"}
      route={route}
      selectedProjectId={projectState.selectedProjectId}
    >
      <main className="main-content">
        <AnimatePresence mode="sync" initial={false}>
          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="route-transition"
            exit={reduceMotion ? { opacity: 1 } : { opacity: 0, y: -4 }}
            initial={reduceMotion ? false : { opacity: 0, y: 6 }}
            key={route}
            transition={{ duration: reduceMotion ? 0 : 0.2 }}
          >
            <RouteContent
              dispatchProjects={dispatchProjects}
              navigate={navigate}
              projectState={projectState}
              route={route}
            />
          </motion.div>
        </AnimatePresence>
      </main>
      <AdaptiveChat />
    </CommandShell>
  );
}
