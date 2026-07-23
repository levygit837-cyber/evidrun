from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

from pydantic import TypeAdapter

from evidrun.contexts import ContextComposer
from evidrun.contracts import (
    AdmissionRecord,
    ArtifactRef,
    CapabilityDescriptorRef,
    GoalStateTerminalResult,
    RunExecutionAttempt,
    RunExecutionJob,
    RunSpec,
    semantic_model_dump,
)
from evidrun.contracts.compiler import SubjectEnvelopeCompiler
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import LeaseLost, Repository
from evidrun.infrastructure.providers import ProviderRequestError
from evidrun.runs.adapters import (
    ArtifactInputMaterializer,
    EvaluationOutcome,
    RuntimeAdapterCatalog,
    SubjectBudgetExceeded,
    ToolTraceSink,
)
from evidrun.shared.ports import SubjectResult
from evidrun.shared.types import Classification, canonical_json, sha256_bytes, utc_now

TERMINAL_RUN_STATUSES = {
    "completed",
    "failed",
    "cancelled",
    "budget_exhausted",
    "guardrail_stopped",
}

_json_object = TypeAdapter(dict[str, object])


class _PersistedToolTrace(ToolTraceSink):
    def __init__(
        self,
        *,
        repository: Repository,
        artifact_store: ArtifactStore,
        run_id: str,
        project_id: str,
        actor_id: str,
        lease: tuple[str, str, str, int],
    ) -> None:
        self.repository = repository
        self.artifact_store = artifact_store
        self.run_id = run_id
        self.project_id = project_id
        self.actor_id = actor_id
        self.lease = lease

    def called(
        self,
        *,
        capability_ref: Any,
        call_id: str,
        arguments: str,
    ) -> None:
        arguments_ref = self.artifact_store.put_ref(
            canonical_json({"raw_arguments": arguments}).encode("utf-8"),
            project_id=self.project_id,
            media_type="application/json",
            classification=Classification.INTERNAL,
        )
        self.repository.append_event(
            run_id=self.run_id,
            event_type="tool.called",
            payload={
                "capability_ref": capability_ref.model_dump(mode="json"),
                "call_id": call_id,
                "input_digest": sha256_bytes(arguments.encode("utf-8")),
                "arguments_ref": arguments_ref.model_dump(mode="json"),
            },
            actor_type="subject",
            actor_id=self.actor_id,
            operation_key=f"tool:{call_id}:called",
            lease=self.lease,
        )

    def completed(
        self,
        *,
        capability_ref: Any,
        call_id: str,
        result: str,
        classification: Classification,
    ) -> None:
        result_ref = self.artifact_store.put_ref(
            result.encode("utf-8"),
            project_id=self.project_id,
            media_type="application/json",
            classification=classification,
        )
        self.repository.append_event(
            run_id=self.run_id,
            event_type="tool.completed",
            payload={
                "capability_ref": capability_ref.model_dump(mode="json"),
                "call_id": call_id,
                "result_ref": result_ref.model_dump(mode="json"),
                "reason": None,
            },
            actor_type="tool",
            actor_id=capability_ref.name,
            operation_key=f"tool:{call_id}:completed",
            lease=self.lease,
        )

    def denied(self, *, call_id: str, reason: str) -> None:
        self.repository.append_event(
            run_id=self.run_id,
            event_type="tool.denied",
            payload={
                "call_id": call_id,
                "decided_by": "runtime-policy",
                "rationale": reason,
            },
            actor_type="system",
            actor_id="runtime-policy",
            operation_key=f"tool:{call_id}:denied",
            lease=self.lease,
        )

    def failed(
        self,
        *,
        capability_ref: Any,
        call_id: str,
        reason: str,
    ) -> None:
        self.repository.append_event(
            run_id=self.run_id,
            event_type="tool.failed",
            payload={
                "capability_ref": capability_ref.model_dump(mode="json"),
                "call_id": call_id,
                "result_ref": None,
                "reason": reason,
            },
            actor_type="tool",
            actor_id=capability_ref.name,
            operation_key=f"tool:{call_id}:failed",
            lease=self.lease,
        )


