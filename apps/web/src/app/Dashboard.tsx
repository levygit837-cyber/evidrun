import * as Tabs from "@radix-ui/react-tabs";
import * as Tooltip from "@radix-ui/react-tooltip";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Bot,
  Box,
  Check,
  ChevronRight,
  CircleDot,
  Database,
  Download,
  FlaskConical,
  GitCompareArrows,
  Hash,
  Layers3,
  MessageSquareText,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { BackendState, Comparison, Run } from "../types";

const short = (value: string | null | undefined, size = 10) =>
  value ? `${value.slice(0, size)}…` : "—";

function StatusDot({ status }: { status: string }) {
  return (
    <span className={`status-dot status-${status}`}>
      <span /> {status}
    </span>
  );
}

function ScoreRing({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div className="score-ring" style={{ "--score": `${pct * 3.6}deg` } as React.CSSProperties}>
      <div>
        <strong>{pct}</strong>
        <span>score</span>
      </div>
    </div>
  );
}

function EmptyState({ onRun, pending }: { onRun: () => void; pending: boolean }) {
  return (
    <main className="empty-state">
      <div className="empty-orbit orbit-one" />
      <div className="empty-orbit orbit-two" />
      <div className="empty-copy">
        <span className="eyebrow"><FlaskConical size={14} /> laboratório pronto</span>
        <h1>Contexto bom é contexto <em>comprovado.</em></h1>
        <p>
          Execute o primeiro benchmark controlado. O Evidrun vai preservar cada decisão,
          snapshot, evidência e trade-off sem chamar nenhuma API externa.
        </p>
        <button className="primary-action" onClick={onRun} disabled={pending}>
          {pending ? <RefreshCw className="spin" size={17} /> : <Play size={17} fill="currentColor" />}
          {pending ? "Executando laboratório…" : "Executar CRL-CTX-002"}
        </button>
        <div className="empty-promises">
          <span><ShieldCheck size={15} /> offline</span>
          <span><Hash size={15} /> hash chain</span>
          <span><GitCompareArrows size={15} /> variável isolada</span>
        </div>
      </div>
    </main>
  );
}

function RunPanel({ run, active }: { run: Run; active: boolean }) {
  return (
    <article className={`run-panel ${active ? "candidate" : "baseline"}`}>
      <div className="run-panel-head">
        <div>
          <span className="variant-label">{active ? "candidate" : "baseline"}</span>
          <h3>{run.variant_id}</h3>
        </div>
        <ScoreRing score={run.grade?.score ?? 0} />
      </div>
      <div className="run-output">
        <span>Resposta observada</span>
        <p>{run.output}</p>
      </div>
      <dl className="run-facts">
        <div><dt>Policy</dt><dd>{run.context_snapshot?.policy_id}</dd></div>
        <div><dt>Janela</dt><dd>{run.context_snapshot?.selected_chars} chars</dd></div>
        <div><dt>Estratégia</dt><dd>{run.context_snapshot?.strategy}</dd></div>
        <div><dt>Context hash</dt><dd>{short(run.context_hash)}</dd></div>
      </dl>
      <div className="evidence-box">
        <span><CircleDot size={13} /> Evidência citada</span>
        <code>{run.grade?.evidence[0] ?? "Nenhuma evidência decisiva ficou visível."}</code>
      </div>
    </article>
  );
}

