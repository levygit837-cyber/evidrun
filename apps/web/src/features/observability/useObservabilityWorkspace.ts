import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ObservabilityAdapter, RunStreamState } from "../../data/contracts";
import {
  TERMINAL_RUN_STATUSES,
  type DetailData,
  type ListFailureKind,
  type ObservabilitySearchState,
  cleanSearchState,
  filterRuns,
  mergeEvents,
  normalizePeriodFilter,
  normalizeStatusFilter,
  summarizeRuns,
} from "./observabilityModel";

/**
 * Queries, live stream and filter state for the Observability workspace. The popover refs are
 * returned so the view can keep its Escape and outside-pointer dismissal wired to real nodes.
 */
export function useObservabilityWorkspace({
  adapter,
  search,
  onSearchChange,
}: {
  adapter: ObservabilityAdapter;
  search: ObservabilitySearchState;
  onSearchChange(next: ObservabilitySearchState): void;
}) {
  const queryClient = useQueryClient();
  const runsQuery = useQuery({ queryKey: ["observability", "runs"], queryFn: adapter.listRuns });
  const selectedRunId = search.run;
  const detailQuery = useQuery({
    queryKey: ["observability", "run", selectedRunId],
    enabled: Boolean(selectedRunId),
    queryFn: async (): Promise<DetailData> => {
      const runId = selectedRunId!;
      const [run, events, evaluations, checkpoints] = await Promise.all([
        adapter.getRun(runId),
        adapter.getEvents(runId),
        adapter.getEvaluations(runId),
        adapter.getCheckpoints(runId),
      ]);
      return { run, events: mergeEvents(run.events, events), evaluations, checkpoints };
    },
  });
  const [streamState, setStreamState] = useState<RunStreamState>("closed");
  const [streamError, setStreamError] = useState<string | null>(null);
  const [moreFiltersOpen, setMoreFiltersOpen] = useState(false);
  const moreFiltersRef = useRef<HTMLDivElement>(null);
  const moreFiltersButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!moreFiltersOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setMoreFiltersOpen(false);
      moreFiltersButtonRef.current?.focus();
    };
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (event.target instanceof Node && !moreFiltersRef.current?.contains(event.target)) {
        setMoreFiltersOpen(false);
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
    };
  }, [moreFiltersOpen]);

  useEffect(() => {
    if (!selectedRunId) {
      setStreamState("closed");
      setStreamError(null);
      return;
    }
    setStreamError(null);
    return adapter.stream.subscribe(selectedRunId, {
      onEvent(event) {
        queryClient.setQueryData<DetailData>(
          ["observability", "run", selectedRunId],
          (current) => current ? { ...current, events: mergeEvents(current.events, [event]) } : current,
        );
        if (TERMINAL_RUN_STATUSES.has(event.type.replace("run.", ""))) {
          void queryClient.invalidateQueries({ queryKey: ["observability", "runs"] });
          void queryClient.invalidateQueries({ queryKey: ["observability", "run", selectedRunId] });
        }
      },
      onState: setStreamState,
      onError(error) {
        setStreamError(`Stream interrompido: ${error.message}. A reconexão permanece ativa.`);
      },
    });
  }, [adapter, queryClient, selectedRunId]);

  const runs = runsQuery.data ?? [];
  const filteredRuns = useMemo(() => filterRuns(runs, search), [runs, search]);
  const summary = useMemo(() => summarizeRuns(runs), [runs]);
  const failureKind: ListFailureKind = runsQuery.error instanceof TypeError
    ? "disconnected"
    : "endpoint";

  return {
    runsQuery,
    detailQuery,
    runs,
    filteredRuns,
    summary,
    failureKind,
    selectedRunId,
    selectedMissing: Boolean(
      selectedRunId && runsQuery.isSuccess && !runs.some((run) => run.id === selectedRunId),
    ),
    status: normalizeStatusFilter(search.status),
    period: normalizePeriodFilter(search.period),
    filtersActive: Boolean(search.q || search.status || search.period),
    streamState,
    streamError,
    moreFiltersOpen,
    setMoreFiltersOpen,
    moreFiltersRef,
    moreFiltersButtonRef,
    updateSearch(patch: Partial<ObservabilitySearchState>) {
      onSearchChange(cleanSearchState({ ...search, ...patch }));
    },
    clearFilters() {
      onSearchChange(cleanSearchState({ run: search.run }));
    },
  };
}
