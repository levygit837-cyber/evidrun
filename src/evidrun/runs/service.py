from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import yaml

from evidrun.contexts import ContextComposer
from evidrun.evaluations import ExactCauseGrader
from evidrun.experiments import ExperimentManifest
from evidrun.infrastructure.database import Repository
from evidrun.shared.types import utc_now
from evidrun.subject_runners import ScriptedLogInvestigator


class EvidrunService:
    def __init__(self, repository: Repository):
        self.repository = repository
        self.composer = ContextComposer()
        self.runner = ScriptedLogInvestigator()

    def bootstrap_demo(self, benchmark_root: Path) -> dict[str, Any]:
        manifest_path = benchmark_root / "experiments" / "crl-ctx-002-demo.yaml"
        fixture_path = benchmark_root / "scenarios" / "crl-ctx-002" / "fixtures" / "long.log"
        manifest = ExperimentManifest.model_validate(yaml.safe_load(manifest_path.read_text()))
        source = fixture_path.read_text()

        dashboard = self.repository.latest_dashboard()
        if dashboard["workspaces"]:
            workspace_id = dashboard["workspaces"][0]["id"]
        else:
            workspace_id = self.repository.create_workspace("Laboratório local").id
        project = next(
            (p for p in dashboard["projects"] if p["name"] == "Context Reliability Lab"), None
        )
        project_id = (
            project["id"]
            if project
            else self.repository.create_project(workspace_id, "Context Reliability Lab").id
        )
        revision = self.repository.save_experiment_revision(
            project_id=project_id, manifest=manifest.model_dump(mode="json")
        )

        runs: dict[str, dict[str, Any]] = {}
        snapshots: dict[str, dict[str, Any]] = {}
        for variant in manifest.variants:
            run, snapshot, grade = asyncio.run(
                self._execute_variant(revision.id, manifest, variant.id, source)
            )
            runs[variant.id] = {"run": run, "grade": grade}
            snapshots[variant.id] = snapshot

        baseline = runs[manifest.baseline_variant]
        candidate_variant = next(
            variant.id
            for variant in manifest.variants
            if variant.id != manifest.baseline_variant
        )
        candidate = runs[candidate_variant]
        baseline_score = float(baseline["grade"]["score"])
        candidate_score = float(candidate["grade"]["score"])
        diff = self.composer.diff(
            snapshots[manifest.baseline_variant], snapshots[candidate_variant]
        )
        report = self._build_report(
            manifest=manifest,
            baseline_run=baseline["run"],
            candidate_run=candidate["run"],
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            context_diff=diff,
        )
        comparison = self.repository.save_comparison(
            experiment_revision_id=revision.id,
            baseline_run_id=baseline["run"]["id"],
            candidate_run_id=candidate["run"]["id"],
            primary_variable=manifest.primary_variable,
            validity=manifest.validity,
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            report_markdown=report,
        )
        return {
            "experiment_revision_id": revision.id,
            "comparison_id": comparison.id,
            "baseline_run_id": baseline["run"]["id"],
            "candidate_run_id": candidate["run"]["id"],
            "validity": manifest.validity,
            "context_diff": diff,
        }

    async def _execute_variant(
        self,
        experiment_revision_id: str,
        manifest: ExperimentManifest,
        variant_id: str,
        source: str,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        variant = next(item for item in manifest.variants if item.id == variant_id)
        policy = manifest.policy_for(variant)
        row = self.repository.create_run(
            experiment_revision_id=experiment_revision_id,
            variant_id=variant.id,
            runner=self.runner.name,
            objective=manifest.objective,
        )
        run = {"id": row.id, "variant_id": variant.id}
        self.repository.append_event(run_id=row.id, event_type="run.queued", payload=run)
        self.repository.update_run(row.id, status="preparing")
        self.repository.append_event(
            run_id=row.id,
            event_type="run.preparing",
            payload={"scenario_refs": list(manifest.scenario_refs)},
        )
        snapshot = self.composer.compose(source, policy)
        saved_snapshot = self.repository.save_snapshot(row.id, snapshot)
        self.repository.append_event(
            run_id=row.id,
            event_type="context.composed",
            payload={
                "snapshot_id": saved_snapshot.id,
                "policy_id": policy.id,
                "strategy": policy.strategy,
                "source_chars": snapshot["source_chars"],
                "selected_chars": snapshot["selected_chars"],
                "omitted": snapshot["omitted"],
                "content_hash": snapshot["content_hash"],
            },
        )
        self.repository.update_run(row.id, status="running", context_hash=snapshot["content_hash"])
        self.repository.append_event(
            run_id=row.id,
            event_type="subject.invoked",
            payload={"runner": self.runner.name, "network": "disabled"},
        )
        result = await self.runner.execute(manifest.objective, snapshot["selected_content"])
        self.repository.append_event(
            run_id=row.id,
            event_type="subject.responded",
            payload={
                "output": result.output,
                "evidence": list(result.evidence),
                "metadata": dict(result.metadata),
            },
        )
        self.repository.update_run(row.id, status="grading", output=result.output)
        grader_spec = manifest.graders[0]
        grade = ExactCauseGrader(grader_spec.id, grader_spec.expected).grade(
            result.output, result.evidence
        )
        saved_grade = self.repository.save_grade(
            run_id=row.id,
            grader_id=grader_spec.id,
            score=grade["score"],
            passed=grade["passed"],
            rationale=grade["rationale"],
            evidence=grade["evidence"],
        )
        self.repository.append_event(
            run_id=row.id,
            event_type="grader.completed",
            payload={"grade_id": saved_grade.id, **grade},
        )
        self.repository.update_run(
            row.id,
            status="completed",
            output=result.output,
            context_hash=snapshot["content_hash"],
            completed_at=utc_now(),
        )
        self.repository.append_event(
            run_id=row.id,
            event_type="run.completed",
            payload={"status": "completed", "score": grade["score"]},
        )
        return run, snapshot, grade

    @staticmethod
    def _build_report(
        *,
        manifest: ExperimentManifest,
        baseline_run: dict[str, Any],
        candidate_run: dict[str, Any],
        baseline_score: float,
        candidate_score: float,
        context_diff: dict[str, Any],
    ) -> str:
        return f"""# Relatório — {manifest.title}

## Resultado

- Variável primária: `{manifest.primary_variable}`
- Validade: `{manifest.validity}`
- Baseline: `{baseline_score:.2f}`
- Candidate: `{candidate_score:.2f}`
- Delta: `{candidate_score - baseline_score:+.2f}`

## Mudança observada

```json
{json.dumps(context_diff, ensure_ascii=False, indent=2)}
```

## Evidências

- Baseline run: `{baseline_run['id']}`
- Candidate run: `{candidate_run['id']}`

## Limitação

Este experimento usa um runner determinístico para verificar a infraestrutura do Evidrun. O
resultado não demonstra capacidade, estabilidade ou melhoria de um modelo de linguagem.
"""
