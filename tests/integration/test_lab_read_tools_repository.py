from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from evidrun.contracts.lab_agent.errors import LabAgentErrorCode
from evidrun.contracts.lab_agent.scope import LabAgentSessionScope
from evidrun.infrastructure.database import Database
from evidrun.infrastructure.database.models import (
    ExperimentRevisionRow,
    GradeRow,
    ProjectRow,
    RunRow,
    WorkspaceRow,
)
from evidrun.infrastructure.database.unit_of_work import UnitOfWork
from evidrun.lab.tools.read_port import LabToolRejected
from evidrun.lab.tools.read_repository import SqlAlchemyLabReadRepository
from evidrun.lab.tools.registry import CapabilityCatalog


class CapabilitySource:
    def capability_catalog(self) -> CapabilityCatalog:
        return CapabilityCatalog(
            admitted=({"name": "single_turn"},),
            active_rejections=({"name": "bounded", "code": "bounded_exploration_terminal"},),
        )


@pytest.fixture
def scoped_repository(tmp_path: Path) -> tuple[SqlAlchemyLabReadRepository, UnitOfWork]:
    database = Database(tmp_path / "lab-tools.db")
    database.create_all()
    unit_of_work = UnitOfWork(database)
    _seed(unit_of_work)
    yield SqlAlchemyLabReadRepository(unit_of_work, CapabilitySource()), unit_of_work
    database.dispose()


def test_aggregate_metrics_never_crosses_projects(
    scoped_repository: tuple[SqlAlchemyLabReadRepository, UnitOfWork],
) -> None:
    repository, _unit_of_work = scoped_repository
    scope = LabAgentSessionScope(workspace_id="workspace-1", project_id="project-1")

    with pytest.raises(LabToolRejected) as rejected:
        repository.aggregate_metrics(
            scope,
            metric="grade_score",
            group_by="status",
            run_ids=("run-1", "run-2"),
        )

    assert rejected.value.error.code == LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE


def test_aggregate_metrics_uses_allowlists_and_reports_sample_size(
    scoped_repository: tuple[SqlAlchemyLabReadRepository, UnitOfWork],
) -> None:
    repository, _unit_of_work = scoped_repository
    scope = LabAgentSessionScope(workspace_id="workspace-1", project_id="project-1")

    groups = repository.aggregate_metrics(
        scope,
        metric="grade_score",
        group_by="status",
        run_ids=("run-1",),
    )

    assert groups == ({"group": "completed", "value": 0.75, "sample_size": 1},)
    with pytest.raises(ValueError, match="allowlists"):
        repository.aggregate_metrics(
            scope,
            metric="avg(score); DROP TABLE runs",
            group_by="status",
            run_ids=("run-1",),
        )


def test_list_projects_returns_only_navigation_metadata(
    scoped_repository: tuple[SqlAlchemyLabReadRepository, UnitOfWork],
) -> None:
    repository, _unit_of_work = scoped_repository
    scope = LabAgentSessionScope(workspace_id="workspace-1")

    projects = repository.list_projects(scope)

    assert projects == (
        {"id": "project-1", "name": "Alpha", "created_at": "2026-08-02T12:00:00+00:00"},
    )
    assert set(projects[0]) == {"id", "name", "created_at"}


def test_sample_size_counts_runs_not_join_rows(
    scoped_repository: tuple[SqlAlchemyLabReadRepository, UnitOfWork],
) -> None:
    """Uma Run com dois grades é uma amostra, não duas.

    O outerjoin com GradeRow multiplica linhas por grade. Sem `distinct`, `run_count`
    devolvia 2.0 para uma única Run e `sample_size` afirmava uma amostra inexistente — e o
    contrato trata `sample_size` como a validade do grupo, então inflá-lo mente ao humano
    sobre quanta evidência sustenta o número.
    """

    repository, unit_of_work = scoped_repository
    scope = LabAgentSessionScope(workspace_id="workspace-1", project_id="project-1")
    with unit_of_work.session() as session:
        session.add(
            GradeRow(
                id="grade-run-1-second",
                run_id="run-1",
                grader_id="second-grader",
                score=0.95,
                passed=True,
                rationale="ok",
                evidence_json="[]",
                created_at=datetime(2026, 8, 2, 12, tzinfo=UTC),
            )
        )
        session.commit()

    counted = repository.aggregate_metrics(
        scope, metric="run_count", group_by="status", run_ids=("run-1",)
    )
    averaged = repository.aggregate_metrics(
        scope, metric="grade_score", group_by="status", run_ids=("run-1",)
    )

    assert counted == ({"group": "completed", "value": 1.0, "sample_size": 1},)
    # A média ainda usa os dois grades; só a contagem de amostra fala de Runs.
    assert averaged == ({"group": "completed", "value": 0.85, "sample_size": 1},)


