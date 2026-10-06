# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.geracad_curso_acesso.helpers import matricula_tem_acesso, ESTADOS_ACESSO


@tagged('post_install', '-at_install')
class TestMatriculaTemAcesso(TransactionCase):

    def test_inscrito_tem_acesso(self):
        self.assertTrue(matricula_tem_acesso('inscrito'))

    def test_formado_nao_tem_acesso(self):
        self.assertFalse(matricula_tem_acesso('formado'))

    def test_estados_bloqueados_nao_tem_acesso(self):
        for state in ('draft', 'trancado', 'suspensa', 'abandono',
                      'cancelada', 'expulso', 'falecido', 'transferido'):
            self.assertFalse(matricula_tem_acesso(state), state)

    def test_estado_falsy_nao_tem_acesso(self):
        self.assertFalse(matricula_tem_acesso(False))

    def test_constante_so_inscrito(self):
        self.assertEqual(ESTADOS_ACESSO, ('inscrito',))
