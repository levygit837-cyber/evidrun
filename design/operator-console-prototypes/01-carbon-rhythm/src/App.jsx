import { useEffect, useMemo, useReducer } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { OperatorContext } from "./context/OperatorContext.jsx";
import { RouterProvider, useRouter } from "./context/RouterContext.jsx";
import { OperatorShell } from "./components/OperatorShell.jsx";
import { LabRoute } from "./routes/LabRoute.jsx";
import { ProjectsRoute } from "./routes/ProjectsRoute.jsx";
import { StudyRoute } from "./routes/StudyRoute.jsx";
import { RunsRoute } from "./routes/RunsRoute.jsx";
import {
  createInitialState,
  operatorReducer,
  selectCurrentAgent,
  selectCurrentProject,
  selectCurrentRun,
  selectCurrentStudy,
} from "./state/operatorState.js";

const routeComponents = {
  "/": LabRoute,
  "/projects": ProjectsRoute,
  "/study": StudyRoute,
  "/runs": RunsRoute,
};

function RoutedConsole() {
  const { path, navigate } = useRouter();
  const [state, dispatch] = useReducer(operatorReducer, undefined, createInitialState);
  const reduceMotion = useReducedMotion();
  const Route = routeComponents[path] ?? LabRoute;
  const agent = selectCurrentAgent(state);
  const study = selectCurrentStudy(state);
  const run = selectCurrentRun(state);
  const currentProject = selectCurrentProject(state);

  useEffect(() => {
    if (!routeComponents[path]) navigate("/", { replace: true });
  }, [navigate, path]);

  useEffect(() => {
    if (agent?.status !== "running" || !agent.auto) return undefined;
    const timer = window.setTimeout(() => dispatch({ type: "AGENT_ADVANCE" }), 260);
    return () => window.clearTimeout(timer);
  }, [agent?.activityCount, agent?.auto, agent?.status]);

  useEffect(() => {
    if (!run?.auto) return undefined;
    const timer = window.setTimeout(() => dispatch({ type: "RUN_ADVANCE" }), 320);
    return () => window.clearTimeout(timer);
  }, [run?.auto, run?.phaseIndex]);

  const contextValue = useMemo(
    () => ({
      state: {
        ...state,
        agent,
        study,
        run,
        currentProject,
      },
      dispatch,
    }),
    [agent, currentProject, run, state, study],
  );

  return (
    <OperatorContext.Provider value={contextValue}>
      <OperatorShell>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={path}
            className="route-motion"
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? { opacity: 1 } : { opacity: 0, y: -5 }}
            transition={{ duration: reduceMotion ? 0 : 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            <Route />
          </motion.div>
        </AnimatePresence>
      </OperatorShell>
    </OperatorContext.Provider>
  );
}

export function App() {
  return (
    <RouterProvider>
      <RoutedConsole />
    </RouterProvider>
  );
}
