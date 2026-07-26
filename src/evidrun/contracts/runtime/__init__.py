"""Runtime contracts: spec, records, envelope, events and durable execution.

This package replaced the single `contracts/runtime.py` module. Import from the submodule
that owns the symbol (`runtime.spec`, `runtime.records`, `runtime.envelope`,
`runtime.events`, `runtime.execution`), or from `evidrun.contracts`, the public facade of
the vocabulary. Nothing is re-exported here: a name has exactly one home.
"""
