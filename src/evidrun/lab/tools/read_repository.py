"""Repository de leitura escopado usado pelas tools do Lab Agent.

A fronteira recebe o scope validado e projeta somente os campos públicos do catálogo v1.
Queries de agregação usam expressões SQLAlchemy escolhidas por allowlist; nenhum identificador
produzido pelo modelo entra no texto SQL.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from evidrun.contracts import EvaluationRecord, semantic_model_dump
from evidrun.contracts.lab_agent.errors import LabAgentTargetSituation
from evidrun.contracts.lab_agent.scope import LabAgentFocusKind, LabAgentSessionScope
from evidrun.infrastructure.database.models import (
    AdmissionRecordRow,
    ComparisonRow,
    ContractRevisionRow,
    ExperimentRevisionRow,
    GradeRow,
    ProjectRow,
    RunEventRow,
    RunRow,
    RunSpecRow,
)
from evidrun.infrastructure.database.read_model import ReadModel
from evidrun.infrastructure.database.timestamps import aware_utc
from evidrun.infrastructure.database.unit_of_work import UnitOfWork
from evidrun.lab.tools.read_port import (
    Readable,
    is_classified,
    reject_classification,
    reject_project_required,
    reject_target,
)
from evidrun.lab.tools.registry import CapabilityCatalog, CapabilityCatalogSource


class SqlAlchemyLabReadRepository:
    """Adapter read-only sobre o ReadModel e as tabelas existentes."""

    #: Toda métrica conta Run distinta, nunca linha do outerjoin com GradeRow. Uma Run com
    #: dois grades produz duas linhas de junção: sem `distinct`, `run_count` devolvia 2 para
    #: uma única Run, e `sample_size` afirmava uma amostra que não existe. O contrato trata
    #: `sample_size` como validade do grupo, então inflá-lo mente sobre a evidência.
    _METRICS: Mapping[str, Callable[[], Any]] = {
        "grade_score": lambda: func.avg(GradeRow.score),
        "run_count": lambda: func.count(RunRow.id.distinct()),
        "completion_rate": lambda: func.avg(
            case((RunRow.completed_at.is_not(None), 1.0), else_=0.0)
        ),
    }
    _GROUPS: Mapping[str, Callable[[], Any]] = {
        "status": lambda: RunRow.status,
        "variant_id": lambda: RunRow.variant_id,
        "runner": lambda: RunRow.runner,
    }

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        capability_source: CapabilityCatalogSource,
    ) -> None:
        self._uow = unit_of_work
        self._read_model = ReadModel(unit_of_work)
        self._capability_source = capability_source

    def list_projects(self, scope: LabAgentSessionScope) -> Sequence[Readable]:
        return tuple(
            {"id": item["id"], "name": item["name"], "created_at": item["created_at"]}
            for item in self._read_model.list_projects(scope.workspace_id)
        )

    def read_contract_revision(
        self, scope: LabAgentSessionScope, revision_ref: str
    ) -> Readable:
        with self._uow.session() as session:
            row = session.get(ContractRevisionRow, revision_ref)
            if row is None:
                reject_target(LabAgentTargetSituation.ABSENT, "revision_ref")
            self._require_project(session, scope, row.project_id, "revision_ref")
            if not self._focus_allows_revision(session, scope, row):
                reject_target(LabAgentTargetSituation.SIBLING_PROJECT, "revision_ref")
            revision = self._read_model.get_contract_revision(row.id)
            document = semantic_model_dump(revision)
            if self._contains_classified_content(document):
                reject_classification("revision_ref")
            return {"document": document, "status": row.status, "digest": row.digest}

    def list_runs(
        self, scope: LabAgentSessionScope, *, limit: int, status: str | None
    ) -> Sequence[Readable]:
        project_id = self._project_required(scope)
        with self._uow.session() as session:
            query = self._apply_focus_to_runs(select(RunRow), scope)
            if status is not None:
                query = query.where(RunRow.status == status)
            candidates = list(
                session.scalars(query.order_by(RunRow.created_at.desc(), RunRow.id))
            )
            rows = [
                row for row in candidates if self._project_id_for_run(row.id) == project_id
            ][:limit]
        return tuple(
            {
                "run_id": row.id,
                "run_spec_id": row.run_spec_id,
                "status": row.status,
                "terminal": row.completed_at is not None,
                "created_at": aware_utc(row.created_at).isoformat(),
                "completed_at": aware_utc(row.completed_at).isoformat()
                if row.completed_at
                else None,
            }
            for row in rows
        )

    def read_run(self, scope: LabAgentSessionScope, run_id: str) -> Readable:
        with self._uow.session() as session:
            row = session.get(RunRow, run_id)
            if row is None:
                reject_target(LabAgentTargetSituation.ABSENT, "run_id")
            project_id = self._project_id_for_run(row.id)
            self._require_project(session, scope, project_id, "run_id")
            if not self._focus_allows_run(session, scope, row.id):
                reject_target(LabAgentTargetSituation.SIBLING_PROJECT, "run_id")
            terminal = session.scalar(
                select(RunEventRow)
                .where(
                    RunEventRow.run_id == run_id,
                    RunEventRow.event_type.in_(
                        ("run.completed", "run.failed", "run.budget_exhausted")
                    ),
                )
                .order_by(RunEventRow.sequence.desc())
                .limit(1)
            )
            terminal_cause = None
            if terminal is not None:
                if is_classified(terminal.classification):
                    reject_classification("run_id")
                payload = json.loads(terminal.payload_json)
                terminal_cause = (
                    payload.get("reason") or payload.get("cause") or terminal.event_type
                )
        return {
            "run_id": row.id,
            "status": row.status,
            "lifecycle": "terminal" if row.completed_at else "active",
            "terminal_cause": terminal_cause,
            "run_spec_ref": row.run_spec_id,
            "admission_ref": row.admission_id,
        }

    def read_run_events(
        self,
        scope: LabAgentSessionScope,
        run_id: str,
        *,
        after_sequence: int,
        limit: int,
    ) -> Sequence[Readable]:
        self._require_visible_run(scope, run_id)
        with self._uow.session() as session:
            rows = list(
                session.scalars(
                    select(RunEventRow)
                    .where(
                        RunEventRow.run_id == run_id,
                        RunEventRow.sequence > after_sequence,
                    )
                    .order_by(RunEventRow.sequence)
                    .limit(limit)
                )
            )
        for row in rows:
            if is_classified(row.classification):
                reject_classification("run_id")
        return tuple(
            {
                # Sem `classification`: toda linha que chega aqui sobreviveu à recusa acima,
                # então o campo só ecoaria internal/public. A coluna "Devolve" do contrato v1
                # é "eventos válidos da Run em ordem de sequência"; um campo a mais é
                # superfície que o próximo consumidor passa a poder depender.
                "event_id": row.id,
                "run_id": row.run_id,
                "sequence": row.sequence,
                "type": row.event_type,
                "occurred_at": aware_utc(row.occurred_at).isoformat(),
                "payload": json.loads(row.payload_json),
            }
            for row in rows
        )

    def read_evaluation_records(
        self, scope: LabAgentSessionScope, run_id: str
    ) -> Sequence[Readable]:
        self._require_visible_run(scope, run_id)
        records = self._read_model.get_evaluation_records(run_id)
        return tuple(self._evaluation_projection(item) for item in records)

    def read_comparison(
        self, scope: LabAgentSessionScope, comparison_id: str
    ) -> Readable:
        with self._uow.session() as session:
            row = session.get(ComparisonRow, comparison_id)
            if row is None:
                reject_target(LabAgentTargetSituation.ABSENT, "comparison_id")
            experiment = session.get(ExperimentRevisionRow, row.experiment_revision_id)
            if experiment is None:
                raise ValueError("comparison references an unknown experiment revision")
            self._require_project(session, scope, experiment.project_id, "comparison_id")
            if scope.focus_kind is not None and not (
                scope.focus_kind == LabAgentFocusKind.COMPARISON
                and scope.focus_id == comparison_id
            ):
                reject_target(LabAgentTargetSituation.SIBLING_PROJECT, "comparison_id")
        return {
            # A coluna "Devolve" do contrato v1 é a allowlist desta projeção: variável
            # primária, validade, deltas e refs das Runs. `baseline_score` e
            # `candidate_score` ficam fora porque o delta já é a comparação, e os dois
            # escores brutos são o número de onde ele saiu, não a comparação.
            "comparison_id": row.id,
            "primary_variable": row.primary_variable,
            "validity": row.validity,
            "delta": row.delta,
            "run_refs": [row.baseline_run_id, row.candidate_run_id],
        }

    def read_admission(self, scope: LabAgentSessionScope, admission_id: str) -> Readable:
        with self._uow.session() as session:
            row = session.get(AdmissionRecordRow, admission_id)
            if row is None:
                reject_target(LabAgentTargetSituation.ABSENT, "admission_id")
            record = self._read_model.get_admission_record(admission_id)
            project_id = self._read_model.project_id_for_run_spec(
                self._read_model.get_run_spec(row.run_spec_id)
            )
            self._require_project(session, scope, project_id, "admission_id")
            run_ids = tuple(
                session.scalars(select(RunRow.id).where(RunRow.admission_id == admission_id))
            )
            if scope.focus_kind is not None and not any(
                self._focus_allows_run(session, scope, run_id) for run_id in run_ids
            ):
                reject_target(LabAgentTargetSituation.SIBLING_PROJECT, "admission_id")
        return {
            "decision": record.decision,
            "rejection_codes": [item.reason.code for item in record.issues],
            "issues": [semantic_model_dump(item) for item in record.issues],
            "missing_requirements": list(record.missing_requirements),
        }

    def read_capability_catalog(self) -> CapabilityCatalog:
        return self._capability_source.capability_catalog()

    def aggregate_metrics(
        self,
        scope: LabAgentSessionScope,
        *,
        metric: str,
        group_by: str,
        run_ids: Sequence[str],
    ) -> Sequence[Readable]:
        project_id = self._project_required(scope)
        metric_factory = self._METRICS.get(metric)
        group_factory = self._GROUPS.get(group_by)
        if metric_factory is None or group_factory is None:
            raise ValueError("metric and group_by must come from the declared allowlists")
        metric_expression = metric_factory()
        group_expression = group_factory()
        with self._uow.session() as session:
            candidate_query = (
                select(RunRow.id)
                .join(
                    ExperimentRevisionRow,
                    ExperimentRevisionRow.id == RunRow.experiment_revision_id,
                )
                .where(
                    RunRow.id.in_(tuple(run_ids)),
                    ExperimentRevisionRow.project_id == project_id,
                )
            )
            visible_ids = tuple(
                session.scalars(self._apply_focus_to_runs(candidate_query, scope))
            )
            if set(visible_ids) != set(run_ids):
                reject_target(LabAgentTargetSituation.SIBLING_PROJECT, "run_ids")
            query = (
                select(
                    group_expression.label("group_key"),
                    metric_expression.label("value"),
                    func.count(RunRow.id.distinct()).label("sample_size"),
                )
                .select_from(RunRow)
                .outerjoin(GradeRow, GradeRow.run_id == RunRow.id)
                .where(RunRow.id.in_(visible_ids))
                .group_by(group_expression)
                .order_by(group_expression)
            )
            rows = session.execute(query).all()
        return tuple(
            {
                "group": row.group_key,
                "value": float(row.value) if row.value is not None else None,
                "sample_size": int(row.sample_size),
            }
            for row in rows
            if row.sample_size > 0
        )

    @staticmethod
    def _project_required(scope: LabAgentSessionScope) -> str:
        if scope.project_id is None:
            reject_project_required()
        return scope.project_id

    def _project_id_for_run(self, run_id: str) -> str:
        try:
            return self._read_model.project_id_for_run(run_id)
        except KeyError:
            reject_target(LabAgentTargetSituation.ABSENT, "run_id")

    def _require_visible_run(self, scope: LabAgentSessionScope, run_id: str) -> None:
        with self._uow.session() as session:
            row = session.get(RunRow, run_id)
            if row is None:
                reject_target(LabAgentTargetSituation.ABSENT, "run_id")
            self._require_project(session, scope, self._project_id_for_run(run_id), "run_id")
            if not self._focus_allows_run(session, scope, run_id):
                reject_target(LabAgentTargetSituation.SIBLING_PROJECT, "run_id")

    def _require_project(
        self,
        session: Session,
        scope: LabAgentSessionScope,
        target_project_id: str,
        field: str,
    ) -> None:
        project_id = self._project_required(scope)
        if target_project_id == project_id:
            return
        target = session.get(ProjectRow, target_project_id)
        situation = (
            LabAgentTargetSituation.SIBLING_PROJECT
            if target is not None and target.workspace_id == scope.workspace_id
            else LabAgentTargetSituation.OTHER_WORKSPACE
        )
        reject_target(situation, field)



    @staticmethod
    def _evaluation_projection(record: EvaluationRecord) -> Readable:
        return {
            "record_id": record.record_id,
            "dimensions": [semantic_model_dump(item) for item in record.dimension_values],
            "source_type": record.source_type,
        }


    @staticmethod
    def _contains_classified_content(value: object) -> bool:
        if isinstance(value, Mapping):
            document = cast(Mapping[object, object], value)
            classification = next(
                (item for key, item in document.items() if str(key) == "classification"),
                None,
            )
            if is_classified(classification):
                return True
            return any(
                SqlAlchemyLabReadRepository._contains_classified_content(item)
                for item in document.values()
            )
        if isinstance(value, list):
            return any(
                SqlAlchemyLabReadRepository._contains_classified_content(item)
                for item in cast(list[object], value)
            )
        return False

    def _apply_focus_to_runs(
        self, query: Select[tuple[Any]], scope: LabAgentSessionScope
    ) -> Select[tuple[Any]]:
        if scope.focus_kind is None:
            return query
        if scope.focus_kind == LabAgentFocusKind.RUN:
            return query.where(RunRow.id == scope.focus_id)
        if scope.focus_kind == LabAgentFocusKind.COMPARISON:
            return query.where(
                RunRow.id.in_(
                    select(ComparisonRow.baseline_run_id).where(
                        ComparisonRow.id == scope.focus_id
                    ).union(
                        select(ComparisonRow.candidate_run_id).where(
                            ComparisonRow.id == scope.focus_id
                        )
                    )
                )
            )
        return query.where(
            RunRow.run_spec_id.in_(
                select(RunSpecRow.id).where(RunSpecRow.study_logical_id == scope.focus_id)
            )
        )

    def _focus_allows_run(
        self, session: Session, scope: LabAgentSessionScope, run_id: str
    ) -> bool:
        query = self._apply_focus_to_runs(select(RunRow.id).where(RunRow.id == run_id), scope)
        return session.scalar(query) is not None

    def _focus_allows_revision(
        self,
        session: Session,
        scope: LabAgentSessionScope,
        revision: ContractRevisionRow,
    ) -> bool:
        if scope.focus_kind is None:
            return True
        if scope.focus_kind == LabAgentFocusKind.STUDY:
            return revision.logical_id == scope.focus_id
        run_ids = tuple(
            session.scalars(self._apply_focus_to_runs(select(RunRow.id), scope))
        )
        for run_id in run_ids:
            run = session.get(RunRow, run_id)
            if run is None or run.run_spec_id is None:
                continue
            spec = self._read_model.get_run_spec(run.run_spec_id)
            refs = (
                spec.study_ref,
                spec.scenario_ref,
                spec.goal_ref,
                spec.agent_inventory_ref,
                spec.evaluation_plan_ref,
            )
            if any(
                item.logical_id == revision.logical_id
                and item.revision == revision.revision
                and item.digest == revision.digest
                for item in refs
            ):
                return True
        return False