def test_absent_and_out_of_project_targets_are_indistinguishable(
    scoped_repository: tuple[SqlAlchemyLabReadRepository, UnitOfWork],
) -> None:
    """Alvo inexistente e alvo de outro Project produzem a mesma recusa, campo a campo.

    Esta é a prova mínima do errors-v1 exercida pelo enforcement real, não pelo helper: a
    primeira divergência entre callsites transformaria a recusa num oráculo de existência,
    e nenhum teste do helper isolado pegaria isso.
    """

    repository, _unit_of_work = scoped_repository
    scope = LabAgentSessionScope(workspace_id="workspace-1", project_id="project-1")

    with pytest.raises(LabToolRejected) as absent:
        repository.read_run(scope, "run-does-not-exist")
    with pytest.raises(LabToolRejected) as foreign:
        repository.read_run(scope, "run-2")

    first, second = absent.value.error, foreign.value.error
    assert first.code == second.code == LabAgentErrorCode.SCOPE_TARGET_NOT_VISIBLE
    assert first.category == second.category
    assert first.message == second.message
    assert first.remediation == second.remediation
    assert first.field_path == second.field_path
    leaks = ("run-2", "project-2", "Beta", "workspace-2", "exist")
    text = f"{first.message} {first.remediation} {second.message} {second.remediation}"
    assert not [leak for leak in leaks if leak in text]


def _seed(unit_of_work: UnitOfWork) -> None:
    now = datetime(2026, 8, 2, 12, tzinfo=UTC)
    with unit_of_work.session() as session:
        session.add_all(
            [
                WorkspaceRow(
                    id="workspace-1",
                    name="Workspace",
                    name_key="workspace",
                    created_at=now,
                ),
                WorkspaceRow(
                    id="workspace-2", name="Other", name_key="other", created_at=now
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                ProjectRow(
                    id="project-1",
                    workspace_id="workspace-1",
                    name="Alpha",
                    name_key="alpha",
                    created_at=now,
                ),
                ProjectRow(
                    id="project-2",
                    workspace_id="workspace-2",
                    name="Beta",
                    name_key="beta",
                    created_at=now,
                ),
            ]
        )
        session.flush()
        _add_run(session, "run-1", "project-1", 0.75, now)
        session.flush()
        _add_run(session, "run-2", "project-2", 0.25, now)
        session.commit()


def _add_run(
    session: Session, run_id: str, project_id: str, score: float, now: datetime
) -> None:
    revision_id = f"experiment-{run_id}"
    session.add(
        ExperimentRevisionRow(
            id=revision_id,
            experiment_id=f"experiment-logical-{run_id}",
            project_id=project_id,
            title=run_id,
            status="accepted",
            manifest_json="{}",
            manifest_hash=("a" if run_id == "run-1" else "b") * 64,
            created_at=now,
        )
    )
    session.add(
        RunRow(
            id=run_id,
            experiment_revision_id=revision_id,
            variant_id="baseline",
            repetition=1,
            status="completed",
            runner="scripted",
            objective="objective",
            created_at=now,
            completed_at=now,
        )
    )
    session.flush()
    session.add(
        GradeRow(
            id=f"grade-{run_id}",
            run_id=run_id,
            grader_id="lab-test-grader",
            score=score,
            passed=True,
            rationale="ok",
            evidence_json="[]",
            created_at=now,
        )
    )
