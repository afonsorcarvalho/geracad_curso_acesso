# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

GROUP_PROFESSOR = 'geracad_curso.group_geracad_curso_professor'
TEMPLATE_CONVITE = 'geracad_curso_acesso.mail_template_convite_professor'
# Validade do link de definição de senha enviado no convite.
DIAS_VALIDADE_CONVITE = 7

# Grupos autorizados a gerir o acesso geracad do professor (server-side).
GRUPOS_GESTAO_ACESSO = (
    'geracad_curso.group_geracad_curso_secretaria',
    'geracad_curso.group_geracad_curso_administrator',
    'base.group_system',
)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    geracad_acesso_ativo = fields.Boolean(
        string='Acesso geracad ativo',
        compute='_compute_geracad_acesso_ativo',
    )

    def _check_pode_gerir_acesso_professor(self):
        """Garante que o usuário atual pode ativar/desativar acesso de professor.

        Enforcement server-side: vale para qualquer frontend (UI, RPC, outro
        portal), não só a visibilidade do botão.
        """
        if not any(self.env.user.has_group(g) for g in GRUPOS_GESTAO_ACESSO):
            raise AccessError(_(
                "Você não tem permissão para gerir o acesso geracad de professor. "
                "Requer um dos grupos: Secretaria, Administrador Geracad Cursos "
                "ou Configurações."))

    def _geracad_user(self):
        """Retorna o res.users ligado ao partner, incluindo arquivados.

        Usa sudo(): criar/escrever em res.users no Odoo 14 exige
        base.group_erp_manager/base.group_system, mas os grupos autorizados
        por _check_pode_gerir_acesso_professor (Secretaria, Administrador
        Geracad Cursos) só implicam base.group_user (leitura). O guard já
        controla quem pode chegar até aqui (ou, no caso do compute, apenas
        expõe um status somente-leitura), e o conjunto de grupos gravado é
        fixo (hardcoded), então não há superfície de escalonamento de
        privilégio.
        """
        self.ensure_one()
        return self.env['res.users'].sudo().with_context(active_test=False).search(
            [('partner_id', '=', self.id)], limit=1)

    @api.depends('user_ids', 'user_ids.active', 'user_ids.groups_id')
    def _compute_geracad_acesso_ativo(self):
        grp = self.env.ref(GROUP_PROFESSOR, raise_if_not_found=False)
        grp_interno = self.env.ref('base.group_user', raise_if_not_found=False)
        for partner in self:
            user = partner._geracad_user()
            partner.geracad_acesso_ativo = bool(
                user and user.active and grp and grp in user.groups_id
                and grp_interno and grp_interno in user.groups_id)

    def action_ativar_geracad_professor(self):
        self.ensure_one()
        self._check_pode_gerir_acesso_professor()
        if not self.e_professor:
            raise ValidationError(_("Só é possível ativar acesso geracad para um professor (marque 'É professor')."))
        if not self.email:
            raise ValidationError(_("Preencha o e-mail do professor antes de ativar o acesso geracad."))
        if self.env['geracad.curso.matricula'].sudo().search_count([('aluno_id', '=', self.id)]):
            raise ValidationError(_(
                "Este cadastro possui matrícula de aluno e não pode virar usuário interno de professor. "
                "Use um cadastro separado para o professor."))

        grp_prof = self.env.ref(GROUP_PROFESSOR)
        grp_interno = self.env.ref('base.group_user')
        user = self._geracad_user()
        conflito = self.env['res.users'].sudo().with_context(active_test=False).search(
            [('login', '=ilike', self.email), ('id', '!=', user.id)], limit=1)
        if conflito:
            raise ValidationError(_(
                "O e-mail %s já é login de outro usuário (%s). Use outro e-mail.")
                % (self.email, conflito.name))
        # no_reset_password: evita o e-mail padrão do Odoo; enviamos o convite próprio.
        Users = self.env['res.users'].sudo().with_context(no_reset_password=True)
        # Professor leciona em qualquer unidade: libera todas as empresas.
        empresas = self.env['res.company'].sudo().search([])
        empresa_padrao = self.company_id or self.env.company
        if not user:
            user = Users.create({
                'name': self.name,
                'login': self.email,
                'partner_id': self.id,
                'company_ids': [(6, 0, empresas.ids)],
                'company_id': empresa_padrao.id,
                'groups_id': [(6, 0, [grp_interno.id, grp_prof.id])],
            })
        else:
            user.with_context(no_reset_password=True).sudo().write({
                'active': True,
                'login': self.email,
                'company_ids': [(6, 0, empresas.ids)],
                'groups_id': [(4, grp_interno.id), (4, grp_prof.id)],
            })
        self._enviar_convite_geracad(user)
        return True

    def _enviar_convite_geracad(self, user):
        """Gera link de definição de senha e envia o e-mail de convite."""
        self.ensure_one()
        partner = self.sudo()
        expiracao = fields.Datetime.now() + timedelta(days=DIAS_VALIDADE_CONVITE)
        # expiration força um token novo mesmo se já houver um válido.
        partner.signup_prepare(signup_type='signup', expiration=expiracao)
        template = self.env.ref(TEMPLATE_CONVITE)
        template.sudo().send_mail(user.id, force_send=True)

    def action_desativar_geracad_professor(self):
        self.ensure_one()
        self._check_pode_gerir_acesso_professor()
        grp_prof = self.env.ref(GROUP_PROFESSOR)
        user = self._geracad_user()
        if user:
            user.sudo().write({
                'active': False,
                'groups_id': [(3, grp_prof.id)],
            })
        return True
