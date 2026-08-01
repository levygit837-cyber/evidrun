import { useMutation } from "@tanstack/react-query";
import { Box, Download, ExternalLink, FileWarning, LoaderCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ObservabilityAdapter } from "../../data/contracts";
import { Fact, PageState } from "./ObservabilityParts";
import {
  TERMINAL_RUN_STATUSES,
  type DetailData,
  formatDate,
  projectEvidenceReferences,
} from "./observabilityModel";

export function EvidencePanel({
  data,
  adapter,
}: {
  data: DetailData;
  adapter: ObservabilityAdapter;
}) {
  const refs = useMemo(
    () => projectEvidenceReferences(data.events, data.evaluations, data.checkpoints),
    [data.checkpoints, data.evaluations, data.events],
  );
  const groupedRefs = useMemo(() => ({
    event: refs.filter((item) => item.origin === "event"),
    evaluation: refs.filter((item) => item.origin === "evaluation"),
    checkpoint: refs.filter((item) => item.origin === "checkpoint"),
  }), [refs]);
  const [exportedPath, setExportedPath] = useState<string | null>(null);
  const [revealError, setRevealError] = useState<string | null>(null);
  const exportBundle = useMutation({
    mutationFn: () => adapter.exportRunBundle(data.run.id),
    onSuccess: (result) => setExportedPath(result.path),
  });
  const terminal = TERMINAL_RUN_STATUSES.has(data.run.status);

  useEffect(() => {
    setExportedPath(null);
    setRevealError(null);
  }, [data.run.id]);

  async function reveal() {
    if (!exportedPath || !window.evidrunDesktop) return;
    setRevealError(null);
    const shown = await window.evidrunDesktop.showItemInFolder(exportedPath);
    if (!shown) setRevealError("O desktop não conseguiu revelar o arquivo exportado.");
  }

  return (
    <div className="obs-evidence">
      <div className="obs-context-note">
        <Box aria-hidden="true" size={15} />
        <span>Evidence Bundle v3 usa references_only. portable=false e replayable=false.</span>
      </div>
      <div className="obs-bundle-actions">
        <button
          className="obs-action-button"
          disabled={!terminal || exportBundle.isPending}
          onClick={() => exportBundle.mutate()}
          type="button"
        >
          {exportBundle.isPending ? <LoaderCircle className="obs-spin" size={14} /> : <Download size={14} />}
          Export Evidence Bundle v3
        </button>
        {!terminal ? <span>Disponível após estado terminal.</span> : null}
        {exportedPath ? (
          <button
            className="obs-text-button"
            disabled={!window.evidrunDesktop}
            onClick={() => void reveal()}
            type="button"
          >
            <ExternalLink aria-hidden="true" size={13} />
            Revelar arquivo
          </button>
        ) : null}
      </div>
      {exportBundle.isError ? (
        <div className="obs-inline-error" role="alert">Falha ao exportar o Evidence Bundle v3.</div>
      ) : null}
      {exportedPath ? <code className="obs-export-path">{exportedPath}</code> : null}
      {revealError ? <div className="obs-inline-error" role="alert">{revealError}</div> : null}
      <section className="obs-reference-list">
        <header>
          <strong>Referências preservadas</strong>
          <span>{refs.length}</span>
        </header>
        {refs.length ? (
          <div className="obs-evidence-groups">
            {(["event", "evaluation", "checkpoint"] as const).map((origin) => groupedRefs[origin].length ? (
              <section key={origin}>
                <h3>{origin === "event" ? "Run Events" : origin === "evaluation" ? "Recorded Evaluations" : "Checkpoint Records"}</h3>
                <ul>
                  {groupedRefs[origin].map((item, index) => (
                    <li key={`${item.sourceId}:${item.ref}:${index}`}>
                      <code>{item.ref}</code>
                      <dl>
                        <Fact label="Origem">{item.origin}</Fact>
                        <Fact label="Papel">{item.role || "Não informado"}</Fact>
                        <Fact label="Record">{item.sourceId || "Não informado"}</Fact>
                        <Fact label="Digest">{item.digest ?? "Não informado"}</Fact>
                        <Fact label="Media type">{item.mediaType ?? "Não informado"}</Fact>
                        <Fact label="Sequence">{item.sequence ?? "Não informado"}</Fact>
                        <Fact label="Timestamp">{item.timestamp ? formatDate(item.timestamp) : "Não informado"}</Fact>
                        <Fact label="Classification">{item.classification ?? "Não informado"}</Fact>
                        <Fact label="Gate">{item.gateStatus ?? "Não informado"}</Fact>
                      </dl>
                      <span>Referência preservada; conteúdo indisponível</span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null)}
          </div>
        ) : (
          <PageState icon={<FileWarning size={20} />} title="Sem referências" role="status">
            Nenhuma ref run:, event: ou artifact: aparece nos records carregados.
          </PageState>
        )}
      </section>
    </div>
  );
}