class RunExecutionCoordinator:
    def __init__(
        self,
        repository: Repository,
        artifact_store: ArtifactStore,
        catalog: RuntimeAdapterCatalog | None = None,
    ) -> None:
        self.repository = repository
        self.artifact_store = artifact_store
        self.catalog = catalog or RuntimeAdapterCatalog()
        if self.catalog.materializer is None:
            self.catalog.materializer = ArtifactInputMaterializer(artifact_store)
        self.catalog.project_id_for_spec = self.repository.project_id_for_run_spec
        self.admission_service = self.catalog.admission_service()
        self.composer = ContextComposer()

    def enqueue(
        self,
        *,
        run_spec_id: str,
        admission_id: str,
        idempotency_key: str,
        retry_of: str | None = None,
        experiment_revision_id: str | None = None,
    ) -> tuple[str, RunExecutionJob]:
        run, job = self.repository.enqueue_run(
            run_spec_id=run_spec_id,
            admission_id=admission_id,
            idempotency_key=idempotency_key,
            retry_of=retry_of,
            experiment_revision_id=experiment_revision_id,
        )
        return run.id, job

    def reject_attempt(
        self,
        job: RunExecutionJob,
        attempt: RunExecutionAttempt,
        *,
        reason_code: str,
    ) -> None:
        """Close a fatal operational job without exposing exception details."""

        self._assert_lease(job, attempt)
        try:
            contracts = self.repository.get_run_contracts(job.run_id)
        except KeyError, ValueError:
            contracts = None
        run = self.repository.get_run(job.run_id)
        if (
            contracts is not None
            and contracts[1].decision == "admitted"
            and contracts[1].run_spec_digest == contracts[0].digest
            and run.status not in TERMINAL_RUN_STATUSES
        ):
            evaluations = self.repository.get_evaluation_records(run.id)
            self.repository.append_event(
                run_id=run.id,
                event_type="run.failed",
                payload={
                    "status": "failed",
                    "goal_result": semantic_model_dump(
                        GoalStateTerminalResult(state="not_assessable")
                    ),
                    "terminal_cause": "Runtime execution could not be completed safely",
                    "evaluation_record_refs": [record.record_id for record in evaluations],
                },
                operation_key="run:terminal",
                lease=self._lease(job, attempt),
                reject_execution_code=reason_code,
            )
            return
        self.repository.reject_lease(
            job_id=job.job_id,
            attempt_id=attempt.attempt_id,
            worker_id=attempt.worker_id,
            lease_generation=attempt.lease_generation,
            reason_code=reason_code,
        )

    async def execute_attempt(
        self,
        job: RunExecutionJob,
        attempt: RunExecutionAttempt,
    ) -> None:
        self._assert_lease(job, attempt)
        run = self.repository.get_run(job.run_id)
        if run.status in TERMINAL_RUN_STATUSES:
            self._complete_lease(job, attempt)
            return
        contracts = self.repository.get_run_contracts(run.id)
        if contracts is None:
            raise ValueError("execution job references a legacy Run without contracts")
        spec, admission = contracts
        if admission.decision != "admitted" or admission.run_spec_digest != spec.digest:
            raise ValueError("execution job contracts are no longer coherent")
        active_admission = self.admission_service.admit(spec)
        if (
            active_admission.decision != "admitted"
            or active_admission.resolved_inventory != admission.resolved_inventory
            or active_admission.workspace_status != admission.workspace_status
            or active_admission.interaction_status != admission.interaction_status
        ):
            raise ValueError("stored admission no longer matches the active runtime catalog")
        subject_adapter = self.catalog.subject_for(spec, admission)
        self.catalog.evaluator_for(spec)

        envelope, materialized_inputs = self._prepare(job, attempt, spec, admission)
        run = self.repository.get_run(run.id)
        if run.status in TERMINAL_RUN_STATUSES:
            self._complete_lease(job, attempt)
            return

        events = self.repository.get_run_events(run.id)
        invocation_count = sum(item["type"] == "subject.invoked" for item in events)
        response_count = sum(item["type"] == "subject.responded" for item in events)
        if invocation_count > response_count:
            completed_call_ids = {
                str(item["payload"]["call_id"])
                for item in events
                if item["type"] in {"tool.completed", "tool.denied", "tool.failed"}
            }
            trace_sink = _PersistedToolTrace(
                repository=self.repository,
                artifact_store=self.artifact_store,
                run_id=run.id,
                project_id=self.repository.project_id_for_run(run.id),
                actor_id=subject_adapter.name,
                lease=self._lease(job, attempt),
            )
            for event in events:
                if (
                    event["type"] == "tool.called"
                    and str(event["payload"]["call_id"]) not in completed_call_ids
                ):
                    trace_sink.failed(
                        capability_ref=CapabilityDescriptorRef.model_validate(
                            event["payload"]["capability_ref"]
                        ),
                        call_id=str(event["payload"]["call_id"]),
                        reason="prior tool execution ended without a durable result",
                    )
            self._terminal(
                job,
                attempt,
                event_type="run.failed",
                goal_result=GoalStateTerminalResult(state="not_assessable"),
                cause="Prior Subject invocation ended without a durable response",
            )
            return
        if response_count:
            self._resume_after_response(job, attempt, spec)
            return

        remaining = self._remaining_wall_seconds(run.id, spec)
        if remaining <= 0:
            self._terminal(
                job,
                attempt,
                event_type="run.budget_exhausted",
                goal_result=GoalStateTerminalResult(state="not_assessable"),
                cause="Run exceeded its max_wall_seconds budget",
            )
            return
        self._assert_lease(job, attempt)
        self.repository.append_event(
            run_id=run.id,
            event_type="subject.invoked",
            payload={
                "runner": subject_adapter.name,
                "network": spec.workspace.network_policy.mode,
                "subject_envelope_digest": envelope.digest,
                "evaluation_guidance_digest": (
                    envelope.evaluation_guidance.digest
                    if envelope.evaluation_guidance is not None
                    else None
                ),
                "provider_profile_id": (admission.resolved_inventory.provider_profile_id),
                "provider_model": admission.resolved_inventory.provider_model,
                "provider_reasoning_effort": (
                    admission.resolved_inventory.provider_reasoning_effort
                ),
                "provider_adapter": admission.resolved_inventory.provider_adapter,
            },
            operation_key="subject:invoked",
            lease=self._lease(job, attempt),
        )
        trace_sink = _PersistedToolTrace(
            repository=self.repository,
            artifact_store=self.artifact_store,
            run_id=run.id,
            project_id=self.repository.project_id_for_run(run.id),
            actor_id=subject_adapter.name,
            lease=self._lease(job, attempt),
        )
        try:
            result = await asyncio.wait_for(
                subject_adapter.execute(
                    envelope,
                    materialized_inputs,
                    trace_sink=trace_sink,
                ),
                timeout=remaining,
            )
        except TimeoutError:
            self._assert_lease(job, attempt)
            self._terminal(
                job,
                attempt,
                event_type="run.budget_exhausted",
                goal_result=GoalStateTerminalResult(state="not_assessable"),
                cause="Run exceeded its max_wall_seconds budget",
            )
            return
        except SubjectBudgetExceeded:
            self._assert_lease(job, attempt)
            self._terminal(
                job,
                attempt,
                event_type="run.budget_exhausted",
                goal_result=GoalStateTerminalResult(state="not_assessable"),
                cause="Run exceeded its max_tool_calls budget",
            )
            return
        except ProviderRequestError as exc:
            self._assert_lease(job, attempt)
            self._terminal(
                job,
                attempt,
                event_type="run.failed",
                goal_result=GoalStateTerminalResult(state="not_assessable"),
                cause=f"Subject provider request failed: {exc.code}",
            )
            return
        except Exception:
            self._assert_lease(job, attempt)
            self._terminal(
                job,
                attempt,
                event_type="run.failed",
                goal_result=GoalStateTerminalResult(state="not_assessable"),
                cause="Subject runner execution failed",
            )
            return

        self._assert_lease(job, attempt)
        response = self._persist_response(job, attempt, spec, result)
        outcome = self.catalog.evaluator_for(spec).evaluate(
            run_id=run.id,
            spec=spec,
            result=result,
            response_event_id=response.id,
            response_sequence=response.sequence,
            response_event_hash=response.event_hash,
            tool_events=tuple(
                item
                for item in self.repository.get_run_events(run.id)
                if item["type"].startswith("tool.")
            ),
            artifact_store=self.artifact_store,
            project_id=self.repository.project_id_for_run(run.id),
        )
        self._persist_evaluation(job, attempt, outcome)
        self._terminal(
            job,
            attempt,
            event_type="run.completed",
            goal_result=outcome.goal_result,
            cause="terminal Subject response evaluated",
        )

    def _prepare(
        self,
        job: RunExecutionJob,
        attempt: RunExecutionAttempt,
        spec: RunSpec,
        admission: AdmissionRecord,
    ) -> tuple[Any, dict[str, str]]:
        run = self.repository.get_run(job.run_id)
        if run.status not in {"queued", "preparing", "running", "evaluating"}:
            raise ValueError(f"Run cannot be prepared while {run.status}")

        try:
            envelope_record = self.repository.get_subject_envelope(run.id)
            envelope = envelope_record.envelope
        except KeyError:
            visible_inputs = tuple(
                item
                for item in spec.scenario.input_bindings
                if item.visibility in {"subject", "subject_and_evaluator"}
            )
            if len(visible_inputs) != 1 or spec.context_policy is None:
                raise ValueError(
                    "admitted deterministic Run has unsupported Subject inputs"
                ) from None
            declared = visible_inputs[0]
            if self.catalog.materializer is None:
                raise ValueError("active catalog has no ArtifactInputMaterializer") from None
            project_id = self.repository.project_id_for_run(run.id)
            source = self.catalog.materializer.resolve_text(
                declared.source,
                project_id=project_id,
            )
            snapshot = self.composer.compose(source, spec.context_policy)
            selected = str(snapshot["selected_content"])
            materialized_ref = self.artifact_store.put_ref(
                selected.encode("utf-8"),
                project_id=project_id,
                media_type=declared.source.media_type,
                classification=declared.source.classification,
            )
            stored_snapshot = {
                **snapshot,
                "selected_content": (
                    "[REDACTED]"
                    if spec.capture_policy.default_mode == "redacted"
                    else ""
                    if spec.capture_policy.default_mode in {"metadata", "disabled"}
                    else selected
                ),
            }
            materialized = declared.model_copy(update={"source": materialized_ref})
            envelope = SubjectEnvelopeCompiler.compile(
                spec, admission, materialized_inputs=(materialized,)
            )
            self.repository.prepare_run_execution(
                run_id=run.id,
                spec=spec,
                admission=admission,
                snapshot=stored_snapshot,
                envelope=envelope,
                lease=self._lease(job, attempt),
            )

        materialized_inputs = {
            item.id: self.artifact_store.get_verified(
                item.source,
                project_id=self.repository.project_id_for_run(run.id),
            ).decode("utf-8")
            for item in envelope.inputs
        }
        run = self.repository.get_run(run.id)
        if run.status == "preparing":
            self._assert_lease(job, attempt)
            self.repository.append_event(
                run_id=run.id,
                event_type="run.running",
                payload={
                    "from_status": "preparing",
                    "reason": "SubjectEnvelope materialized and runner adapter ready",
                },
                operation_key="run:running",
                lease=self._lease(job, attempt),
            )
        return envelope, materialized_inputs

    def _persist_response(
        self,
        job: RunExecutionJob,
        attempt: RunExecutionAttempt,
        spec: RunSpec,
        result: SubjectResult,
    ) -> Any:
        run_id = job.run_id
        capture_mode = spec.capture_policy.default_mode
        captured_output = "[REDACTED]" if capture_mode == "redacted" else None
        captured_metadata = (
            [
                {"key": str(key), "value": value}
                for key, value in result.metadata.items()
                if isinstance(value, (str, int, float, bool))
            ]
            if capture_mode != "disabled"
            else []
        )
        output_ref: ArtifactRef | None = None
        captured_evidence: list[str] = []
        if capture_mode == "raw_encrypted":
            result_document = {
                "output": result.output,
                "evidence": list(result.evidence),
                "metadata": captured_metadata,
            }
            output_ref = self.artifact_store.put_ref(
                canonical_json(result_document).encode("utf-8"),
                project_id=self.repository.project_id_for_run(run_id),
                media_type="application/json",
                classification=Classification.SENSITIVE,
                raw_authorized=True,
                ttl_days=spec.capture_policy.sensitive_ttl_days,
            )
            captured_evidence = [f"artifact:{output_ref.artifact_id}"]
        return self.repository.save_subject_response(
            run_id=run_id,
            spec=spec,
            response_payload={
                "output": captured_output,
                "output_ref": (
                    output_ref.model_dump(mode="json") if output_ref is not None else None
                ),
                "output_digest": sha256_bytes(result.output.encode("utf-8")),
                "capture_mode": capture_mode,
                "evidence": captured_evidence,
                "metadata": captured_metadata,
            },
            captured_output=captured_output,
            lease=self._lease(job, attempt),
        )

    def _persist_evaluation(
        self,
        job: RunExecutionJob,
        attempt: RunExecutionAttempt,
        outcome: EvaluationOutcome,
    ) -> None:
        self._assert_lease(job, attempt)
        lease = self._lease(job, attempt)
        self.repository.save_deterministic_evaluation(
            record=outcome.record,
            score=outcome.score,
            passed=outcome.passed,
            rationale=outcome.rationale,
            evidence=outcome.evidence,
            lease=lease,
        )

    def _resume_after_response(
        self,
        job: RunExecutionJob,
        attempt: RunExecutionAttempt,
        spec: RunSpec,
    ) -> None:
        records = self.repository.get_evaluation_records(job.run_id)
        run = self.repository.get_run(job.run_id)
        if run.status == "running":
            self.repository.append_event(
                run_id=job.run_id,
                event_type="run.evaluating",
                payload={
                    "from_status": "running",
                    "reason": "persisted Subject response is being reconciled",
                },
                operation_key="run:evaluating",
                lease=self._lease(job, attempt),
            )
        if not records:
            events = self.repository.get_run_events(job.run_id)
            response_event = next(item for item in events if item["type"] == "subject.responded")
            payload = response_event["payload"]
            output_ref_document = payload.get("output_ref")
            if output_ref_document is None:
                self._terminal(
                    job,
                    attempt,
                    event_type="run.failed",
                    goal_result=GoalStateTerminalResult(state="not_assessable"),
                    cause=("Subject response cannot be deterministically recovered for evaluation"),
                )
                return
            output_ref = ArtifactRef.model_validate(output_ref_document)
            result_document = _json_object.validate_json(
                self.artifact_store.get_verified(
                    output_ref,
                    project_id=self.repository.project_id_for_run(job.run_id),
                )
            )
            output_value = result_document.get("output")
            evidence_value = result_document.get("evidence")
            metadata_value = result_document.get("metadata")
            if (
                not isinstance(output_value, str)
                or not isinstance(evidence_value, list)
                or not all(isinstance(item, str) for item in cast(list[object], evidence_value))
                or not isinstance(metadata_value, list)
            ):
                raise ValueError("persisted Subject result has an invalid shape")
            metadata: dict[str, str | int | float | bool] = {}
            for item_value in cast(list[object], metadata_value):
                if not isinstance(item_value, dict):
                    continue
                item = cast(dict[str, object], item_value)
                key = item.get("key")
                value = item.get("value")
                if (
                    set(item) == {"key", "value"}
                    and isinstance(key, str)
                    and isinstance(value, (str, int, float, bool))
                ):
                    metadata[key] = value
            result = SubjectResult(
                output=output_value,
                evidence=tuple(cast(list[str], evidence_value)),
                metadata=metadata,
            )
            outcome = self.catalog.evaluator_for(spec).evaluate(
                run_id=job.run_id,
                spec=spec,
                result=result,
                response_event_id=str(response_event["event_id"]),
                response_sequence=int(response_event["sequence"]),
                response_event_hash=str(response_event["event_hash"]),
                tool_events=tuple(item for item in events if item["type"].startswith("tool.")),
                artifact_store=self.artifact_store,
                project_id=self.repository.project_id_for_run(job.run_id),
            )
            self._persist_evaluation(job, attempt, outcome)
            self._terminal(
                job,
                attempt,
                event_type="run.completed",
                goal_result=outcome.goal_result,
                cause="persisted Subject response evaluated after recovery",
            )
            return
        for record in records:
            dimension = record.dimension_values[0]
            passed = bool(dimension.value)
            self.repository.save_grade(
                run_id=record.run_id,
                grader_id=record.stage_id,
                score=1.0 if passed else 0.0,
                passed=passed,
                rationale=dimension.rationale,
                evidence=tuple(item.ref for item in dimension.evidence_refs),
                lease=self._lease(job, attempt),
            )
            self.repository.append_event(
                run_id=job.run_id,
                event_type="evaluation.completed",
                payload={
                    "evaluation_record_id": record.record_id,
                    "evaluation_record_digest": record.digest,
                    "gate_status": record.gate_status,
                },
                operation_key=f"evaluation:{record.stage_id}:completed",
                lease=self._lease(job, attempt),
            )
        passed = all(record.gate_status != "failed" for record in records)
        del spec
        self._terminal(
            job,
            attempt,
            event_type="run.completed",
            goal_result=GoalStateTerminalResult(state="achieved" if passed else "not_achieved"),
            cause="persisted deterministic evaluation reconciled",
        )

    def _terminal(
        self,
        job: RunExecutionJob,
        attempt: RunExecutionAttempt,
        *,
        event_type: str,
        goal_result: GoalStateTerminalResult,
        cause: str,
    ) -> None:
        run = self.repository.get_run(job.run_id)
        if run.status in TERMINAL_RUN_STATUSES:
            self._complete_lease(job, attempt)
            return
        self._assert_lease(job, attempt)
        if run.status not in TERMINAL_RUN_STATUSES:
            evaluations = self.repository.get_evaluation_records(run.id)
            self.repository.append_event(
                run_id=run.id,
                event_type=event_type,
                payload={
                    "status": event_type.removeprefix("run."),
                    "goal_result": semantic_model_dump(goal_result),
                    "terminal_cause": cause,
                    "evaluation_record_refs": [record.record_id for record in evaluations],
                },
                operation_key="run:terminal",
                lease=self._lease(job, attempt),
                complete_execution=True,
            )

    def _remaining_wall_seconds(self, run_id: str, spec: RunSpec) -> float:
        running = next(
            item for item in self.repository.get_run_events(run_id) if item["type"] == "run.running"
        )
        started = datetime.fromisoformat(str(running["occurred_at_utc"]))
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        elapsed = (utc_now() - started).total_seconds()
        return max(0.0, spec.budgets.max_wall_seconds - elapsed)

    def _assert_lease(self, job: RunExecutionJob, attempt: RunExecutionAttempt) -> None:
        self.repository.assert_lease(
            job_id=job.job_id,
            attempt_id=attempt.attempt_id,
            worker_id=attempt.worker_id,
            lease_generation=attempt.lease_generation,
        )

    @staticmethod
    def _lease(job: RunExecutionJob, attempt: RunExecutionAttempt) -> tuple[str, str, str, int]:
        return (
            job.job_id,
            attempt.attempt_id,
            attempt.worker_id,
            attempt.lease_generation,
        )

    def _complete_lease(self, job: RunExecutionJob, attempt: RunExecutionAttempt) -> None:
        try:
            self.repository.complete_lease(
                job_id=job.job_id,
                attempt_id=attempt.attempt_id,
                worker_id=attempt.worker_id,
                lease_generation=attempt.lease_generation,
            )
        except LeaseLost:
            execution = self.repository.get_run_execution(job.run_id)
            if execution is None or execution[0].status != "completed":
                raise
