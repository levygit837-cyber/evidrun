/** Structured desktop logging with a closed field allowlist. */

type Classification = "public" | "internal";
type LogValue = string | number | boolean;
type LogSink = (line: string) => void;

const REDACTED = "<redacted>";
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}$/;
const EVENT_CODE = /^[a-z][a-z0-9_.-]{2,127}$/;

export const LOG_FIELD_POLICY: Readonly<Record<string, Classification>> = Object.freeze({
  event_code: "public",
  correlation_id: "internal",
  error_code: "public",
  error_type: "public",
  provider_id: "internal",
  status_code: "public",
  worker_id: "internal",
  process: "public",
  exit_code: "public",
  signal: "public",
  bundle_version: "public",
  artifact_ref: "internal",
  contract_type: "public",
  operation: "public",
});

const INTEGER_FIELDS = new Set(["status_code", "exit_code"]);

export interface SecureLogOptions {
  correlationId?: string;
  errorCode?: string;
  error?: unknown;
  fields?: Readonly<Record<string, unknown>>;
}

export function safeLogDocument(
  eventCode: string,
  options: SecureLogOptions = {},
): Record<string, LogValue> {
  const document: Record<string, LogValue> = {
    event_code: safeText(eventCode, true),
  };
  if (options.correlationId !== undefined) {
    document.correlation_id = safeText(options.correlationId);
  }
  if (options.errorCode !== undefined) {
    document.error_code = safeText(options.errorCode);
  }
  if (options.error !== undefined) {
    document.error_type = safeErrorType(options.error);
  }
  for (const [name, value] of Object.entries(options.fields ?? {})) {
    if (!(name in LOG_FIELD_POLICY) || name in document) continue;
    document[name] = safeValue(name, value);
  }
  return document;
}

export function emitSecureLog(
  eventCode: string,
  options: SecureLogOptions = {},
  sink: LogSink = (line) => console.error(line),
): void {
  const document = safeLogDocument(eventCode, options);
  const ordered = Object.fromEntries(
    Object.entries(document).sort(([left], [right]) => left.localeCompare(right)),
  );
  sink(JSON.stringify(ordered));
}

function safeValue(name: string, value: unknown): LogValue {
  if (INTEGER_FIELDS.has(name)) {
    return typeof value === "number" && Number.isInteger(value) ? value : REDACTED;
  }
  return typeof value === "string" ? safeText(value) : REDACTED;
}

function safeErrorType(error: unknown): string {
  if (error instanceof Error) return safeText(error.name);
  return safeText(typeof error);
}

function safeText(value: string, event = false): string {
  return (event ? EVENT_CODE : IDENTIFIER).test(value) ? value : REDACTED;
}
