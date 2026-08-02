"""Contratos do Lab Agent: escopo de sessão, envelope e o catálogo de recusas.

Importe do submódulo que possui o símbolo (`lab_agent.scope`, `lab_agent.envelope`,
`lab_agent.errors`), ou de `evidrun.contracts`, a fachada pública do vocabulário. Nada é
reexportado aqui: um nome tem exatamente uma casa.

Estes tipos existem no domínio e ainda não possuem runtime. Laço, executor e tools
pertencem a issues próprias; nada aqui executa tool call nem produz efeito.
"""
