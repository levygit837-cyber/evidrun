import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { api } from "../api/client";
import { Button } from "../ui/primitives";
import { useBackendRuntime } from "./BackendRuntimeProvider";
import { pendingRunCount, runtimeAlert } from "./runtimeStatus";

/**
 * The banner that keeps a stalled queue from looking like a healthy app.
 *
 * Shares the Observability query key so React Query dedupes it — the queue is read from the
 * API the renderer already talks to, never through the desktop bridge, because Electron Main
 * does not open the database.
 *
 * Only polls while the executor is unhealthy: when everything is fine there is no banner to
 * render and no reason to keep asking.
 */
export function RuntimeAlert() {
  const { state: backend, executor, restart, restartExecutor } = useBackendRuntime();
  const unhealthy = executor.status !== "ready" || backend.status === "failed";
  const runs = useQuery({
    queryKey: ["observability", "runs"],
    queryFn: api.runs,
    enabled: backend.status === "ready",
    refetchInterval: unhealthy ? 5_000 : false,
  });
  const alert = runtimeAlert(backend, executor, pendingRunCount(runs.data ?? []));
  if (!alert) return null;

  return (
    <div className={`runtime-alert runtime-alert-${alert.tone}`} role="alert">
      <AlertTriangle aria-hidden="true" size={16} />
      <div className="runtime-alert-copy">
        <strong>{alert.title}</strong>
        <span>{alert.detail}</span>
      </div>
      {alert.action === "restart-executor" ? (
        <Button onClick={() => void restartExecutor()} size="small" variant="secondary">
          Reiniciar executor
        </Button>
      ) : null}
      {alert.action === "restart-backend" ? (
        <Button onClick={() => void restart()} size="small" variant="secondary">
          Reiniciar backend
        </Button>
      ) : null}
    </div>
  );
}