function ComparisonView({ comparison, runs }: { comparison: Comparison; runs: Run[] }) {
  const baseline = runs.find((run) => run.id === comparison.baseline_run_id);
  const candidate = runs.find((run) => run.id === comparison.candidate_run_id);
  if (!baseline || !candidate) return null;
  return (
    <section className="comparison-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow"><GitCompareArrows size={14} /> comparação pareada</span>
          <h2>Uma mudança. Um efeito observável.</h2>
        </div>
        <div className="validity-badge"><Check size={14} /> {comparison.validity}</div>
      </div>
      <div className="comparison-grid">
        <RunPanel run={baseline} active={false} />
        <div className="delta-column">
          <span>delta</span>
          <strong>+{comparison.delta.toFixed(2)}</strong>
          <ArrowRight size={22} />
          <small>{comparison.primary_variable}</small>
        </div>
        <RunPanel run={candidate} active />
      </div>
      <div className="context-diff">
        <div className="diff-head">
          <div><Layers3 size={16} /><span>Context diff</span></div>
          <span>{baseline.context_snapshot?.source_chars} caracteres na fonte</span>
        </div>
        <div className="diff-track">
          <div className="diff-segment kept-head">início preservado</div>
          <div className="diff-gap">evidência omitida no baseline</div>
          <div className="diff-segment kept-tail">ROOT_CAUSE preservada</div>
        </div>
        <div className="diff-snippet">
          <span className="minus">− {baseline.context_snapshot?.strategy}: fim removido</span>
          <span className="plus">+ {candidate.context_snapshot?.strategy}: DB_POOL_EXHAUSTED visível</span>
        </div>
      </div>
    </section>
  );
}

