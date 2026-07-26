---
id: benchmark-live-read-agent
type: benchmark
title: Benchmark live de recuperação fundamentada por tool
status: implemented
authority: non-normative
volatility: current
owner: evaluation
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: runtime-kernel@2
sources:
  - https://platform.openai.com/docs/guides/evals
  - https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
  - https://taskdev.metr.org/specification/
  - https://taskdev.metr.org/quality-assurance/
  - https://arxiv.org/abs/2505.23419
supersedes: []
superseded_by: null
implementation_refs:
  - tests/support/live_read_study.py
  - tests/live/test_real_agent_benchmark.py
  - tests/live/probe_provider_tool_protocol.py
verification_refs:
  - tests/integration/test_live_agent_runtime.py
  - tests/live/test_real_agent_benchmark.py
---

# Objetivo e limite da evidência

Este é um teste transversal do Runtime Kernel, não uma medição de conhecimento geral do modelo. A
tarefa mede se um Subject real consegue usar uma tool admitida para recuperar um fato de um corpus
autorizado, emitir uma citation verificável e atravessar fila, lease, persistência, avaliação e
Bundle v3.

O desenho segue quatro princípios recorrentes na literatura prática de evals:

- declarar tarefa, input e grader separadamente;
- usar exemplos representativos e rubric determinística quando o resultado admite verificação
  exata;
- guardar transcript/tool trace para diagnóstico, avaliando principalmente o outcome e não um único
  caminho ideal;
- usar corpus fresco e ambiente reproduzível para reduzir contaminação.

Uma Run bem-sucedida prova integração naquele ambiente e momento. Alegações de capacidade ou
comparação entre modelos exigem várias repetições, distribuição de seeds/nonces e relato de
variância.

# Scenario

Cada execução gera um memo sintético novo de 65 linhas. O corpus contém:

- observações neutras;
- uma hipótese anterior explicitamente rejeitada;
- um control code inativo;
- uma linha fechada `ROOT_CAUSE_CODE=<nonce fresco>`;
- `ROOT_CAUSE_STATUS=CONFIRMED`;
- distractors depois da resposta.

O nonce não entra no Goal nem no SubjectEnvelope. O Subject recebe somente o objective, o inventário
com `input_id=incident-memo` e o schema de `read_text`.

# Ação permitida

```text
read_text(input_id, start_line, max_lines)
```

A tool só lê inputs já materializados no SubjectEnvelope, devolve linhas numeradas e limita cada
chamada a 80 linhas. Não há ferramenta de escrita, shell, rede arbitrária, path, URL ou lookup por
artifact ID. O budget live permite no máximo duas chamadas para observar tanto leitura direta quanto
uma eventual correção.

# Output e scoring

O output aceito possui exatamente:

```json
{
  "answer": "<ROOT_CAUSE_CODE>",
  "evidence": [
    {"input_id": "incident-memo", "line": 36}
  ]
}
```

O grader atribui `true` somente quando todas as condições são satisfeitas:

1. o JSON tem exatamente as duas chaves;
2. `answer` é igual ao expected oculto;
3. existe `tool.completed` de uma capability admitida;
4. seu `result_ref` possui digest e shape válidos;
5. a citation aponta para uma linha realmente devolvida nessa chamada;
6. a linha, após trim, é exatamente `ROOT_CAUSE_CODE=<answer>`.

Resposta correta com citation inventada, campo extra, distractor, linha que apenas menciona ou nega o
expected e texto fora do JSON recebem `false`. Provider indisponível, timeout, lease perdido ou
integridade canônica impedida produzem `not_assessable`, não score zero inventado.

# Execução live

O teste é opt-in porque consome um provider real e Keychain local:

```bash
EVIDRUN_RUN_LIVE_AGENT=1 \
EVIDRUN_LIVE_DATA_DIR=/tmp/evidrun-live \
uv run pytest -vv -s tests/live/test_real_agent_benchmark.py
```

O processo preparador usa `TestHumanAttestationVerifier` importado somente de `tests/support`, registra
e aceita as revisions, compila, admite e enfileira. Em seguida ele fecha o Database. O teste inicia
`python -m evidrun.entrypoints.worker.app --once` em subprocesso, reabre o SQLite em outra instância,
verifica ledger/evaluation, decripta o output somente para a asserção local, exporta Bundle v3 e roda
o verificador isolado.

O worker, API, CLI, Settings e composição de produção continuam usando
`UnavailableHumanAttestationVerifier`. Nenhum environment variable, endpoint ou campo de RunSpec
seleciona o verifier de teste.

# Matriz automatizada

`tests/integration/test_live_agent_runtime.py` usa provider fake somente para tornar falhas
reproduzíveis. Ele cobre:

- happy path com tool trace, output cifrado, evaluation e Bundle v3;
- pedido de `input_id` fora do envelope com `tool.denied`;
- estouro de `max_tool_calls` como `run.budget_exhausted`;
- citation não fundamentada, distractor e campo extra;
- crash depois de resposta durável, dispose/reopen do SQLite e avaliação sem reinvocação;
- network, capture e tool budget incompatíveis rejeitados na admissão.

Os testes gerais do Runtime Kernel complementam essa matriz com disputa de claim, heartbeat, lease
expirado, runner exception, timeout, stale fencing, retry como nova Run, idempotência, terminal
existente, divergência RunSpec/admission, ArtifactStore adulterado e migração SQLite.

# Interpretação do trace

O caminho nominal é:

```text
run.queued
run.preparing
context.composed
capability.offered
run.running
subject.invoked
(tool.called -> tool.completed){1,2}
subject.responded
run.evaluating
evaluation.completed
run.completed
```

O trace contém refs e digests, provider/model/reasoning, contagem de rounds/tool calls e usage. Ele
não contém credencial, raw reasoning ou hidden expected. O Bundle continua auditável e
`references_only`; não é replay nem portabilidade de todos os blobs.
