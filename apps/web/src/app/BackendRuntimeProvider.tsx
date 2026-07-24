import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { invalidateBackendConnection } from "../api/client";
import type { BackendState } from "../types";

interface BackendRuntimeContextValue {
  state: BackendState;
  restart(): Promise<void>;
}

const BackendRuntimeContext = createContext<BackendRuntimeContextValue | null>(null);

export function BackendRuntimeProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<BackendState>(() => ({
    status: window.evidrunDesktop ? "starting" : "ready",
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

    const unsubscribe = desktop.onBackendStateChanged((nextState) => {
      if (!active) return;
      invalidateBackendConnection();
      setState(nextState);
      if (nextState.status === "ready") void queryClient.invalidateQueries();
    });
    return () => {
      active = false;
      unsubscribe();
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
    }),
    [queryClient, state],
  );

  return <BackendRuntimeContext.Provider value={value}>{children}</BackendRuntimeContext.Provider>;
}

export function useBackendRuntime(): BackendRuntimeContextValue {
  const value = useContext(BackendRuntimeContext);
  if (!value) throw new Error("useBackendRuntime must be used inside BackendRuntimeProvider");
  return value;
}
