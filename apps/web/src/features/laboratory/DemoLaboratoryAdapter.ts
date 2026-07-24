import type { LabUiEvent, LaboratoryAdapter } from "../../data/contracts";

export interface DemoLaboratoryAdapterOptions {
  delayMs?: number;
}

const demoTools = [
  {
    id: "search-repository",
    name: "search_repository",
    durationMs: 180,
    argumentsSummary: 'query: "Run Demo e eventos relacionados"',
    resultSummary: "3 referências demonstrativas encontradas.",
  },
  {
    id: "compile-subject",
    name: "compile_subject",
    durationMs: 220,
    argumentsSummary: "escopo: objetivo e contexto Demo",
    resultSummary: "SubjectEnvelope demonstrativo compilado sem dados externos.",
  },
  {
    id: "inspect-run",
    name: "inspect_run",
    durationMs: 240,
    argumentsSummary: 'run: "run-demo-018"',
    resultSummary: "Cronologia Demo inspecionada; nenhuma Run real foi consultada.",
  },
] as const;

function abortError() {
  return new DOMException("A demonstração foi cancelada.", "AbortError");
}

function wait(delayMs: number, signal: AbortSignal) {
  if (signal.aborted) return Promise.reject(abortError());

  return new Promise<void>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      signal.removeEventListener("abort", onAbort);
      resolve();
    }, delayMs);

    function onAbort() {
      window.clearTimeout(timer);
      reject(abortError());
    }

    signal.addEventListener("abort", onAbort, { once: true });
  });
}

function scenarioFor(input: string) {
  const normalized = input.toLocaleLowerCase("pt-BR");
  if (normalized.includes("falha")) return "failure" as const;
  if (normalized.includes("tool") || normalized.includes("ferramenta")) return "tool" as const;
  return "normal" as const;
}

export class DemoLaboratoryAdapter implements LaboratoryAdapter {
  readonly mode = "demo" as const;
  private readonly delayMs: number;
  private readonly attempts = new Map<string, number>();

  constructor({ delayMs = 140 }: DemoLaboratoryAdapterOptions = {}) {
    this.delayMs = delayMs;
  }

  async *send(input: string, signal: AbortSignal): AsyncIterable<LabUiEvent> {
    const attempt = (this.attempts.get(input) ?? 0) + 1;
    this.attempts.set(input, attempt);
    const scenario = scenarioFor(input);

    await wait(this.delayMs, signal);
    yield { type: "status", source: "demo", label: "Organizando contexto Demo" };
    await wait(this.delayMs, signal);

    if (scenario === "failure" && attempt === 1) {
      yield {
        type: "error",
        source: "demo",
        message: "Falha simulada pelo adapter Demo. Nenhum backend foi acionado.",
      };
      return;
    }

    if (scenario === "tool" || (scenario === "failure" && attempt > 1)) {
      for (const tool of demoTools) {
        yield {
          type: "tool",
          source: "demo",
          id: tool.id,
          name: tool.name,
          status: "running",
          argumentsSummary: tool.argumentsSummary,
        };
        await wait(this.delayMs, signal);
        yield {
          type: "tool",
          source: "demo",
          id: tool.id,
          name: tool.name,
          status: "completed",
          durationMs: tool.durationMs,
          argumentsSummary: tool.argumentsSummary,
          resultSummary: tool.resultSummary,
        };
      }
    }

    yield {
      type: "status",
      source: "demo",
      label: attempt > 1 ? "Validando a nova tentativa Demo" : "Sintetizando draft Demo",
    };
    await wait(this.delayMs, signal);

    yield {
      type: "message",
      source: "demo",
      content:
        attempt > 1
          ? "Draft Demo recuperado na nova tentativa. A falha anterior e esta resposta foram produzidas localmente para validar a interface."
          : "Draft Demo concluído. Esta resposta foi produzida por uma sequência local determinística e não contém resultados de uma Run real.",
    };
    yield { type: "done", source: "demo" };
  }
}
