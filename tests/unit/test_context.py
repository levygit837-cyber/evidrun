from __future__ import annotations

from evidrun.contexts import ContextComposer
from evidrun.experiments.models import ContextPolicySpec


def test_tail_policy_preserves_decisive_marker() -> None:
    source = "A" * 100 + "\nROOT_CAUSE=DB_POOL_EXHAUSTED"
    composer = ContextComposer()
    head = composer.compose(
        source, ContextPolicySpec(id="head", strategy="head", max_chars=50)
    )
    tail = composer.compose(
        source, ContextPolicySpec(id="tail", strategy="tail", max_chars=50)
    )
    assert "ROOT_CAUSE=" not in head["selected_content"]
    assert "ROOT_CAUSE=DB_POOL_EXHAUSTED" in tail["selected_content"]
    assert composer.diff(head, tail)["added_root_cause"] is True

