"""The four merge layers, each concluded separately and pointing at its own evidence.

A green CI proves that checks ran. It does not record whether the result matched the
specification, whether the architecture held, or whether the verification was sufficient.
Those are three different conclusions and this module keeps them apart:

1. `spec` - outcome, invariants and non-goals met;
2. `standards` - architecture, authority, security, docs and budgets;
3. `verification` - focused tests, contracts, regressions and independent evidence;
4. `ci` - the full deterministic suite on the candidate commit.

Two rules carry the weight. A layer concluded `passed` must name evidence, so `passed` can
never be empty. And the first three layers may not cite the CI run: reusing `run:` evidence
there is exactly the "CI is green, therefore everything is fine" substitution the gate
exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .diagnostics import Diagnostic, Severity
from .parsing import (
    Table,
    read_enum,
    read_optional_text,
    read_table,
    read_text,
    read_text_tuple,
)
from .vocabulary import ChangeClassification, ImpactDeclaration, ImpactLevel

__all__ = [
    "MERGE_LAYER_ORDER",
    "CiCoverage",
    "EvidenceKind",
    "LayerConclusion",
    "MergeGate",
    "MergeLayer",
    "ReviewDepth",
    "merge_gate_diagnostics",
    "parse_merge_gate",
    "required_review_depth",
]


class EvidenceKind(StrEnum):
    """What a piece of evidence actually is, declared rather than guessed from text."""

    DIFF = "diff"
    TEST = "test"
    LOG = "log"
    REVIEW = "review"
    #: A CI run. Reserved for the `ci` layer; citing it elsewhere is the substitution.
    RUN = "run"


class LayerConclusion(StrEnum):
    PASSED = "passed"
    NOT_APPLICABLE = "not-applicable"


class ReviewDepth(StrEnum):
    #: An independent pass by someone who did not write the change.
    ORTHOGONAL = "orthogonal"
    #: A review sized to the change, allowed only when the risk families are untouched.
    PROPORTIONAL = "proportional"


#: Declaration order is the reading order of the gate; `ci` is last on purpose.
MERGE_LAYER_ORDER = ("spec", "standards", "verification", "ci")

_EVIDENCE_LAYERS = ("spec", "standards", "verification")


@dataclass(frozen=True)
class MergeLayer:
    name: str
    conclusion: LayerConclusion
    evidence: tuple[str, ...]
    justification: str | None

    def kinds(self) -> tuple[EvidenceKind, ...]:
        """The declared kind of each evidence entry, in order."""

        kinds: list[EvidenceKind] = []
        for item in self.evidence:
            prefix = item.split(":", 1)[0]
            try:
                kinds.append(EvidenceKind(prefix))
            except ValueError:
                continue
        return tuple(kinds)


@dataclass(frozen=True)
class CiCoverage:
    """Whether the recorded run still describes the code being merged."""

    #: False when the repository does not know the declared commit at all.
    resolved: bool
    #: Delivery paths that changed after the suite ran; empty means still covered.
    changed_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class MergeGate:
    review: ReviewDepth
    layers: tuple[MergeLayer, ...]
    #: The commit the full suite covered. Nothing delivered may change after it.
    ci_commit: str

    def layer(self, name: str) -> MergeLayer | None:
        return next((item for item in self.layers if item.name == name), None)


def required_review_depth(
    classification: ChangeClassification, impact: ImpactDeclaration
) -> ReviewDepth:
    """Derive the minimum review depth from declared risk, never from change size.

    A small diff can remove a capability, and a large one can be a rename. Only the
    declared risk families decide, so the answer cannot be argued down by line count.
    """

    if classification is ChangeClassification.BREAKING:
        return ReviewDepth.ORTHOGONAL
    risky = {ImpactLevel.REMOVED, ImpactLevel.BREAKING}
    if {impact.capability, impact.normative} & risky:
        return ReviewDepth.ORTHOGONAL
    if impact.persisted_contract is not ImpactLevel.NONE:
        return ReviewDepth.ORTHOGONAL
    return ReviewDepth.PROPORTIONAL


def parse_merge_gate(value: object, errors: list[str]) -> MergeGate | None:
    """Parse `[merge_gate]`, or return None when the section is absent."""

    if value is None:
        return None
    table = read_table(value, "merge_gate", errors)
    if table is None:
        return None
    review = read_enum(table, "review", ReviewDepth, errors, prefix="merge_gate.")
    # Required, not optional: a gate that does not name the covered commit records nothing.
    ci_commit = read_text(table, "ci_commit", errors, prefix="merge_gate.")
    layers = _parse_layers(table, errors)
    if review is None or ci_commit is None or layers is None:
        return None
    return MergeGate(review=review, layers=layers, ci_commit=ci_commit)


def _parse_layers(table: Table, errors: list[str]) -> tuple[MergeLayer, ...] | None:
    layers: list[MergeLayer] = []
    for name in MERGE_LAYER_ORDER:
        nested = read_table(table.get(name), f"merge_gate.{name}", errors)
        if nested is None:
            continue
        prefix = f"merge_gate.{name}."
        conclusion = read_enum(nested, "conclusion", LayerConclusion, errors, prefix=prefix)
        evidence = read_text_tuple(nested, "evidence", errors, prefix=prefix)
        justification = read_optional_text(nested, "justification", errors, prefix=prefix)
        if conclusion is None:
            continue
        if conclusion is LayerConclusion.NOT_APPLICABLE and not justification:
            errors.append(f"{prefix}justification e obrigatoria quando not-applicable")
        _validate_evidence_kinds(name, evidence, errors, prefix)
        layers.append(MergeLayer(name, conclusion, evidence, justification))
    if len(layers) != len(MERGE_LAYER_ORDER):
        missing = sorted(set(MERGE_LAYER_ORDER) - {item.name for item in layers})
        if missing:
            errors.append("merge_gate exige as camadas: " + ", ".join(missing))
        return None
    return tuple(layers)


def _validate_evidence_kinds(
    name: str, evidence: tuple[str, ...], errors: list[str], prefix: str
) -> None:
    declared = {item.value for item in EvidenceKind}
    for item in evidence:
        head, separator, reference = item.partition(":")
        if not separator or not reference.strip():
            errors.append(f"{prefix}evidence exige a forma <kind>:<referencia>: {item}")
            continue
        if head not in declared:
            errors.append(
                f"{prefix}evidence usa kind desconhecido '{head}'; "
                f"use um de: {', '.join(sorted(declared))}"
            )
    if name == "ci" and evidence and EvidenceKind.RUN.value not in {
        item.partition(":")[0] for item in evidence
    }:
        errors.append("merge_gate.ci.evidence exige ao menos uma entrada run:")


def merge_gate_diagnostics(
    gate: MergeGate | None,
    *,
    classification: ChangeClassification,
    impact: ImpactDeclaration,
    coverage: CiCoverage | None = None,
) -> tuple[Diagnostic, ...]:
    """Evaluate the gate against the recorded CI coverage and the declared risk."""

    if gate is None:
        return (
            Diagnostic(
                code="merge_gate.absent",
                severity=Severity.WARNING,
                message=(
                    "O contrato nao registra as quatro camadas do merge gate; "
                    "CI verde nao prova Spec, Standards nem Verification."
                ),
                remediation=(
                    "Adicione [merge_gate] com spec, standards, verification e ci, "
                    "cada camada apontando para sua propria evidencia."
                ),
            ),
        )
    diagnostics: list[Diagnostic] = []
    _check_layers(gate, diagnostics)
    _check_ci_coverage(gate, coverage, diagnostics)
    _check_review_depth(gate, classification, impact, diagnostics)
    return tuple(diagnostics)


def _check_layers(gate: MergeGate, diagnostics: list[Diagnostic]) -> None:
    for layer in gate.layers:
        if layer.conclusion is LayerConclusion.PASSED and not layer.evidence:
            diagnostics.append(
                Diagnostic(
                    code="merge_gate.evidence_missing",
                    severity=Severity.BLOCKER,
                    message=(
                        f"A camada {layer.name} concluiu passed sem apontar evidencia."
                    ),
                    remediation=(
                        "Aponte diff, teste, log ou review, ou conclua "
                        "not-applicable com justificativa."
                    ),
                )
            )
        if layer.name in _EVIDENCE_LAYERS and EvidenceKind.RUN in layer.kinds():
            diagnostics.append(
                Diagnostic(
                    code="merge_gate.ci_used_as_evidence",
                    severity=Severity.BLOCKER,
                    message=(
                        f"A camada {layer.name} usa a execucao de CI como evidencia; "
                        "CI verde prova somente que os checks rodaram."
                    ),
                    remediation=(
                        "Substitua a entrada run: por diff, teste, log ou review "
                        "especifico desta camada."
                    ),
                )
            )
    ci = gate.layer("ci")
    if ci is not None and ci.conclusion is LayerConclusion.NOT_APPLICABLE:
        diagnostics.append(
            Diagnostic(
                code="merge_gate.ci_not_applicable",
                severity=Severity.BLOCKER,
                message="A camada ci nao pode ser not-applicable: a suite sempre roda.",
                remediation="Registre a execucao completa no commit candidato.",
            )
        )


def _check_ci_coverage(
    gate: MergeGate, coverage: CiCoverage | None, diagnostics: list[Diagnostic]
) -> None:
    """The recorded run must name a real commit and still cover the delivered code.

    Requiring `ci_commit == HEAD` would be unsatisfiable: committing the contract that
    records the run moves HEAD past it. What matters instead is that nothing delivered
    changed after the suite ran, so the evidence still describes the code being merged.
    """

    if coverage is None:
        return
    if not coverage.resolved:
        diagnostics.append(
            Diagnostic(
                code="merge_gate.ci_commit_unknown",
                severity=Severity.BLOCKER,
                message=(
                    f"merge_gate.ci_commit aponta {gate.ci_commit}, "
                    "que nao existe neste repositorio."
                ),
                remediation="Registre o SHA real do commit em que a suite completa rodou.",
            )
        )
        return
    if coverage.changed_paths:
        diagnostics.append(
            Diagnostic(
                code="merge_gate.ci_coverage_stale",
                severity=Severity.BLOCKER,
                message=(
                    f"A suite registrada rodou em {gate.ci_commit}, mas a entrega "
                    "mudou depois disso."
                ),
                paths=coverage.changed_paths,
                remediation=(
                    "Reexecute a suite completa no commit final e atualize "
                    "merge_gate.ci_commit."
                ),
            )
        )


def _check_review_depth(
    gate: MergeGate,
    classification: ChangeClassification,
    impact: ImpactDeclaration,
    diagnostics: list[Diagnostic],
) -> None:
    required = required_review_depth(classification, impact)
    if required is ReviewDepth.ORTHOGONAL and gate.review is ReviewDepth.PROPORTIONAL:
        diagnostics.append(
            Diagnostic(
                code="merge_gate.review_depth_insufficient",
                severity=Severity.BLOCKER,
                message=(
                    "O risco declarado exige revisao ortogonal, mas o contrato "
                    "declara revisao proporcional."
                ),
                remediation=(
                    "Declare review=\"orthogonal\" e aponte a review independente, "
                    "ou reclassifique o risco."
                ),
            )
        )
        return
    if gate.review is not ReviewDepth.ORTHOGONAL:
        return
    reviewed = any(
        EvidenceKind.REVIEW in layer.kinds()
        for layer in gate.layers
        if layer.name in _EVIDENCE_LAYERS
    )
    if not reviewed:
        diagnostics.append(
            Diagnostic(
                code="merge_gate.review_evidence_missing",
                severity=Severity.BLOCKER,
                message=(
                    "A revisao ortogonal foi declarada mas nenhuma camada aponta "
                    "evidencia review:."
                ),
                remediation="Aponte a review independente na camada que ela concluiu.",
            )
        )
