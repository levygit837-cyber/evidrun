import { useEffect, useReducer } from "react";
import {
  ArrowDown,
  ChartBar,
  ChatsCircle,
  CheckCircle,
  DownloadSimple,
  Fingerprint,
  Play,
  ShieldCheck,
  WarningCircle,
} from "@phosphor-icons/react";
import { CRL_EVENTS, ILLUSTRATIVE_EVENTS, RUN_PHASES, STUB_EVENTS } from "../data/mockData.js";
import { runInitialState, runReducer } from "../state/runState.js";
import { Button, Notice, SegmentedControl, StatusBadge, TechnicalRef } from "../components/primitives/Controls.jsx";
import { FixtureScopeLock } from "../components/scope/FixtureScopeLock.jsx";

const PRESETS = [
  { value: "loading", label: "Loading" },
  { value: "failed", label: "Failed" },
  { value: "completed", label: "Completed" },
  { value: "live", label: "Live ilustrativa" },
];

const PHASE_EVENT_COUNTS = [1, 3, 6, 8, 9];

async function digestPayload(payload) {
  if (!globalThis.crypto?.subtle) return "digest-local-stub";
  const bytes = new TextEncoder().encode(payload);
  const hash = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function RunLedger({ events, activeType, illustrative = false }) {
  return (
    <ol className="run-ledger" aria-label={illustrative ? "Sequência ilustrativa" : "Nove eventos factuais da fixture"}>
      {events.map((event) => {
        const active = event.type === activeType;
        return (
          <li key={event.id} className={active ? "is-active" : ""}>
            <span className="run-ledger__marker">{active ? <span /> : <CheckCircle size={18} weight="regular" aria-hidden="true" />}</span>
            <div className="run-ledger__event"><small>{event.phase}</small><strong>{event.type}</strong><code>{event.ref}</code></div>
            <time>{event.time ?? (active ? "ativo" : "concluído")}</time>
          </li>
        );
      })}
    </ol>
  );
}

export function RunsRoute({ onOpenChat, navigate, project, onSelectFixture }) {
  const [run, dispatch] = useReducer(runReducer, runInitialState);

  useEffect(() => {
    if (run.preset !== "progressing") return undefined;
    const timeout = setTimeout(() => dispatch({ type: "ADVANCE" }), 720);
    return () => clearTimeout(timeout);
  }, [run.preset, run.phaseIndex, run.generation]);

  const exportBundle = async () => {
    const payload = JSON.stringify({
      bundle_version: 3,
      mode: "references_only",
      portable: false,
      replayable: false,
      run: "run_019f9100...ae5e5",
      references: CRL_EVENTS.map((event) => event.ref),
    }, null, 2);
    const digest = await digestPayload(payload);
    if (typeof URL.createObjectURL === "function") {
      const url = URL.createObjectURL(new Blob([payload], { type: "application/json" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "evidrun-bundle-v3-references-only.json";
      anchor.click();
      URL.revokeObjectURL(url);
    }
    dispatch({ type: "EXPORTED", digest });
  };

  const progressingEvents = STUB_EVENTS.slice(0, PHASE_EVENT_COUNTS[run.phaseIndex]);
  const activeType = run.phaseIndex === 0 ? "run.queued" : run.phaseIndex === 1 ? "run.preparing" : run.phaseIndex === 2 ? "run.running" : run.phaseIndex === 3 ? "run.evaluating" : "run.completed";
  const displayEvents = run.preset === "progressing" ? progressingEvents : CRL_EVENTS;
  const isIllustrative = run.preset === "live" || run.preset === "progressing";

  if (project.id !== "crl") {
    return <FixtureScopeLock entity="Run" project={project} onBack={() => navigate("/projects")} onOpenFixture={onSelectFixture} />;
  }

  return (
    <div className="route route--runs">
      <header className="route-header route-header--actions">
        <div>
          <span className="route-kicker">Runs & Evidence</span>
          <h1>{run.preset === "live" ? "Run Observatory" : run.preset === "progressing" ? run.phaseIndex === 4 ? "Stub Run terminal" : "Stub Run em execução" : run.preset === "failed" ? "Run interrompida" : run.preset === "loading" ? "Carregando Run" : "Run completed"}</h1>
          <p>{run.preset === "live" ? "Contexto ilustrativo separado para demonstrar read_text sem atribuí-lo à fixture CRL." : run.preset === "progressing" ? "Lifecycle local com IDs e eventos demonstrativos. Nenhum record da fixture canônica é reutilizado." : "Acompanhe fase, job, attempt, eventos factuais e as limitações do Bundle."}</p>
        </div>
        <div className="route-header__actions">
          <Button icon={ChatsCircle} onClick={onOpenChat}>Abrir Chat</Button>
          <Button variant="primary" icon={Play} onClick={() => dispatch({ type: "START" })}>Start Stub Run</Button>
        </div>
      </header>

      <div className="run-preset-bar">
        <span>Presets determinísticos</span>
        <SegmentedControl
          compact
          label="Estado demonstrado da Run"
          value={run.preset}
          onChange={(preset) => dispatch({ type: "PRESET", preset })}
          options={PRESETS}
        />
      </div>

      {run.preset === "loading" ? (
        <section className="run-loading" aria-busy="true" aria-label="Carregando Run">
          <div className="skeleton skeleton--title" />
          <div className="skeleton skeleton--meta" />
          <div className="skeleton-grid"><div className="skeleton skeleton--panel" /><div className="skeleton skeleton--panel" /></div>
        </section>
      ) : run.preset === "failed" ? (
        <section className="run-failed">
          <WarningCircle size={38} aria-hidden="true" />
          <div><h2>Attempt encerrado antes da fase terminal</h2><p>Falha determinística do stub durante <TechnicalRef>run.running</TechnicalRef>. Nenhum evento completed foi inventado.</p></div>
          <dl><div><dt>Run</dt><dd>demo:run-failed</dd></div><div><dt>Job</dt><dd>demo:job-failed-01</dd></div><div><dt>Attempt</dt><dd>demo:attempt-01</dd></div></dl>
          <Button onClick={() => dispatch({ type: "START" })}>Iniciar outro stub</Button>
        </section>
      ) : (
        <>
          <section className="run-identity">
            <div className="run-identity__primary">
              <div><span>Run</span><TechnicalRef>{run.runId}</TechnicalRef></div>
              <StatusBadge tone={isIllustrative ? "info" : "success"}>{run.status}</StatusBadge>
              {isIllustrative ? <StatusBadge tone="warning">Demonstração local</StatusBadge> : <StatusBadge tone="neutral">CRL-CTX-002</StatusBadge>}
            </div>
            <dl>
              <div><dt>Job</dt><dd>{run.jobId}</dd></div>
              <div><dt>Attempt</dt><dd>{run.attemptId}</dd></div>
              <div><dt>Variant</dt><dd>{run.preset === "live" ? "read-text" : run.preset === "progressing" ? "lifecycle-stub" : "tail-preservation · rep 1"}</dd></div>
              <div><dt>Data</dt><dd>23 jul 2026 · America/Asuncion</dd></div>
            </dl>
          </section>

          <div className="runs-layout">
            <section className="runs-main">
              {run.preset === "completed" ? (
                <section className="captured-comparison" aria-labelledby="comparison-title">
                  <header><div><ChartBar size={21} aria-hidden="true" /><h2 id="comparison-title">Comparação capturada</h2></div><TechnicalRef>artifact:comparison-crl-ctx-002</TechnicalRef></header>
                  <div className="score-comparison">
                    <div><span>head-truncation</span><div className="score-line"><i style={{ width: "0%" }} /></div><strong>0.0</strong></div>
                    <div className="is-selected"><span>tail-preservation</span><div className="score-line"><i style={{ width: "100%" }} /></div><strong>1.0</strong></div>
                  </div>
                  <p>Fixture conhecida: delta 1.0. Não extrapolar para outros benchmarks.</p>
                </section>
              ) : run.preset === "live" ? (
                <Notice tone="warning" title="Sequência ilustrativa separada">
                  A Run abaixo demonstra <TechnicalRef>read_text</TechnicalRef> em um contexto autorizado distinto. O manifest CRL-CTX-002 não possui tools.
                </Notice>
              ) : (
                <Notice title="Lifecycle ilustrativo separado">
                  Esta sequência usa somente IDs <TechnicalRef>demo:</TechnicalRef> e refs <TechnicalRef>event:demo-stub-*</TechnicalRef>. Ela não é a Run capturada pela fixture CRL.
                </Notice>
              )}

              <section className="run-story" aria-labelledby="run-story-title">
                <header>
                  <div><h2 id="run-story-title">{run.preset === "live" ? "Sequência ilustrativa" : run.preset === "progressing" ? "Lifecycle do stub" : "Ledger factual"}</h2><p>{run.preset === "live" ? "Eventos do stub de ferramenta, não da fixture CRL." : run.preset === "progressing" ? `${displayEvents.length} de 9 eventos ilustrativos.` : `${displayEvents.length} de 9 eventos da história canônica.`}</p></div>
                  {run.preset === "progressing" ? <StatusBadge tone="info">{RUN_PHASES[run.phaseIndex]}</StatusBadge> : <StatusBadge tone={run.preset === "live" ? "warning" : "success"}>{run.preset === "live" ? "não registrado" : "9 eventos"}</StatusBadge>}
                </header>
                <RunLedger events={run.preset === "live" ? ILLUSTRATIVE_EVENTS : displayEvents} activeType={run.preset === "live" ? "run.evaluating" : run.preset === "progressing" ? activeType : null} illustrative={isIllustrative} />
              </section>
            </section>

            <aside className="evidence-panel" aria-labelledby="evidence-panel-title">
              <header><Fingerprint size={23} aria-hidden="true" /><div><span>Proveniência</span><h2 id="evidence-panel-title">{isIllustrative ? "Contexto ilustrativo" : "Evidence & Bundle"}</h2></div></header>
              {isIllustrative ? (
                <>
                  <div className="provenance-chain">
                    <div><span>RunSpec</span><TechnicalRef>{run.preset === "live" ? "demo:rspec-read-text" : "demo:rspec-stub"}</TechnicalRef></div>
                    <ArrowDown size={18} aria-hidden="true" />
                    <div><span>AdmissionRecord</span><TechnicalRef>{run.preset === "live" ? "demo:admission-read-text" : "demo:admission-stub"}</TechnicalRef><StatusBadge tone="warning">não registrado</StatusBadge></div>
                    <ArrowDown size={18} aria-hidden="true" />
                    <div><span>Run</span><TechnicalRef>{run.runId}</TechnicalRef></div>
                  </div>
                  <Notice compact title="Nenhum record canônico">IDs `demo:` representam somente estado React. Não constituem RunSpec, AdmissionRecord, Run ou Evidence registrados.</Notice>
                  <section className="bundle-card">
                    <header><div><h3>Bundle indisponível</h3><p>sem export demonstrativo</p></div><StatusBadge tone="warning">não registrado</StatusBadge></header>
                    <dl>
                      <div><dt>portable</dt><dd>não alegado</dd></div>
                      <div><dt>replayable</dt><dd>não alegado</dd></div>
                      <div><dt>integrity</dt><dd>não verificável</dd></div>
                    </dl>
                    <Button variant="primary" icon={DownloadSimple} disabled>Exportar Bundle</Button>
                    <p>Selecione Completed para consultar a fixture CRL estável e seu bundle references-only.</p>
                  </section>
                </>
              ) : (
                <>
                  <div className="provenance-chain">
                    <div><span>RunSpec</span><TechnicalRef>rspec_019f9100...09fd4</TechnicalRef></div>
                    <ArrowDown size={18} aria-hidden="true" />
                    <div><span>AdmissionRecord</span><TechnicalRef>adm_019f9100...160304</TechnicalRef><StatusBadge tone="success">admitted</StatusBadge></div>
                    <ArrowDown size={18} aria-hidden="true" />
                    <div><span>Run</span><TechnicalRef>{run.runId}</TechnicalRef></div>
                  </div>

                  <section className="digest-limit">
                    <ShieldCheck size={20} aria-hidden="true" />
                    <div><h3>SubjectEnvelope digest</h3><TechnicalRef>4be0e9fe...91c50d3a</TechnicalRef><p>Registrado em subject.invoked. O documento exato não foi persistido nem exportado, portanto o envelope não é recomputável pelo Bundle.</p></div>
                  </section>

                  <section className="bundle-card">
                    <header><div><h3>Bundle v3</h3><p>{run.exported ? "export local concluído" : "ainda não exportado"}</p></div><StatusBadge tone="neutral">references_only</StatusBadge></header>
                    <dl>
                      <div><dt>portable</dt><dd>false</dd></div>
                      <div><dt>replayable</dt><dd>false</dd></div>
                      <div><dt>integrity</dt><dd>{run.exported ? "verificada após export" : "verificar após export"}</dd></div>
                    </dl>
                    {run.exported ? <TechnicalRef>sha256:{run.digest?.slice(0, 16)}...</TechnicalRef> : null}
                    <Button variant="primary" icon={DownloadSimple} onClick={exportBundle}>{run.exported ? "Exportado e verificado" : "Exportar Bundle"}</Button>
                    <p>Integridade não implica blobs, grants, portabilidade, restore ou replay.</p>
                  </section>
                </>
              )}
            </aside>
          </div>
        </>
      )}
      <div className="sr-only" aria-live="polite">Estado atual da Run: {run.status}</div>
    </div>
  );
}
