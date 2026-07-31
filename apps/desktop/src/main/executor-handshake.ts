import { BridgeError, bridgeErrorCodes } from "../shared/desktop-contract.js";

export interface ExecutorReadinessMessage {
  protocol: "evidrun-worker-v1";
  schema_version: "1";
  pid: number;
  worker_id: string;
}

/**
 * Validate the executor's readiness line.
 *
 * Deliberately strict and separate from the backend's envelope: the two processes
 * announce different things, and accepting a malformed banner would report `ready` for an
 * executor that may never claim a job.
 */
export function parseExecutorReadiness(line: string): ExecutorReadinessMessage {
  const value = JSON.parse(line) as Partial<ExecutorReadinessMessage>;
  if (
    value.protocol !== "evidrun-worker-v1" ||
    value.schema_version !== "1" ||
    typeof value.pid !== "number" ||
    value.pid < 1 ||
    typeof value.worker_id !== "string" ||
    value.worker_id.length === 0
  ) {
    throw new BridgeError(
      bridgeErrorCodes.invalidExecutorHandshake,
      "Executor returned an invalid desktop handshake",
    );
  }
  return value as ExecutorReadinessMessage;
}
