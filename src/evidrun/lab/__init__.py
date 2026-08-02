"""Runtime do Lab Agent: laço nativo, catálogo de tools e composição de instrução.

Importe do submódulo que possui o símbolo (`lab.protocol`, `lab.loop`, `lab.tools`,
`lab.instructions`). Nada é reexportado aqui: um nome tem exatamente uma casa.

Este pacote é o Control Plane do copiloto. Nenhum caminho daqui escreve no event ledger,
produz Event de Run, cria `AdmissionRecord` ou alcança `decide_contract_revision`.
"""
