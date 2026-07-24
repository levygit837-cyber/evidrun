# Fixture mínima de fronteiras de evidência

Estado: fixture de teste, não contrato normativo.

Autoridade: research.

Origem: `docs/research/run-scenario-discovery/`, especialmente o cenário A e a matriz de lifecycle
e ownership.

Esta fixture transforma a menor hipótese útil do discovery em uma Run offline e determinística:
um único Artifact interno contém um marcador de causa-raiz, um Subject scripted o identifica e um
grader exato ancora sua avaliação no evento `subject.responded`.

Ela usa apenas contratos e Runtime Kernel já existentes. Não adiciona schema público, endpoint,
tabela, migration, provider, capability, checkpoint, finding, judge ou autoridade humana de
produção. A aceitação das revisions ocorre somente no teste pelo verifier estreito de
`tests/support`.

## Arquivos

- `incident.log`: único input materializado para o Subject.
- `expected-run.md`: projeção humana esperada; é derivada e não substitui os records canônicos.
- `tests/acceptance/test_run_evidence_boundaries_fixture.py`: compila, admite, executa e verifica a
  Run; depois compara a projeção normalizada com o golden Markdown.

## Fronteiras exercitadas

| Dado | Owner | Visível ao Subject | Presente na projeção |
| --- | --- | --- | --- |
| Study intent | Control Plane de teste | Não | Não |
| Goal | Goal revision / RunSpec | Sim | Sim |
| Input bruto | Artifact store | Somente após materialização admitida | Não |
| ArtifactRef | Scenario / SubjectEnvelope | Sim | Somente identidade e classificação |
| Oracle `SEARCH_INDEX_LAG` | EvaluationPlan | Não | Não |
| Eventos de lifecycle | Ledger append-only | Não automaticamente | Tipos em ordem |
| EvaluationRecord | Evaluation service | Não durante a Run | Stage, source e gate |
| RunRecord | Runtime Kernel | Não | Relações verificadas, sem IDs efêmeros |

UUIDv7, timestamps e digests variam por execução. O teste verifica esses valores diretamente contra
RunSpec, AdmissionRecord e RunRecord, mas a projeção golden os representa semanticamente. Isso
mantém a saída reproduzível sem transformar placeholders em fonte de verdade.

## Reprodução

Na raiz do repositório:

```bash
UV_CACHE_DIR=/private/tmp/evidrun-uv-cache \
  uv run --extra dev pytest tests/acceptance/test_run_evidence_boundaries_fixture.py -q
```

O teste deve produzir `1 passed` sem rede e sem chamada a provider.

## O que permanece fora desta fixture

- testar schemas fechados candidatos contra os cenários A, B e C;
- decidir composição e omissão de módulos em um contrato sucessor;
- contratar mounts e grants do execution workspace;
- definir projectors públicos e versionar seus outputs;
- definir supersession de avaliações e migração de projections;
- implementar capabilities condicionais somente após threat model e gates próprios.
