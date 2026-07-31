"""Human-readable execution trust labels shared by auditable projections."""

from __future__ import annotations

from html import escape

from evidrun.contracts import ExecutionTrustRecord

TRUST_LABELS = {
    "unverified_revision_set": (
        "Não verificada",
        "Sem confirmação humana das revisions",
    ),
    "verified_revision_set": (
        "Verificada",
        "Revisions confirmadas por autoridade humana",
    ),
}


def render_run_trust_summary_html(
    *,
    run_id: str,
    trust: ExecutionTrustRecord,
    isolation: str,
) -> str:
    """Printable page whose fixed header/footer preserve trust out of context."""

    label, explanation = TRUST_LABELS[trust.kind]
    identity = (
        f"Run {escape(run_id)} · Trust {escape(label)} · "
        f"trust_id {escape(trust.trust_id)}"
    )
    return (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<title>Evidrun — trust da Run</title><style>"
        "@page{margin:24mm 16mm}body{font:15px sans-serif;color:#17202a}"
        "header,footer{position:fixed;left:0;right:0;font-size:10px}"
        "header{top:-18mm}footer{bottom:-18mm}code{word-break:break-all}"
        "dt{font-weight:700;margin-top:12px}dd{margin:3px 0 0}"
        "</style></head><body>"
        f"<header>{identity}</header><footer>{identity}</footer>"
        "<h1>Execution Trust</h1><dl>"
        f"<dt>Run</dt><dd><code>{escape(run_id)}</code></dd>"
        f"<dt>Trust</dt><dd>{escape(label)} — {escape(explanation)}</dd>"
        f"<dt>Trust ID</dt><dd><code>{escape(trust.trust_id)}</code></dd>"
        f"<dt>Trust digest</dt><dd><code>{escape(trust.digest)}</code></dd>"
        f"<dt>Isolamento</dt><dd>{escape(isolation)}</dd>"
        "</dl><p>Trust e isolamento são eixos independentes. "
        "O rótulo de isolamento não afirma sandbox além do adapter comprovado.</p>"
        "</body></html>"
    )
