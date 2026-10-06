# -*- coding: utf-8 -*-
"""Regras puras de acesso ao portal do aluno.

Sem dependência do ORM: permite teste unitário isolado e reuso entre o
controller e (futuros) modelos.
"""

# Estados de matrícula que liberam conteúdo no portal do aluno.
# Qualquer outro estado (formado, trancado, abandono, etc.) só vê o aviso.
ESTADOS_ACESSO = ('inscrito',)


def matricula_tem_acesso(state):
    """Retorna True se uma matrícula nesse `state` pode ver conteúdo no portal."""
    return state in ESTADOS_ACESSO
