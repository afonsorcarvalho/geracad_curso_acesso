# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestProfessorAcesso(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.Users = self.env['res.users']
        self.grp_prof = self.env.ref('geracad_curso.group_geracad_curso_professor')
        self.grp_interno = self.env.ref('base.group_user')

    def _novo_professor(self, email='prof@example.com'):
        return self.Partner.create({
            'name': 'Prof Teste',
            'e_professor': True,
            'email': email,
        })

    def _user_do_partner(self, partner):
        return self.Users.with_context(active_test=False).search(
            [('partner_id', '=', partner.id)], limit=1)

    def test_ativar_cria_user_interno_com_grupo(self):
        prof = self._novo_professor()
        prof.action_ativar_geracad_professor()
        user = self._user_do_partner(prof)
        self.assertTrue(user, "deveria ter criado um res.users")
        self.assertTrue(user.active)
        self.assertEqual(user.login, 'prof@example.com')
        self.assertIn(self.grp_interno, user.groups_id, "deveria ser usuário interno")
        self.assertIn(self.grp_prof, user.groups_id, "deveria ter grupo professor")
        self.assertTrue(prof.geracad_acesso_ativo)

    def test_ativar_libera_todas_empresas(self):
        self.env['res.company'].create({'name': 'Unidade Extra Teste'})
        prof = self._novo_professor()
        prof.action_ativar_geracad_professor()
        user = self._user_do_partner(prof)
        self.assertEqual(user.company_ids, self.env['res.company'].search([]))

    def test_acesso_ativo_exige_grupo_interno(self):
        """geracad_acesso_ativo deve exigir usuário INTERNO com grupo professor.

        O grupo professor não implica base.group_user (implied_ids comentado
        em geracad_curso), então um usuário ativo com o grupo professor mas
        sem base.group_user não deve contar como acesso geracad ativo.
        """
        prof = self._novo_professor()
        prof.action_ativar_geracad_professor()
        self.assertTrue(prof.geracad_acesso_ativo)

        user = self._user_do_partner(prof)
        # Nota: remover base.group_user SOZINHO aciona a lógica core do Odoo
        # UsersImplied.write() que trata usuários "demoted" (perderam o
        # grupo interno) limpando TODOS os grupos, incluindo os passados
        # antes na mesma chamada — o que apagaria também o grupo professor
        # e invalidaria o cenário do teste. Por isso removemos o grupo
        # interno e reafirmamos o grupo professor na MESMA escrita: o core
        # aplica a limpeza e depois reaplica exatamente os comandos
        # informados, resultando em um usuário ativo com APENAS o grupo
        # professor (sem base.group_user) — exatamente o cenário que
        # _compute_geracad_acesso_ativo precisa rejeitar.
        user.write({'groups_id': [(3, self.grp_interno.id), (4, self.grp_prof.id)]})

        self.assertTrue(user.active, "usuário deve continuar ativo")
        self.assertIn(self.grp_prof, user.groups_id, "grupo professor deve continuar presente")
        self.assertNotIn(self.grp_interno, user.groups_id, "grupo interno deve ter sido removido")
        prof.invalidate_cache(['geracad_acesso_ativo'])
        self.assertFalse(
            prof.geracad_acesso_ativo,
            "sem grupo interno (base.group_user), acesso geracad não deve estar ativo "
            "mesmo com grupo professor e usuário ativo")

    def test_ativar_sem_email_levanta(self):
        prof = self._novo_professor(email=False)
        with self.assertRaises(ValidationError):
            prof.action_ativar_geracad_professor()

    def test_ativar_sem_permissao_levanta(self):
        prof = self._novo_professor()
        user_sem_perm = self.Users.create({
            'name': 'Sem Permissao',
            'login': 'semperm@example.com',
            'groups_id': [(6, 0, [self.grp_interno.id])],
        })
        with self.assertRaises(AccessError):
            prof.with_user(user_sem_perm).action_ativar_geracad_professor()

    def test_desativar_sem_permissao_levanta(self):
        prof = self._novo_professor()
        prof.action_ativar_geracad_professor()
        user_sem_perm = self.Users.create({
            'name': 'Sem Permissao 2',
            'login': 'semperm2@example.com',
            'groups_id': [(6, 0, [self.grp_interno.id])],
        })
        with self.assertRaises(AccessError):
            prof.with_user(user_sem_perm).action_desativar_geracad_professor()

    def test_ativar_nao_professor_levanta(self):
        partner = self.Partner.create({'name': 'Fulano', 'e_professor': False, 'email': 'f@example.com'})
        with self.assertRaises(ValidationError):
            partner.action_ativar_geracad_professor()

    def _get_or_create_turma(self):
        """Retorna uma turma existente no ambiente ou cria a cadeia mínima
        (geracad.curso.type -> geracad.curso -> geracad.curso.turma) para
        que o teste funcione também em uma base limpa (ex.: CI)."""
        turma = self.env['geracad.curso.turma'].search([], limit=1)
        if turma:
            return turma
        company = self.env.company
        curso_type = self.env['geracad.curso.type'].create({
            'name': 'Tipo Teste Acesso',
        })
        curso = self.env['geracad.curso'].create({
            'name': 'Curso Teste Acesso',
            'sigla': 'CTSTACS',
            'type_curso': curso_type.id,
            'company_id': company.id,
        })
        return self.env['geracad.curso.turma'].create({
            'curso_id': curso.id,
            'turno': 'MAT',
            'company_id': company.id,
        })

    def test_ativar_partner_aluno_levanta(self):
        prof = self._novo_professor()
        turma = self._get_or_create_turma()
        self.env['geracad.curso.matricula'].create({
            'aluno_id': prof.id,
            'curso_turma_id': turma.id,
            'company_id': turma.company_id.id,
        })
        with self.assertRaises(ValidationError):
            prof.action_ativar_geracad_professor()

    def test_ativar_por_secretaria_nao_admin_funciona(self):
        """Regressão: Secretaria/Administrador Geracad Cursos só implicam
        base.group_user (leitura em res.users), não base.group_erp_manager/
        base.group_system. Sem sudo() no acesso a res.users dentro deste
        modelo, um usuário de Secretaria passa no guard mas recebe
        AccessError ao tentar criar o res.users do professor. Este teste
        deve falhar (AccessError) sem o fix de sudo, e passar com ele."""
        prof = self._novo_professor(email='prof.secretaria@example.com')
        grp_secretaria = self.env.ref('geracad_curso.group_geracad_curso_secretaria')
        secretaria_user = self.Users.create({
            'name': 'Secretaria Teste',
            'login': 'secretaria.teste@example.com',
            'groups_id': [(6, 0, [self.grp_interno.id, grp_secretaria.id])],
        })
        prof.with_user(secretaria_user).action_ativar_geracad_professor()
        user = self._user_do_partner(prof)
        self.assertTrue(user, "deveria ter criado um res.users")
        self.assertTrue(user.active)
        self.assertIn(self.grp_interno, user.groups_id, "deveria ser usuário interno")
        self.assertIn(self.grp_prof, user.groups_id, "deveria ter grupo professor")
        prof.invalidate_cache(['geracad_acesso_ativo'])
        self.assertTrue(prof.geracad_acesso_ativo)

    def test_desativar_arquiva_e_remove_grupo(self):
        prof = self._novo_professor()
        prof.action_ativar_geracad_professor()
        prof.action_desativar_geracad_professor()
        user = self._user_do_partner(prof)
        self.assertTrue(user, "user deve continuar existindo, apenas arquivado")
        self.assertFalse(user.active, "user deve estar arquivado")
        self.assertNotIn(self.grp_prof, user.groups_id, "grupo professor deve ser removido")
        self.assertFalse(prof.geracad_acesso_ativo)

    def test_reativar_reaproveita_user_arquivado(self):
        prof = self._novo_professor()
        prof.action_ativar_geracad_professor()
        user_antes = self._user_do_partner(prof)
        prof.action_desativar_geracad_professor()
        prof.action_ativar_geracad_professor()
        user_depois = self._user_do_partner(prof)
        self.assertEqual(user_antes, user_depois, "deve reaproveitar o mesmo user, não criar outro")
        self.assertTrue(user_depois.active)
        self.assertIn(self.grp_prof, user_depois.groups_id)
        self.assertTrue(prof.geracad_acesso_ativo)

    def test_wizard_concede_acesso_e_envia_convite(self):
        prof = self._novo_professor(email=False)
        wiz = self.env['geracad.professor.acesso.wizard'].with_context(
            active_id=prof.id).create({'email': ' Novo.Prof@Example.com '})
        self.assertEqual(wiz.partner_id, prof)
        tpl = self.env.ref('geracad_curso_acesso.mail_template_convite_professor')
        with patch.object(type(tpl), 'send_mail', autospec=True) as send_mail:
            wiz.action_conceder()
        self.assertEqual(prof.email, 'novo.prof@example.com')
        user = self._user_do_partner(prof)
        self.assertEqual(user.login, 'novo.prof@example.com')
        self.assertTrue(prof.geracad_acesso_ativo)
        self.assertTrue(prof.signup_token, "deveria gerar token de cadastro de senha")
        self.assertEqual(prof.signup_type, 'signup')
        send_mail.assert_called_once()
        self.assertEqual(send_mail.call_args[0][0], tpl)
        self.assertEqual(send_mail.call_args[0][1], user.id)

    def test_wizard_email_invalido_levanta(self):
        prof = self._novo_professor(email=False)
        wiz = self.env['geracad.professor.acesso.wizard'].create(
            {'partner_id': prof.id, 'email': 'nao-e-email'})
        with self.assertRaises(ValidationError):
            wiz.action_conceder()

    def test_ativar_email_ja_usado_por_outro_user_levanta(self):
        self.Users.create({'name': 'Outro', 'login': 'dup@example.com'})
        prof = self._novo_professor(email='dup@example.com')
        with self.assertRaises(ValidationError):
            prof.action_ativar_geracad_professor()

    def test_template_convite_renderiza_link_e_ajuda(self):
        prof = self._novo_professor(email='render@example.com')
        prof.action_ativar_geracad_professor()
        user = self._user_do_partner(prof)
        tpl = self.env.ref('geracad_curso_acesso.mail_template_convite_professor')
        body = tpl._render_field('body_html', [user.id])[user.id]
        self.assertIn(prof.signup_token, body)
        self.assertIn('Ajuda', body)
        self.assertIn('Diários', body)
