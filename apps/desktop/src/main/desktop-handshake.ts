import { BridgeError, bridgeErrorCodes } from "../shared/desktop-contract.js";

export interface ReadinessMessage {
  protocol: "evidrun-desktop-v1";
  port: number;
  backend_instance_id: string;
  schema_version: "1";
  pid: number;
  health_nonce: string;
}

export function parseReadiness(line: string): ReadinessMessage {
  const value = JSON.parse(line) as Partial<ReadinessMessage>;
  if (
    value.protocol !== "evidrun-desktop-v1" ||
    value.schema_version !== "1" ||
    typeof value.port !== "number" ||
    value.port < 1 ||
    value.port > 65535 ||
    typeof value.backend_instance_id !== "string" ||
    typeof value.pid !== "number" ||
    typeof value.health_nonce !== "string"
  ) {
    throw new BridgeError(
      bridgeErrorCodes.invalidBackendHandshake,
      "Backend returned an invalid desktop handshake",
    );
  }
  return value as ReadinessMessage;
}

