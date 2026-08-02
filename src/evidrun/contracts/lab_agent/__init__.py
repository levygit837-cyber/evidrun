"""Lab Agent contracts: session scope, envelope and the refusal catalog.

Import from the submodule that owns the symbol (`lab_agent.scope`, `lab_agent.envelope`,
`lab_agent.errors`, `lab_agent.refusals`), or from `evidrun.contracts`, the public facade
of the vocabulary. Nothing is re-exported here: a name has exactly one home.

Estes tipos existem no domínio e ainda não possuem runtime. Laço, executor e tools
pertencem a issues próprias; nada aqui executa tool call nem produz efeito.
"""
