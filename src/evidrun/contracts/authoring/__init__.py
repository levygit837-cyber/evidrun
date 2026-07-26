"""Authoring contracts: one revision family per module.

This package replaced the single `contracts/authoring.py` module. Import from the submodule
that owns the symbol (`authoring.goal`, `authoring.scenario`, `authoring.inventory`,
`authoring.workspace`, `authoring.protocol`, `authoring.evaluation`, `authoring.checkpoint`,
`authoring.progress`, `authoring.run`, `authoring.study`, `authoring.study_intent`,
`authoring.parse`), or from `evidrun.contracts`, the public facade of the vocabulary.
Nothing is re-exported here: a name has exactly one home.
"""
