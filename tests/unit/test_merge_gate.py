"""The merge gate concludes four layers separately and never lets CI stand in for three.

A green CI proves that checks ran. These pin the two rules that carry the weight: a layer
concluded `passed` must name its own evidence, and the first three layers may not cite the
CI run to reach that conclusion.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from change_contract import (  # noqa: E402
    MERGE_LAYER_ORDER,
    ChangeClassification,
    CiCoverage,
    EvidenceKind,
    ImpactLevel,
    LayerConclusion,
    ReviewDepth,
    load_contract,
    merge_gate_diagnostics,
    required_review_depth,
)
from change_contract.merge_gate import parse_merge_gate  # noqa: E402
from change_contract.vocabulary import ImpactDeclaration  # noqa: E402


def impact(
    *,
    capability: str = "none",
    persisted: str = "none",
    normative: str = "none",
) -> ImpactDeclaration:
    return ImpactDeclaration(
        capability=ImpactLevel(capability),
        persisted_contract=ImpactLevel(persisted),
        normative=ImpactLevel(normative),
        notes=(),
    )


def gate_table(
    *,
    review: str = "proportional",
    ci_commit: str = "abc1234",
    spec: str = 'conclusion = "passed"\nevidence = ["diff:src/task/owned.py"]',
    standards: str = 'conclusion = "passed"\nevidence = ["review:PR#1"]',
    verification: str = 'conclusion = "passed"\nevidence = ["test:tests/unit/test_x.py"]',
    ci: str = 'conclusion = "passed"\nevidence = ["run:actions/1"]',
    layers: tuple[str, ...] = MERGE_LAYER_ORDER,
) -> dict[str, object]:
    import tomllib

    bodies = {"spec": spec, "standards": standards, "verification": verification, "ci": ci}
    sections = "\n".join(f"[{name}]\n{bodies[name]}" for name in layers)
    document = f'review = "{review}"\nci_commit = "{ci_commit}"\n{sections}\n'
    return tomllib.loads(document)


def parse(table: dict[str, object]) -> tuple[object, list[str]]:
    errors: list[str] = []
    return parse_merge_gate(table, errors), errors


def test_a_complete_gate_parses_and_reports_nothing() -> None:
    gate, errors = parse(gate_table())

    assert errors == []
    assert gate is not None
    assert [layer.name for layer in gate.layers] == list(MERGE_LAYER_ORDER)
    assert (
        merge_gate_diagnostics(
            gate,
            classification=ChangeClassification.FEATURE,
            impact=impact(),
            coverage=CiCoverage(resolved=True),
        )
        == ()
    )


def test_every_layer_is_required() -> None:
    gate, errors = parse(gate_table(layers=("spec", "ci")))

    assert gate is None
    assert any("merge_gate exige as camadas" in item for item in errors)
    assert any("standards" in item and "verification" in item for item in errors)


def test_an_absent_gate_warns_that_ci_proves_only_itself() -> None:
    diagnostics = merge_gate_diagnostics(
        None, classification=ChangeClassification.FEATURE, impact=impact()
    )

    assert [item.code for item in diagnostics] == ["merge_gate.absent"]
    assert diagnostics[0].severity.value == "warning"


def test_passed_without_evidence_is_a_blocker() -> None:
    gate, errors = parse(gate_table(spec='conclusion = "passed"\nevidence = []'))

    assert errors == []
    assert gate is not None
    diagnostics = merge_gate_diagnostics(
        gate,
        classification=ChangeClassification.FEATURE,
        impact=impact(),
        coverage=CiCoverage(resolved=True),
    )

    # `passed` with nothing behind it is the empty conclusion the gate exists to refuse.
    assert [item.code for item in diagnostics] == ["merge_gate.evidence_missing"]
    assert diagnostics[0].severity.value == "blocker"


@pytest.mark.parametrize("layer", ["spec", "standards", "verification"])
def test_the_first_three_layers_may_not_cite_the_ci_run(layer: str) -> None:
    gate, errors = parse(
        gate_table(**{layer: 'conclusion = "passed"\nevidence = ["run:actions/1"]'})
    )

    assert errors == []
    assert gate is not None
    diagnostics = merge_gate_diagnostics(
        gate,
        classification=ChangeClassification.FEATURE,
        impact=impact(),
        coverage=CiCoverage(resolved=True),
    )

    # This is the substitution the gate exists to prevent: "CI is green, therefore the
    # spec was met". Reusing run: evidence outside the ci layer asserts exactly that.
    assert "merge_gate.ci_used_as_evidence" in {item.code for item in diagnostics}
    assert layer in next(
        item.message for item in diagnostics if item.code == "merge_gate.ci_used_as_evidence"
    )


def test_the_ci_layer_cannot_be_not_applicable() -> None:
    gate, errors = parse(
        gate_table(
            ci='conclusion = "not-applicable"\nevidence = []\njustification = "sem codigo"'
        )
    )

    assert errors == []
    assert gate is not None
    diagnostics = merge_gate_diagnostics(
        gate,
        classification=ChangeClassification.FEATURE,
        impact=impact(),
        coverage=CiCoverage(resolved=True),
    )

    assert "merge_gate.ci_not_applicable" in {item.code for item in diagnostics}


def test_not_applicable_requires_a_justification() -> None:
    _, errors = parse(gate_table(spec='conclusion = "not-applicable"\nevidence = []'))

    assert any("justification e obrigatoria" in item for item in errors)


def test_a_justified_not_applicable_layer_is_accepted() -> None:
    gate, errors = parse(
        gate_table(
            spec=(
                'conclusion = "not-applicable"\nevidence = []\n'
                'justification = "Mudanca gerada, sem resultado de produto."'
            )
        )
    )

    assert errors == []
    assert gate is not None
    # `not-applicable` is an honest conclusion when justified, so it must not need evidence.
    assert (
        merge_gate_diagnostics(
            gate,
            classification=ChangeClassification.GENERATED,
            impact=impact(),
            coverage=CiCoverage(resolved=True),
        )
        == ()
    )


def test_evidence_must_declare_its_kind() -> None:
    _, malformed = parse(gate_table(spec='conclusion = "passed"\nevidence = ["passou"]'))
    _, unknown = parse(
        gate_table(spec='conclusion = "passed"\nevidence = ["vibes:acho que sim"]')
    )

    assert any("exige a forma <kind>:<referencia>" in item for item in malformed)
    assert any("kind desconhecido 'vibes'" in item for item in unknown)


def test_the_ci_layer_must_point_at_a_run() -> None:
    _, errors = parse(gate_table(ci='conclusion = "passed"\nevidence = ["log:local.txt"]'))

    assert any("exige ao menos uma entrada run:" in item for item in errors)


@pytest.mark.parametrize(
    ("classification", "impact_kwargs", "expected"),
    [
        ("feature", {}, ReviewDepth.PROPORTIONAL),
        ("docs-only", {}, ReviewDepth.PROPORTIONAL),
        ("breaking", {}, ReviewDepth.ORTHOGONAL),
        ("feature", {"capability": "removed"}, ReviewDepth.ORTHOGONAL),
        ("feature", {"normative": "breaking"}, ReviewDepth.ORTHOGONAL),
        ("feature", {"persisted": "additive"}, ReviewDepth.ORTHOGONAL),
        ("feature", {"capability": "additive"}, ReviewDepth.PROPORTIONAL),
    ],
)
def test_review_depth_follows_declared_risk_not_change_size(
    classification: str, impact_kwargs: dict[str, str], expected: ReviewDepth
) -> None:
    # A small diff can remove a capability and a large one can be a rename, so only the
    # declared risk decides. Line count must never be able to argue the depth down.
    assert (
        required_review_depth(
            ChangeClassification(classification), impact(**impact_kwargs)
        )
        is expected
    )


def test_proportional_review_on_risky_change_is_a_blocker() -> None:
    gate, errors = parse(gate_table(review="proportional"))

    assert errors == []
    assert gate is not None
    diagnostics = merge_gate_diagnostics(
        gate,
        classification=ChangeClassification.BREAKING,
        impact=impact(),
        coverage=CiCoverage(resolved=True),
    )

    assert "merge_gate.review_depth_insufficient" in {item.code for item in diagnostics}


def test_orthogonal_review_must_point_at_a_review() -> None:
    gate, errors = parse(
        gate_table(
            review="orthogonal",
            standards='conclusion = "passed"\nevidence = ["diff:src/task/owned.py"]',
        )
    )

    assert errors == []
    assert gate is not None
    diagnostics = merge_gate_diagnostics(
        gate,
        classification=ChangeClassification.BREAKING,
        impact=impact(),
        coverage=CiCoverage(resolved=True),
    )

    # Declaring the depth is not performing it; the review has to be pointed at.
    assert "merge_gate.review_evidence_missing" in {item.code for item in diagnostics}


def test_orthogonal_review_with_review_evidence_passes() -> None:
    gate, errors = parse(gate_table(review="orthogonal"))

    assert errors == []
    assert gate is not None
    assert gate.review is ReviewDepth.ORTHOGONAL
    assert (
        merge_gate_diagnostics(
            gate,
            classification=ChangeClassification.BREAKING,
            impact=impact(),
            coverage=CiCoverage(resolved=True),
        )
        == ()
    )


def test_an_unknown_ci_commit_is_a_blocker() -> None:
    gate, _ = parse(gate_table())

    diagnostics = merge_gate_diagnostics(
        gate,
        classification=ChangeClassification.FEATURE,
        impact=impact(),
        coverage=CiCoverage(resolved=False),
    )

    assert [item.code for item in diagnostics] == ["merge_gate.ci_commit_unknown"]


def test_delivery_changed_after_the_run_invalidates_the_coverage() -> None:
    gate, _ = parse(gate_table())

    diagnostics = merge_gate_diagnostics(
        gate,
        classification=ChangeClassification.FEATURE,
        impact=impact(),
        coverage=CiCoverage(resolved=True, changed_paths=("src/task/owned.py",)),
    )

    # A suite that ran before the last edit describes different code.
    assert [item.code for item in diagnostics] == ["merge_gate.ci_coverage_stale"]
    assert diagnostics[0].paths == ("src/task/owned.py",)


def test_ci_commit_is_required() -> None:
    table = gate_table()
    del table["ci_commit"]
    gate, errors = parse(table)

    assert gate is None
    assert any("ci_commit" in item for item in errors)


def test_evidence_kinds_are_read_from_the_declared_prefix() -> None:
    gate, errors = parse(
        gate_table(
            spec='conclusion = "passed"\nevidence = ["diff:a.py", "log:b.txt", "review:PR#2"]'
        )
    )

    assert errors == []
    assert gate is not None
    spec = gate.layer("spec")
    assert spec is not None
    assert spec.kinds() == (EvidenceKind.DIFF, EvidenceKind.LOG, EvidenceKind.REVIEW)


def test_layer_lookup_returns_none_for_an_unknown_name() -> None:
    gate, _ = parse(gate_table())

    assert gate is not None
    assert gate.layer("vibes") is None
    assert gate.layer("ci") is not None
    assert gate.layer("ci").conclusion is LayerConclusion.PASSED


FIXTURES = Path(__file__).resolve().parent / "fixtures/merge-gate"


@pytest.mark.parametrize(
    ("name", "classification"),
    [
        ("feature.toml", "feature"),
        ("refactor.toml", "refactor"),
        ("docs-only.toml", "docs-only"),
        ("generated.toml", "generated"),
    ],
)
def test_each_classification_has_a_loadable_example(name: str, classification: str) -> None:
    """One worked example per classification, loaded through the real contract loader.

    These are the reference the issue asked for: a reader copies the shape instead of
    inventing it, and a change to the schema breaks them here rather than in a PR.
    """

    contract = load_contract(FIXTURES / name)

    assert contract.classification.value == classification
    assert contract.merge_gate is not None
    assert [layer.name for layer in contract.merge_gate.layers] == list(MERGE_LAYER_ORDER)
    assert (
        merge_gate_diagnostics(
            contract.merge_gate,
            classification=contract.classification,
            impact=contract.impact,
            coverage=CiCoverage(resolved=True),
        )
        == ()
    )


def test_the_shipped_template_carries_a_complete_gate() -> None:
    contract = load_contract(ROOT / "docs/templates/change-contract.toml")

    # The template is what every new contract is copied from, so an incomplete gate there
    # would propagate into every future issue.
    assert contract.merge_gate is not None
    assert [layer.name for layer in contract.merge_gate.layers] == list(MERGE_LAYER_ORDER)
    assert contract.merge_gate.review is ReviewDepth.PROPORTIONAL
