import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { invalidateBackendConnection } from "../api/client";
import type { BackendState, ExecutorState } from "../types";

interface BackendRuntimeContextValue {
  state: BackendState;
  /** The Run executor's process state, tracked apart from the backend's. */
  executor: ExecutorState;
  restart(): Promise<void>;
  restartExecutor(): Promise<void>;
}

const BackendRuntimeContext = createContext<BackendRuntimeContextValue | null>(null);

export function BackendRuntimeProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<BackendState>(() => ({
    status: window.evidrunDesktop ? "starting" : "ready",
  }));
  // Outside the desktop shell there is no supervised executor to report on, and claiming
  // `ready` would hide a queue nobody is draining.
  const [executor, setExecutor] = useState<ExecutorState>(() => ({
    status: window.evidrunDesktop ? "starting" : "stopped",
  }));

  useEffect(() => {
    const desktop = window.evidrunDesktop;
    if (!desktop) return;

    let active = true;
    void desktop
      .getBackendConnection()
      .then(() => active && setState({ status: "ready" }))
      .catch((error: unknown) =>
        active &&
        setState({
          status: "failed",
          message: error instanceof Error ? error.message : "Backend indisponível",
        }),
      );
    void desktop
      .getExecutorState()
      .then((nextState) => active && setExecutor(nextState))
      .catch(() => active && setExecutor({ status: "failed", message: "Executor indisponível" }));

    const unsubscribe = desktop.onBackendStateChanged((nextState) => {
      if (!active) return;
      invalidateBackendConnection();
      setState(nextState);
      if (nextState.status === "ready") void queryClient.invalidateQueries();
    });
    const unsubscribeExecutor = desktop.onExecutorStateChanged((nextState) => {
      if (!active) return;
      setExecutor(nextState);
      // A revived executor drains what piled up, so Run views are stale, not the
      // connection: the backend token and port did not change.
      if (nextState.status === "ready") void queryClient.invalidateQueries();
    });
    return () => {
      active = false;
      unsubscribe();
      unsubscribeExecutor();
    };
  }, [queryClient]);

  const value = useMemo<BackendRuntimeContextValue>(
    () => ({
      state,
      async restart() {
        const desktop = window.evidrunDesktop;
        if (!desktop) return;
        setState({ status: "starting", message: "Reiniciando backend local" });
        invalidateBackendConnection();
        try {
          await desktop.restartBackend();
          invalidateBackendConnection();
          setState({ status: "ready" });
          await queryClient.invalidateQueries();
        } catch (error) {
          setState({
            status: "failed",
            message: error instanceof Error ? error.message : "Falha ao reiniciar backend",
          });
        }
      },
      executor,
      /**
       * Restart the executor alone.
       *
       * The backend keeps running, so evidence stays readable throughout. An interrupted
       * Run resumes on a new attempt once its lease expires — ADR 0014 never turns that
       * into a new Run.
       */
      async restartExecutor() {
        const desktop = window.evidrunDesktop;
        if (!desktop) return;
        setExecutor({ status: "starting", message: "Reiniciando executor de Runs" });
        try {
          setExecutor(await desktop.restartExecutor());
          await queryClient.invalidateQueries();
        } catch (error) {
          setExecutor({
            status: "failed",
            message: error instanceof Error ? error.message : "Falha ao reiniciar executor",
          });
        }
      },
    }),
    [executor, queryClient, state],
  );

  return <BackendRuntimeContext.Provider value={value}>{children}</BackendRuntimeContext.Provider>;
}

export function useBackendRuntime(): BackendRuntimeContextValue {
  const value = useContext(BackendRuntimeContext);
  if (!value) throw new Error("useBackendRuntime must be used inside BackendRuntimeProvider");
  return value;
}
