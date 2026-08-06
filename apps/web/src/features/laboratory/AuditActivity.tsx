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
  mode = "demo",
}: {
  statusLog: string[];
  tools: ToolEvent[];
  phase: LaboratoryPhase;
  mode?: "demo" | "live";
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
        <span className="laboratory-live-label">{mode === "live" ? "Live" : "Demo"}</span>
        <span className="laboratory-audit-summary-state">
          {running
            ? "em andamento"
            : phaseLabels[phase].toLocaleLowerCase("pt-BR")}
        </span>
      </summary>
      <div className="laboratory-audit-body">
        <p>
          Eventos de apresentação do corredor {mode === "live" ? "real" : "Demo"}. Esta área não mostra raciocínio oculto.
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
                        {tool.argumentsSummary ?? "Sem parâmetros."}
                      </dd>
                    </div>
                    <div>
                      <dt>Resultado</dt>
                      <dd>
                        {safeResult(tool.resultSummary, tool.name)}
                      </dd>
                    </div>
                    <div>
                      <dt>Visibilidade</dt>
                      <dd>{mode === "live" ? "Resumo retornado pela tool" : "Demo local determinística"}</dd>
                    </div>
                    {tool.name === "propose_draft" ? (
                      <div>
                        <dt>Draft — aguarda humano</dt>
                        <dd>
                          Contrato que seria registrado: {safeResult(tool.resultSummary, tool.name)}. Revise o documento e registre a decisão humana na superfície de aceitação; este draft não é fato nem produz efeito externo.
                        </dd>
                      </div>
                    ) : null}
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

/** Qual tool produz número agregado: fato do catálogo, não palpite sobre o texto.
 *
 * A versão anterior procurava "agregad|média|average|metric|valor" no resumo. O backend devolve
 * JSON — `{"groups":[{"value":0.8,"sample_size":2}]}` — então `{"mean":0.8}` passava sem amostra,
 * exatamente o caso que a regra existe para bloquear. O nome da tool é decidível; o texto não.
 */
const AGGREGATE_TOOLS: Record<string, true> = { aggregate_metrics: true };

function safeResult(resultSummary: string | undefined, toolName?: string) {
  if (!resultSummary) return "Aguardando resultado.";
  if (toolName !== undefined && AGGREGATE_TOOLS[toolName] && !/sample_size/i.test(resultSummary)) {
    // Valor agregado sem amostra não é resultado: o contrato trata `sample_size` como validade do
    // grupo, e exibir a média sozinha afirmaria evidência que não existe.
    return "Resultado agregado oculto: a amostra (sample_size) não foi informada.";
  }
  return resultSummary;
}
