# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import single_email_re


class GeracadProfessorAcessoWizard(models.TransientModel):
    _name = 'geracad.professor.acesso.wizard'
    _description = 'Conceder acesso geracad ao professor'

    partner_id = fields.Many2one('res.partner', string='Professor', required=True, readonly=True)
    email = fields.Char(string='E-mail', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        partner_id = res.get('partner_id') or self.env.context.get('active_id')
        if partner_id:
            res['partner_id'] = partner_id
            res.setdefault('email', self.env['res.partner'].browse(partner_id).email)
        return res

    def action_conceder(self):
        self.ensure_one()
        partner = self.partner_id
        partner._check_pode_gerir_acesso_professor()
        email = (self.email or '').strip().lower()
        if not single_email_re.match(email):
            raise ValidationError(_("E-mail inválido: %s") % self.email)
        if partner.email != email:
            partner.sudo().write({'email': email})
        partner.action_ativar_geracad_professor()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Acesso concedido"),
                'message': _("Convite enviado para %s.") % email,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
