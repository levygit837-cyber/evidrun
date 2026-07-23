from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import yaml

from evidrun.contexts import ContextComposer
from evidrun.contracts import ArtifactRef, EvaluationRecord, EvidenceRef, RunSpec
from evidrun.contracts.compiler import (
    AdmissionService,
    EvaluatorEnvelopeCompiler,
    StudyCompiler,
    SubjectEnvelopeCompiler,
)
from evidrun.contracts.legacy import ExperimentManifestV1Adapter, capability_ref
from evidrun.contracts.runtime import DimensionValue, EvaluationBoundary
from evidrun.evaluations import ExactCauseGrader
from evidrun.experiments import ExperimentManifest
from evidrun.infrastructure.database import Repository
from evidrun.shared.types import new_id, sha256_bytes, utc_now
from evidrun.subject_runners import ScriptedLogInvestigator


class EvidrunService:
    def __init__(self, repository: Repository):
        self.repository = repository
        self.composer = ContextComposer()
        self.runner = ScriptedLogInvestigator()
        self.admission_service = AdmissionService(
            runners=(capability_ref("evidrun.runner", self.runner.name),),
        )

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
            (p for p in dashboard["projects"] if p["name"] == "Context Reliability Lab"),
            None,
        )
        project_id = (
            project["id"]
            if project
            else self.repository.create_project(workspace_id, "Context Reliability Lab").id
        )
        revision = self.repository.save_experiment_revision(
            project_id=project_id, manifest=manifest.model_dump(mode="json")
        )

        package = ExperimentManifestV1Adapter().convert(
            manifest,
            project_id=project_id,
            fixture_path=fixture_path,
        )
        for contract_revision in package.revisions:
            self.repository.save_contract_revision(contract_revision)
        for decision in package.acceptance_decisions():
            self.repository.decide_contract_revision(decision)
        registry = self.repository.contract_registry(project_id)
        run_specs = StudyCompiler(registry).compile(package.study)

        runs: dict[str, dict[str, Any]] = {}
        snapshots: dict[str, dict[str, Any]] = {}
        for spec in run_specs:
            run, snapshot, grade = asyncio.run(self._execute_spec(revision.id, spec, source))
            runs[spec.variant_id] = {"run": run, "grade": grade}
            snapshots[spec.variant_id] = snapshot

        baseline = runs[manifest.baseline_variant]
        candidate_variant = next(
            variant.id for variant in manifest.variants if variant.id != manifest.baseline_variant
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
            "study_revision": package.study.ref.model_dump(mode="json"),
            "comparison_id": comparison.id,
            "baseline_run_id": baseline["run"]["id"],
            "candidate_run_id": candidate["run"]["id"],
            "validity": manifest.validity,
            "context_diff": diff,
        }

    async def _execute_spec(
        self,
        experiment_revision_id: str,
        spec: RunSpec,
        source: str,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        policy = spec.context_policy
        if policy is None:
            raise ValueError("deterministic context benchmark requires a ContextPolicy")

        spec_row = self.repository.save_run_spec(spec)
        admission = self.admission_service.admit(spec)
        admission_row = self.repository.save_admission_record(spec_row.id, admission)
        if admission.decision != "admitted":
            reasons = admission.missing_requirements or admission.denied_policies
            raise ValueError("built-in deterministic RunSpec was rejected: " + ", ".join(reasons))
        row = self.repository.create_run(
            experiment_revision_id=experiment_revision_id,
            variant_id=spec.variant_id,
            runner=self.runner.name,
            objective=spec.goal.instruction,
            repetition=spec.repetition_index,
            run_spec_id=spec_row.id,
            admission_id=admission_row.id,
        )
        run = {"id": row.id, "variant_id": spec.variant_id}
        self.repository.append_event(
            run_id=row.id,
            event_type="run.queued",
            payload={
                "run_id": row.id,
                "variant_id": spec.variant_id,
                "run_spec_digest": spec.digest,
                "admission_digest": admission.digest,
            },
        )
        self.repository.append_event(
            run_id=row.id,
            event_type="run.preparing",
            payload={"scenario_ref": spec.scenario_ref.model_dump(mode="json")},
        )

        snapshot = self.composer.compose(source, policy)
        stored_snapshot = {
            **snapshot,
            "selected_content": (
                "[REDACTED]"
                if spec.capture_policy.default_mode == "redacted"
                else ""
                if spec.capture_policy.default_mode in {"metadata", "disabled"}
                else snapshot["selected_content"]
            ),
        }
        saved_snapshot = self.repository.save_snapshot(row.id, stored_snapshot)
        self.repository.append_event(
            run_id=row.id,
            event_type="context.composed",
            payload={
                "snapshot_id": saved_snapshot.id,
                "policy_id": policy.id,
                "strategy": policy.strategy,
                "source_chars": snapshot["source_chars"],
                "selected_chars": snapshot["selected_chars"],
                "omitted": bool(snapshot["omitted"]),
                "content_hash": snapshot["content_hash"],
            },
        )
        self.repository.append_event(
            run_id=row.id,
            event_type="run.running",
            payload={
                "from_status": "preparing",
                "reason": "context composed and deterministic Subject ready",
            },
        )
        self.repository.update_run(row.id, context_hash=snapshot["content_hash"])
        visible_inputs = tuple(
            item
            for item in spec.scenario.input_bindings
            if item.visibility in {"subject", "subject_and_evaluator"}
        )
        if len(visible_inputs) != 1:
            raise ValueError(
                "deterministic context runner requires exactly one visible Subject input"
            )
        declared_input = visible_inputs[0]
        materialized_input = declared_input.model_copy(
            update={
                "source": ArtifactRef(
                    artifact_id=f"context-snapshot:{saved_snapshot.id}",
                    digest=snapshot["content_hash"],
                    media_type=declared_input.source.media_type,
                    classification=declared_input.source.classification,
                )
            }
        )
        subject_envelope = SubjectEnvelopeCompiler.compile(
            spec,
            admission,
            materialized_inputs=(materialized_input,),
        )
        self.repository.append_event(
            run_id=row.id,
            event_type="subject.invoked",
            payload={
                "runner": self.runner.name,
                "network": "disabled",
                "subject_envelope_digest": subject_envelope.digest,
            },
        )
        result = await self.runner.execute(spec.goal.instruction, snapshot["selected_content"])
        capture_mode = spec.capture_policy.default_mode
        captured_output = "[REDACTED]" if capture_mode == "redacted" else None
        captured_evidence = list(result.evidence) if capture_mode == "raw_encrypted" else []
        captured_metadata = (
            [
                {"key": str(key), "value": value}
                for key, value in result.metadata.items()
                if isinstance(value, (str, int, float, bool))
            ]
            if capture_mode != "disabled"
            else []
        )
        response_event = self.repository.append_event(
            run_id=row.id,
            event_type="subject.responded",
            payload={
                "output": captured_output,
                "output_digest": sha256_bytes(result.output.encode("utf-8")),
                "capture_mode": capture_mode,
                "evidence": captured_evidence,
                "metadata": captured_metadata,
            },
        )
        self.repository.append_event(
            run_id=row.id,
            event_type="run.evaluating",
            payload={
                "from_status": "running",
                "reason": "terminal Subject response captured",
            },
        )
        self.repository.update_run(row.id, output=captured_output)

        evaluator_envelope = EvaluatorEnvelopeCompiler.compile(
            spec, spec.evaluation_plan.stages[0].id
        )
        stage = evaluator_envelope.stage
        expected_parameter = next(item for item in stage.parameters if item.key == "expected")
        expected = str(expected_parameter.value)
        grade = ExactCauseGrader(stage.id, expected).grade(result.output, result.evidence)
        evaluation_record = EvaluationRecord(
            record_id=new_id("eval"),
            run_id=row.id,
            plan_ref=spec.evaluation_plan_ref,
            stage_id=stage.id,
            source_type="deterministic_grader",
            evaluator_ref=stage.evaluator_ref,
            boundary=EvaluationBoundary(
                up_to_event_sequence=response_event.sequence,
                event_hash=response_event.event_hash,
            ),
            dimension_values=(
                DimensionValue(
                    dimension_id=stage.output_dimensions[0],
                    value=bool(grade["passed"]),
                    rationale=str(grade["rationale"]),
                    confidence=1.0,
                    evidence_refs=(EvidenceRef(ref=f"event:{response_event.id}"),),
                ),
            ),
            gate_status="passed" if bool(grade["passed"]) else "failed",
            status="final",
            created_at_utc=utc_now(),
        )
        self.repository.save_evaluation_record(evaluation_record)
        self.repository.save_grade(
            run_id=row.id,
            grader_id=stage.id,
            score=grade["score"],
            passed=grade["passed"],
            rationale=grade["rationale"],
            evidence=[
                item.ref
                for value in evaluation_record.dimension_values
                for item in value.evidence_refs
            ],
        )
        self.repository.append_event(
            run_id=row.id,
            event_type="evaluation.completed",
            payload={
                "evaluation_record_id": evaluation_record.record_id,
                "evaluation_record_digest": evaluation_record.digest,
                "gate_status": evaluation_record.gate_status,
            },
        )
        self.repository.append_event(
            run_id=row.id,
            event_type="run.completed",
            payload={
                "status": "completed",
                "goal_state": (
                    "achieved"
                    if bool(result.metadata.get("marker_visible")) and bool(result.evidence)
                    else "not_achieved"
                ),
                "terminal_cause": "terminal subject response evaluated",
                "evaluation_record_refs": [evaluation_record.record_id],
            },
        )
        self.repository.update_run(
            row.id,
            output=captured_output,
            context_hash=snapshot["content_hash"],
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
