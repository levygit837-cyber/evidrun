import { useNavigate, useSearch } from "@tanstack/react-router";
import {
  AlertTriangle,
  FileWarning,
  LoaderCircle,
  Radio,
  RefreshCw,
  Search,
} from "lucide-react";
import { useBackendRuntime } from "../../app/BackendRuntimeProvider";
import { observabilityAdapter } from "../../data/adapters";
import type { ObservabilityAdapter } from "../../data/contracts";
import type { ExecutorState } from "../../types";
import { ListLoadingState, PageState } from "./ObservabilityParts";
import { RunDetailPanel } from "./RunDetailPanel";
import { RunList } from "./RunList";
import { listFailureCopy, type ObservabilitySearchState } from "./observabilityModel";
import { useObservabilityWorkspace } from "./useObservabilityWorkspace";
import "./observability.css";

interface ObservabilityWorkspaceProps {
  adapter?: ObservabilityAdapter;
  /** Absent outside the desktop shell, where no executor is supervised. */
  executor?: ExecutorState;
  search: ObservabilitySearchState;
  onSearchChange(next: ObservabilitySearchState): void;
}

export function ObservabilityWorkspace({
  adapter = observabilityAdapter,
  executor,
  search,
  onSearchChange,
}: ObservabilityWorkspaceProps) {
  const {
    runsQuery,
    detailQuery,
    runs,
    filteredRuns,
    summary,
    failureKind,
    selectedRunId,
    selectedMissing,
    status,
    period,
    filtersActive,
    streamState,
    streamError,
    moreFiltersOpen,
    setMoreFiltersOpen,
    moreFiltersRef,
    moreFiltersButtonRef,
    updateSearch,
    clearFilters,
  } = useObservabilityWorkspace({ adapter, search, onSearchChange });
  const failure = listFailureCopy[failureKind];
  const connectionLabel = runsQuery.isError
    ? failure.connection
    : runsQuery.isPending
      ? "Conectando"
      : runsQuery.isFetching || streamState === "reconnecting"
      ? "Reconectando"
      : "Conectado";

  return (
    <section className="obs-root" aria-label="Observability">
      <form className="obs-command-bar" onSubmit={(event) => event.preventDefault()}>
        <label className="obs-search-control">
          <Search aria-hidden="true" size={15} />
          <span className="obs-sr-only">Buscar Runs</span>
          <input
            aria-label="Buscar Runs"
            onChange={(event) => updateSearch({ q: event.target.value || undefined })}
            placeholder="Run ID, Study, variant ou runner"
            type="search"
            value={search.q ?? ""}
          />
        </label>
        <label>
          <span className="obs-sr-only">Status</span>
          <select
            aria-label="Status"
            onChange={(event) => updateSearch({ status: event.target.value === "all" ? undefined : event.target.value })}
            value={status}
          >
            <option value="all">Todos os status</option>
            <option value="active">Ativas</option>
            <option value="completed">Completed</option>
            <option value="attention">Atenção</option>
          </select>
        </label>
        <label>
          <span className="obs-sr-only">Período</span>
          <select
            aria-label="Período"
            onChange={(event) => updateSearch({ period: event.target.value === "all" ? undefined : event.target.value })}
            value={period}
          >
            <option value="all">Todo o período</option>
            <option value="24h">Últimas 24 h</option>
            <option value="7d">Últimos 7 dias</option>
            <option value="30d">Últimos 30 dias</option>
          </select>
        </label>
        <div className="obs-more-filters" ref={moreFiltersRef}>
          <button aria-controls="obs-more-filters-popover" aria-expanded={moreFiltersOpen} className="obs-clear-button" onClick={() => setMoreFiltersOpen((value) => !value)} ref={moreFiltersButtonRef} type="button">Mais filtros</button>
          {moreFiltersOpen ? (
            <div className="obs-filter-popover" id="obs-more-filters-popover" role="dialog" aria-label="Mais filtros">
              <label>
                Status exato
                <select aria-label="Status exato" onChange={(event) => updateSearch({ status: event.target.value === "all" ? undefined : event.target.value })} value={status}>
                  <option value="all">Qualquer status</option>
                  <option value="active">Ativas (grupo)</option>
                  <option value="attention">Atenção (grupo)</option>
                  <option value="queued">Queued</option>
                  <option value="preparing">Preparing</option>
                  <option value="running">Running</option>
                  <option value="evaluating">Evaluating</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="budget_exhausted">Budget exhausted</option>
                </select>
              </label>
              <p>Provider e trust não são atribuídos por Run pelo endpoint de lista. Runner pode ser pesquisado em q.</p>
            </div>
          ) : null}
        </div>
        {filtersActive ? <button className="obs-clear-button" onClick={clearFilters} type="button">Limpar filtros</button> : null}
        <span className={`obs-command-connection ${runsQuery.isError ? "is-error" : connectionLabel === "Reconectando" ? "is-reconnecting" : ""}`} role="status">
          {connectionLabel === "Reconectando" ? <RefreshCw className="obs-spin" size={12} /> : <Radio size={12} />}
          {connectionLabel}
        </span>
      </form>

      <nav className="obs-status-strip" aria-label="Agrupar Runs por estado">
        <span className="obs-strip-label">Runs</span>
        {([
          ["all", "Todas", summary.all],
          ["active", "Ativas", summary.active],
          ["completed", "Concluídas", summary.completed],
          ["attention", "Atenção", summary.attention],
        ] as const).map(([value, label, count]) => (
          <button
            aria-current={status === value ? "page" : undefined}
            key={value}
            onClick={() => updateSearch({ status: value === "all" ? undefined : value })}
            type="button"
          >
            <span>{label}</span>
            <strong className="mono">{count}</strong>
          </button>
        ))}
      </nav>

      <div className={`obs-workspace${selectedRunId ? " has-selection" : ""}`} data-layout={selectedRunId ? "master-detail" : "list"}>
        <div className="obs-list-pane">
          {runsQuery.isPending ? <ListLoadingState /> : null}
          {runsQuery.isError ? (
            <div className="obs-error-state" role="alert">
              <AlertTriangle size={20} />
              <div>
                <strong>{failure.title}</strong>
                <span>{failure.detail}</span>
              </div>
              <button className="obs-action-button" onClick={() => void runsQuery.refetch()} type="button">Tentar novamente</button>
            </div>
          ) : null}
          {runsQuery.isSuccess && !runs.length ? (
            <PageState icon={<FileWarning size={20} />} title="Nenhuma Run registrada" role="status">
              A lista live está vazia. Nenhuma fixture foi criada pela interface.
            </PageState>
          ) : null}
          {runsQuery.isSuccess && runs.length && !filteredRuns.length ? (
            <PageState icon={<Search size={20} />} title="Nenhuma Run encontrada" role="status">
              Ajuste q, status ou período. Os filtros atuais não retornaram records.
            </PageState>
          ) : null}
          {filteredRuns.length ? (
            <RunList
              onSelect={(runId) => updateSearch({ run: runId })}
              runs={filteredRuns}
              selectedRunId={selectedRunId}
            />
          ) : null}
        </div>
        {selectedRunId ? <div className="obs-split-divider" aria-hidden="true" /> : null}
        <aside className="obs-detail-pane" aria-label="Detalhe da Run selecionada">
          {selectedRunId && detailQuery.isPending ? (
            <PageState icon={<LoaderCircle className="obs-spin" size={20} />} title="Carregando detalhe" role="status">
              Buscando records, eventos, evaluations e execution.
            </PageState>
          ) : null}
          {selectedRunId && (detailQuery.isError || selectedMissing) ? (
            <PageState icon={<AlertTriangle size={20} />} title="Run indisponível" role="alert">
              O parâmetro run não corresponde a um detalhe carregável.
              <button className="obs-text-button" onClick={() => updateSearch({ run: undefined })} type="button">
                Voltar às Runs
              </button>
            </PageState>
          ) : null}
          {detailQuery.data ? (
            <RunDetailPanel
              adapter={adapter}
              data={detailQuery.data}
              executor={executor}
              onBack={() => updateSearch({ run: undefined })}
              onRetried={(runId) => updateSearch({ run: runId })}
              streamError={streamError}
              streamState={streamState}
            />
          ) : null}
        </aside>
      </div>
    </section>
  );
}

export function ObservabilityPage() {
  const search = useSearch({ from: "/observability" }) as ObservabilitySearchState;
  const navigate = useNavigate({ from: "/observability" });
  const { executor } = useBackendRuntime();
  return (
    <ObservabilityWorkspace
      executor={executor}
      search={search}
      onSearchChange={(next) => {
        void navigate({ search: next, replace: true });
      }}
    />
  );
}
