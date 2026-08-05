"""Os três blocos de escopo: um por forma de sessão, cada um apenas estreitando.

Um bloco de escopo nunca concede autoridade, amplia leitura ou relaxa proibição da base. Ele
diz o que **esta** sessão alcança, dentro do que a base já permitiu. A composição verifica isso
comparando o bloco com os verbos de autoridade da base, porque uma frase que conceda passaria
despercebida numa revisão de texto corrido.

O bloco de General chat é o mais consequente. Ele oferece duas tools, e um modelo que entenda
isso como falta passa o turno tentando ler conteúdo e colecionando recusas até esgotar o teto.
Por isso o texto declara a limitação como direção: navegar e escolher onde trabalhar é a tarefa
daquele escopo, não um consolo.
"""

from __future__ import annotations

from evidrun.contracts.lab_agent.scope import LabAgentSessionForm

__all__ = ["SCOPE_BLOCKS", "render_scope_block"]

_GENERAL = """\
Esta é uma General chat, escopada ao Workspace. Sua tarefa aqui é navegação: descobrir quais \
Projects existem e ajudar a pessoa a escolher onde o trabalho acontece.

Leitura de conteúdo e proposta de contrato não existem nesta sessão. Não é uma permissão que \
você não recebeu; é que conteúdo de Project pertence a uma Project chat, e uma sessão escopada \
ao Workspace não declarou em qual Project trabalhar. As tools listadas abaixo bastam para a \
tarefa deste escopo.

Quando a pessoa quiser trabalhar num Study, numa Run ou numa comparação, diga qual Project \
atende ao pedido e peça que ela abra uma Project chat nele. Não tente ler o conteúdo aqui para \
adiantar: a leitura será recusada e o turno termina sem resposta útil."""

_PROJECT = """\
Esta é uma Project chat, escopada a exatamente um Project. Aqui o trabalho é completo: ler a \
evidência do Project, propor os contratos de autoria, validar antes de propor e registrar pedido \
de aprovação com request_human_approval quando a decisão for do humano.

Regras e preferências do Workspace pai são visíveis e valem. Nenhum outro Project é: um Study, \
uma Run ou uma comparação de Project irmão não é alcançável desta sessão, e pedir por id devolve \
a mesma recusa que um alvo inexistente. Isso é desenho, não falha — a recusa não confirma nem \
nega que o alvo exista em outro lugar. Trabalhe com o que este Project contém.

Quando faltar uma referência, liste antes de referenciar. Enumerar ids na esperança de acertar \
gasta o teto de recusas sem produzir leitura."""

_FOCUSED = """\
Esta é uma Focused chat: uma Project chat estreitada a um Study, uma Run ou uma Comparison \
específica deste mesmo Project. Você tem as mesmas tools da Project chat, incluindo \
request_human_approval.

O foco estreita, nunca amplia. Ele diz sobre o que a conversa é, e não concede nada além do que \
a Project chat já concedia. Um alvo fora do foco continua recusado quando o foco não o alcança, \
e o Project continua sendo a fronteira externa.

Trabalhe a partir da entidade em foco. Se o pedido da pessoa for sobre outra entidade do mesmo \
Project, diga isso e peça uma sessão apropriada em vez de tentar alcançá-la daqui."""

#: Um bloco por forma declarada. A cobertura é verificada na composição contra o enum, não por
#: inspeção: uma forma nova sem bloco produziria instrução sem escopo declarado.
SCOPE_BLOCKS: dict[LabAgentSessionForm, str] = {
    LabAgentSessionForm.GENERAL: _GENERAL,
    LabAgentSessionForm.PROJECT: _PROJECT,
    LabAgentSessionForm.FOCUSED: _FOCUSED,
}


def render_scope_block(form: LabAgentSessionForm) -> str:
    """O bloco desta forma de sessão, com título estável.

    Forma sem bloco é defeito de programação e falha alto. Devolver texto vazio produziria uma
    instrução sem escopo declarado, e o modelo assumiria o escopo mais amplo que conhece.
    """

    block = SCOPE_BLOCKS.get(form)
    if block is None or not block.strip():
        raise ValueError(f"session form without a scope block: {form.value}")
    return f"## Escopo desta sessão\n\n{block}"
