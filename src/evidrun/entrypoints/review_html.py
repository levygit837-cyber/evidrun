"""Printable ReviewPackage representation shared by API and CLI entrypoints."""

from __future__ import annotations

import json
from html import escape
from typing import Any

from evidrun.contracts import ReviewPackage, ReviewRunSpec, semantic_model_dump


def _json_document(value: Any) -> str:
    return escape(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def _pre(value: Any) -> str:
    return f"<pre>{_json_document(value)}</pre>"


def _run_spec_section(index: int, item: ReviewRunSpec) -> str:
    capabilities = [
        semantic_model_dump(requirement)
        for requirement in item.capability_requirements
    ]
    hidden_inputs = [semantic_model_dump(reference) for reference in item.hidden_input_refs]
    refusals = [semantic_model_dump(issue) for issue in item.known_admission_refusals]
    return (
        f"<section><h3>RunSpec {index}: {escape(item.run_spec.variant_id)}</h3>"
        "<dl>"
        f"<dt>Digest</dt><dd><code>{escape(item.run_spec_digest)}</code></dd>"
        f"<dt>Scenario</dt><dd>{escape(item.run_spec.scenario_ref.logical_id)}</dd>"
        f"<dt>Repetição</dt><dd>{item.run_spec.repetition_index}</dd>"
        f"<dt>Disclosure</dt><dd>{escape(item.subject_disclosure.mode)}</dd>"
        f"<dt>Permissions</dt><dd>{_pre(list(item.requested_permissions))}</dd>"
        f"<dt>Classifications</dt><dd>{_pre([value.value for value in item.classifications])}</dd>"
        f"<dt>Network</dt><dd>{_pre(semantic_model_dump(item.network))}</dd>"
        f"<dt>External effects</dt><dd>{_pre(semantic_model_dump(item.external_effects))}</dd>"
        f"<dt>Isolamento</dt><dd>{escape(item.isolation)}</dd>"
        "</dl>"
        f"<h4>Subject disclosure</h4>{_pre(semantic_model_dump(item.subject_disclosure))}"
        f"<h4>Capabilities</h4>{_pre(capabilities)}"
        f"<h4>EvaluationPlan</h4>{_pre(semantic_model_dump(item.evaluation_plan))}"
        f"<h4>Hidden-input refs</h4>{_pre(hidden_inputs)}"
        f"<h4>Limitações</h4>{_pre(list(item.limitations))}"
        f"<h4>Recusas de admissão conhecidas</h4>{_pre(refusals)}"
        f"<h4>Requirements ausentes</h4>{_pre(list(item.missing_requirements))}"
        f"<h4>Policies negadas</h4>{_pre(list(item.denied_policies))}"
        f"<h4>RunSpec completo</h4>{_pre(semantic_model_dump(item.run_spec))}"
        "</section>"
    )


def render_review_package_html(package: ReviewPackage) -> str:
    """Render every review field while keeping ReviewTarget as the only identity."""

    closure_rows = "".join(
        "<tr>"
        f"<td>{escape(item.ref.contract_type.value)}</td>"
        f"<td>{escape(item.ref.logical_id)}</td>"
        f"<td>{item.ref.revision}</td>"
        f"<td><code>{escape(item.ref.digest)}</code></td>"
        "</tr>"
        for item in package.closure
    )
    closure_documents = "".join(
        f"<section><h3>{escape(item.ref.contract_type.value)}: "
        f"{escape(item.ref.logical_id)}@{item.ref.revision}</h3>"
        f"{_pre(item.document)}</section>"
        for item in package.closure
    )
    run_specs = "".join(
        _run_spec_section(index, item)
        for index, item in enumerate(package.run_specs, start=1)
    )
    diff = (
        _pre(semantic_model_dump(package.diff))
        if package.diff is not None
        else "<p>Sem target anterior selecionado.</p>"
    )
    return (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<title>ReviewPackage</title><style>"
        "@page{margin:22mm 14mm}body{font:14px sans-serif;color:#17202a;line-height:1.4}"
        "header,footer{position:fixed;left:0;right:0;font-size:10px}"
        "header{top:-16mm}footer{bottom:-16mm}"
        "table{border-collapse:collapse;width:100%;page-break-inside:auto}"
        "th,td{border:1px solid #bbb;padding:6px;text-align:left}"
        "section{break-inside:avoid;margin:18px 0}code,pre{word-break:break-all}"
        "pre{white-space:pre-wrap;background:#f4f6f7;padding:8px;font-size:10px}"
        "dt{font-weight:700;margin-top:7px}dd{margin:2px 0 0}"
        "</style></head><body>"
        f"<header>ReviewTarget {escape(package.review_target_digest)} · "
        f"Project {escape(package.review_target.project_id)}</header>"
        f"<footer>ReviewTarget {escape(package.review_target_digest)} · "
        "Projeção de revisão, não autoridade humana</footer>"
        "<h1>ReviewPackage</h1><p><strong>Identidade:</strong> ReviewTarget "
        f"<code>{escape(package.review_target_digest)}</code></p>"
        f"<p><strong>Study:</strong> {escape(package.study_ref.logical_id)}@"
        f"{package.study_ref.revision}</p>"
        "<p>Este documento não possui <code>review_package_digest</code> e não constitui "
        "confirmação humana.</p>"
        f"<h2>ReviewTarget</h2>{_pre(semantic_model_dump(package.review_target))}"
        "<h2>Diff</h2>"
        f"{diff}<h2>Closure exata</h2><table><thead><tr>"
        "<th>Tipo</th><th>Logical ID</th><th>Revision</th><th>Digest</th>"
        f"</tr></thead><tbody>{closure_rows}</tbody></table>{closure_documents}"
        f"<h2>RunSpecs</h2>{run_specs}</body></html>"
    )
