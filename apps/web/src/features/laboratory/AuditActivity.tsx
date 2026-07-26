import {
  Braces,
  CheckCircle2,
  ChevronRight,
  FileText,
  LoaderCircle,
  Search,
  XCircle,
} from "lucide-react";
import {
  type LaboratoryPhase,
  type ToolEvent,
  isRunningPhase,
  phaseLabels,
} from "./laboratoryModel";

function ToolIcon({ name }: { name: string }) {
  if (name === "search_repository")
    return <Search aria-hidden="true" size={15} />;
  if (name === "compile_subject")
    return <Braces aria-hidden="true" size={15} />;
  return <FileText aria-hidden="true" size={15} />;
}

function ToolStatus({ tool }: { tool: ToolEvent }) {
  if (tool.status === "running") {
    return (
      <span className="laboratory-tool-status is-running">
        <LoaderCircle aria-hidden="true" size={12} /> em execução
      </span>
    );
  }
  if (tool.status === "failed") {
    return (
      <span className="laboratory-tool-status is-failed">
        <XCircle aria-hidden="true" size={12} /> falhou
      </span>
    );
  }
  return (
    <span className="laboratory-tool-status is-completed">
      <CheckCircle2 aria-hidden="true" size={12} /> concluída
    </span>
  );
}

export function AuditActivity({
  statusLog,
  tools,
  phase,
}: {
  statusLog: string[];
  tools: ToolEvent[];
  phase: LaboratoryPhase;
}) {
  const running = isRunningPhase(phase);

  return (
    <details className="laboratory-audit" open>
      <summary>
        <ChevronRight
          className="laboratory-disclosure-chevron"
          aria-hidden="true"
          size={15}
        />
        <span>Atividade auditável</span>
        <span className="laboratory-demo-label">Demo</span>
        <span className="laboratory-audit-summary-state">
          {running
            ? "em andamento"
            : phaseLabels[phase].toLocaleLowerCase("pt-BR")}
        </span>
      </summary>
      <div className="laboratory-audit-body">
        <p>
          Eventos expostos pelo adapter Demo. Esta área não mostra raciocínio
          oculto e não representa execução do backend.
        </p>
        {statusLog.length > 0 ? (
          <ol className="laboratory-status-log" aria-label="Cronologia Demo">
            {statusLog.map((status, index) => (
              <li key={`${status}-${index}`}>{status}</li>
            ))}
          </ol>
        ) : null}

        {tools.length > 0 ? (
          <div className="laboratory-tool-group" aria-label="Tool calls Demo">
            {tools.map((tool) => (
              <details className="laboratory-tool" key={tool.id}>
                <summary>
                  <span className="laboratory-tool-icon">
                    <ToolIcon name={tool.name} />
                  </span>
                  <span className="laboratory-tool-name">{tool.name}</span>
                  <ToolStatus tool={tool} />
                  {tool.durationMs !== undefined ? (
                    <span className="laboratory-tool-duration">
                      {tool.durationMs} ms
                    </span>
                  ) : null}
                  <ChevronRight
                    className="laboratory-tool-chevron"
                    aria-hidden="true"
                    size={14}
                  />
                </summary>
                <div className="laboratory-tool-detail">
                  <dl>
                    <div>
                      <dt>Parâmetros</dt>
                      <dd>
                        {tool.argumentsSummary ??
                          "Sem parâmetros demonstrativos."}
                      </dd>
                    </div>
                    <div>
                      <dt>Resultado</dt>
                      <dd>
                        {tool.resultSummary ?? "Aguardando resultado Demo."}
                      </dd>
                    </div>
                    <div>
                      <dt>Fonte</dt>
                      <dd>Demo local determinística</dd>
                    </div>
                  </dl>
                </div>
              </details>
            ))}
          </div>
        ) : null}
      </div>
    </details>
  );
}
