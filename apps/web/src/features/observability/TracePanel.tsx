import { Box, Check, ChevronDown, Copy, TerminalSquare } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { RunEvent } from "../../types";
import { Fact, PageState } from "./ObservabilityParts";
import {
  correlateToolEvents,
  formatDate,
  getForensicTurnWindow,
  sortEvents,
} from "./observabilityModel";

export function TracePanel({ events }: { events: RunEvent[] }) {
  const ordered = useMemo(() => sortEvents(events), [events]);
  const toolCorrelations = useMemo(() => correlateToolEvents(ordered), [ordered]);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const selectedEvent = ordered.find((event) => event.event_id === expandedEventId) ?? null;
  const forensicWindow = selectedEvent
    ? getForensicTurnWindow(ordered, selectedEvent.event_id)
    : null;

  useEffect(() => {
    setExpandedEventId(null);
    setCopied(false);
  }, [events[0]?.run_id]);

  async function copyWindow() {
    if (!forensicWindow) return;
    await navigator.clipboard.writeText(JSON.stringify(forensicWindow, null, 2));
    setCopied(true);
  }

  if (!ordered.length) {
    return (
      <PageState icon={<TerminalSquare size={20} />} title="Sem eventos" role="status">
        O ledger ainda não possui records para esta Run.
      </PageState>
    );
  }

  return (
    <div className="obs-trace">
      <ol aria-label="Eventos ordenados por sequence">
        {ordered.map((event) => {
          const expanded = expandedEventId === event.event_id;
          const toolState = toolCorrelations.get(event.event_id);
          return (
            <li key={`${event.sequence}:${event.event_id}`} data-event-type={event.type}>
              <button
                aria-expanded={expanded}
                className="obs-event-row"
                onClick={() => {
                  setCopied(false);
                  setExpandedEventId(expanded ? null : event.event_id);
                }}
                type="button"
              >
                <span className="obs-event-sequence mono">{String(event.sequence).padStart(3, "0")}</span>
                <span className="obs-event-type mono">
                  {toolState === "complete" ? <Box aria-hidden="true" size={13} /> : null}
                  {event.type}
                </span>
                <span className="obs-event-actor">{event.actor_type}</span>
                <time className="mono" dateTime={event.occurred_at_utc}>{formatDate(event.occurred_at_utc)}</time>
                <ChevronDown aria-hidden="true" size={14} />
              </button>
              {expanded ? (
                <div className="obs-event-expanded">
                  {toolState === "complete" ? (
                    <div className="obs-tool-state">Tool activity correlacionada por call_id.</div>
                  ) : null}
                  {toolState === "orphan-terminal" ? (
                    <div className="obs-tool-state obs-tool-state-incomplete">Evento factual incompleto: tool.called correlacionado não foi carregado.</div>
                  ) : null}
                  <dl>
                    <Fact label="Sequence">{event.sequence}</Fact>
                    <Fact label="Timestamp">{formatDate(event.occurred_at_utc)}</Fact>
                    <Fact label="Classification">{event.classification || "Não informado"}</Fact>
                    <Fact label="Correlation ID">{event.correlation_id ?? "Não informado"}</Fact>
                    <Fact label="Causation ID">{event.causation_id ?? "Não informado"}</Fact>
                    <Fact label="Event ID">{event.event_id}</Fact>
                    <Fact label="Event hash">{event.event_hash}</Fact>
                    <Fact label="Prev hash">{event.prev_event_hash ?? "Primeiro evento"}</Fact>
                    <Fact label="Actor">{`${event.actor_type}:${event.actor_id}`}</Fact>
                  </dl>
                  <label>
                    Payload factual
                    <pre tabIndex={0}>{JSON.stringify(event.payload, null, 2)}</pre>
                  </label>
                  <section className="obs-forensic-window" aria-label="Janela forense read-only">
                    <div>
                      <strong>Janela forense read-only</strong>
                      <span>{forensicWindow ? "1 turno disponível" : "Nenhum turno completo neste ponto"}</span>
                    </div>
                    {forensicWindow ? (
                      <>
                        <button className="obs-text-button" onClick={() => void copyWindow()} type="button">
                          {copied ? <Check aria-hidden="true" size={13} /> : <Copy aria-hidden="true" size={13} />}
                          {copied ? "Copiado" : "Copiar 1 turno"}
                        </button>
                        <pre tabIndex={0}>{JSON.stringify(forensicWindow, null, 2)}</pre>
                      </>
                    ) : null}
                  </section>
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