export function Dashboard() {
  const queryClient = useQueryClient();
  const [backendState, setBackendState] = useState<BackendState>({ status: "ready" });
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const bootstrap = useMutation({
    mutationFn: api.bootstrapDemo,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
  });
  const exportBundle = useMutation({
    mutationFn: api.exportBundle,
    onSuccess: async ({ path }) => {
      if (window.evidrunDesktop) await window.evidrunDesktop.showItemInFolder(path);
    },
  });

  useEffect(() => {
    if (!window.evidrunDesktop) return;
    return window.evidrunDesktop.onBackendStateChanged(setBackendState);
  }, []);

  const data = dashboard.data;
  const comparison = data?.comparisons[0];
  const experiment = data?.experiments[0];
  const orderedRuns = useMemo(
    () => [...(data?.runs ?? [])].sort((a, b) => a.variant_id.localeCompare(b.variant_id)),
    [data?.runs],
  );

  if (dashboard.isLoading) {
    return <div className="app-loading"><FlaskConical size={26} /><span>Montando o laboratório…</span></div>;
  }
  if (dashboard.isError) {
    return <div className="app-loading error"><Database size={26} /><span>{dashboard.error.message}</span></div>;
  }

  const hasExperiment = Boolean(data?.experiments.length);
  return (
    <Tooltip.Provider delayDuration={250}>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="brand"><div className="brand-mark"><FlaskConical size={19} /></div><span>evidrun</span><small>alpha</small></div>
          <nav>
            <a className="active"><Activity size={17} /> Visão geral</a>
            <a><FlaskConical size={17} /> Experimentos <span>{data?.summary.experiments ?? 0}</span></a>
            <a><TerminalSquare size={17} /> Runs <span>{data?.summary.runs ?? 0}</span></a>
            <a><GitCompareArrows size={17} /> Comparações</a>
            <a><MessageSquareText size={17} /> Lab Agent <i>em breve</i></a>
          </nav>
          <div className="sidebar-section"><span>Conhecimento</span><a><BookOpen size={17} /> Documentação</a><a><Box size={17} /> Artifacts</a></div>
          <div className="sidebar-footer">
            <div className="backend-line"><span className={`backend-light ${backendState.status}`} /><div><strong>Backend {backendState.status}</strong><small>local · SQLite/WAL</small></div></div>
          </div>
        </aside>

        <div className="main-column">
          <header className="topbar">
            <div className="breadcrumbs"><span>Context Reliability Lab</span><ChevronRight size={14} /><strong>Visão geral</strong></div>
            <div className="topbar-actions"><button className="search"><Search size={15} /> Buscar evidência <kbd>⌘ K</kbd></button><button className="icon-button"><Sparkles size={17} /></button></div>
          </header>

          {!hasExperiment ? (
            <EmptyState onRun={() => bootstrap.mutate()} pending={bootstrap.isPending} />
          ) : (
            <main className="workspace">
              <section className="hero-row">
                <div>
                  <span className="eyebrow"><CircleDot size={13} /> experimento aceito</span>
                  <h1>{experiment?.title}</h1>
                  <p>{experiment?.manifest.hypothesis}</p>
                  <div className="hero-meta"><span><Hash size={13} /> {short(experiment?.manifest_hash, 14)}</span><span><ShieldCheck size={13} /> {experiment?.manifest.evidence_mode}</span></div>
                </div>
                <button className="secondary-action" onClick={() => bootstrap.mutate()} disabled={bootstrap.isPending}><RefreshCw size={15} className={bootstrap.isPending ? "spin" : ""} /> Repetir experimento</button>
              </section>

              <section className="metric-strip">
                <div><span>Runs</span><strong>{data?.summary.runs}</strong><small>todas concluídas</small></div>
                <div><span>Eventos preservados</span><strong>{data?.summary.events}</strong><small>append-only ledger</small></div>
                <div><span>Variável primária</span><strong className="text-value">context_policy</strong><small>sem confounders</small></div>
                <div><span>Melhoria observada</span><strong className="positive">+100%</strong><small>score determinístico</small></div>
              </section>

              <Tabs.Root defaultValue="comparison" className="lab-tabs">
                <Tabs.List><Tabs.Trigger value="comparison">Comparação</Tabs.Trigger><Tabs.Trigger value="timeline">Runs & contexto</Tabs.Trigger><Tabs.Trigger value="report">Relatório</Tabs.Trigger><Tabs.Trigger value="chat">Chat</Tabs.Trigger></Tabs.List>
                <Tabs.Content value="comparison">{comparison && <ComparisonView comparison={comparison} runs={orderedRuns} />}</Tabs.Content>
                <Tabs.Content value="timeline">
                  <section className="timeline-section">
                    <div className="section-heading"><div><span className="eyebrow"><Activity size={14} /> trilha auditável</span><h2>Da policy ao resultado</h2></div></div>
                    {orderedRuns.map((run) => <div className="timeline-run" key={run.id}><div className="timeline-rail"><span /><span /><span /><span /></div><div><h3>{run.variant_id}</h3><StatusDot status={run.status} /><ol><li><strong>run.queued</strong><small>{short(run.id, 18)}</small></li><li><strong>context.composed</strong><small>{run.context_snapshot?.strategy} · {run.context_snapshot?.selected_chars} chars</small></li><li><strong>subject.responded</strong><small>{run.output}</small></li><li><strong>grader.completed</strong><small>score {run.grade?.score.toFixed(2)}</small></li></ol></div></div>)}
                  </section>
                </Tabs.Content>
                <Tabs.Content value="report">
                  <article className="report-card"><div className="report-toolbar"><span><BookOpen size={15} /> Relatório gerado da evidência</span><button onClick={() => comparison && exportBundle.mutate(comparison.id)}><Download size={14} /> Exportar bundle</button></div><pre>{comparison?.report_markdown}</pre></article>
                </Tabs.Content>
                <Tabs.Content value="chat">
                  <section className="chat-shell"><div className="chat-empty"><div className="bot-orb"><Bot size={25} /></div><h2>Lab Agent ainda não configurado</h2><p>As sessões já possuem escopo explícito e persistência. Um provider será conectado somente no próximo marco, sem misturar históricos automaticamente.</p><span><ShieldCheck size={14} /> nenhum provider externo ativo</span></div><div className="chat-composer"><input disabled placeholder="Configure um provider para conversar sobre este experimento…" /><button disabled><ArrowRight size={17} /></button></div></section>
                </Tabs.Content>
              </Tabs.Root>
            </main>
          )}
        </div>
      </div>
    </Tooltip.Provider>
  );
}

