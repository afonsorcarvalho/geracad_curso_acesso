# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.geracad_curso.controllers.portal import MatriculasPortal
from odoo.addons.geracad_curso_acesso.helpers import matricula_tem_acesso, ESTADOS_ACESSO


class MatriculasPortalAcesso(MatriculasPortal):

    # -- Home: counters contam só matrículas/parcelas de matrícula com acesso --
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        Matricula = request.env['geracad.curso.matricula']
        Parcela = request.env['geracad.curso.financeiro.parcelas']
        dom_mat = [('aluno_id', '=', partner.id), ('state', 'in', list(ESTADOS_ACESSO))]
        if 'matriculas_count' in counters:
            values['matriculas_count'] = Matricula.search_count(dom_mat)
        if 'horarios_count' in counters:
            values['horarios_count'] = Matricula.search_count(dom_mat)
        if 'parcelas_count' in counters:
            values['parcelas_count'] = Parcela.sudo().search_count(
                [('aluno_id', '=', partner.id),
                 ('curso_matricula_id.state', 'in', list(ESTADOS_ACESSO))])
        return values

    # -- Detalhe da matrícula: bloqueia se não tem acesso --
    @http.route(['/my/matriculas/<int:matricula_id>'], type='http', auth="public", website=True)
    def portal_matricula_detail(self, matricula_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            matricula_sudo = self._document_check_access('geracad.curso.matricula', matricula_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if not matricula_tem_acesso(matricula_sudo.state):
            return request.render('geracad_curso_acesso.portal_aviso_matricula', {
                'page_name': 'matricula',
                'matricula': matricula_sudo,
            })
        return super().portal_matricula_detail(
            matricula_id, report_type=report_type, access_token=access_token,
            message=message, download=download, **kw)

    # -- Horário da matrícula: bloqueia se não tem acesso --
    @http.route(['/my/horario/<int:matricula_id>'], type='http', auth="user", website=True)
    def portal_matricula_horario(self, matricula_id, **kw):
        partner = request.env.user.partner_id
        matricula = request.env['geracad.curso.matricula'].sudo().search([
            ('id', '=', matricula_id),
            ('aluno_id', '=', partner.id),
        ], limit=1)
        if not matricula:
            return request.redirect('/my')
        if not matricula_tem_acesso(matricula.state):
            return request.render('geracad_curso_acesso.portal_aviso_matricula', {
                'page_name': 'horario',
                'matricula': matricula,
            })
        return super().portal_matricula_horario(matricula_id, **kw)

    # -- Detalhe do pagamento: bloqueia se a matrícula da parcela não tem acesso --
    @http.route(['/my/pagamentos/<int:parcela_id>'], type='http', auth="public", website=True)
    def portal_pagamento_detail(self, parcela_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            parcela_sudo = self._document_check_access('geracad.curso.financeiro.parcelas', parcela_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if not matricula_tem_acesso(parcela_sudo.curso_matricula_id.state):
            return request.render('geracad_curso_acesso.portal_aviso_matricula', {
                'page_name': 'Pagamentos',
                'matricula': parcela_sudo.curso_matricula_id,
            })
        return super().portal_pagamento_detail(
            parcela_id, report_type=report_type, access_token=access_token,
            message=message, download=download, **kw)

    # -- Lista de pagamentos: filtra parcelas de matrículas sem acesso --
    @http.route(['/my/pagamentos', '/my/pagamentos/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_pagamentos(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        response = super().portal_my_pagamentos(page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, **kw)
        parcelas = response.qcontext.get('parcelas')
        if parcelas is not None:
            response.qcontext['parcelas'] = parcelas.filtered(
                lambda p: matricula_tem_acesso(p.curso_matricula_id.state))
        return response

    # -- Listas de matrículas/horários: expõe a função ao template --
    @http.route(['/my/matriculas', '/my/matriculas/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_matriculas(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        response = super().portal_my_matriculas(page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, **kw)
        response.qcontext['matricula_tem_acesso'] = matricula_tem_acesso
        return response

    @http.route(['/my/horarios', '/my/horarios/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_horarios(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        response = super().portal_my_horarios(page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, **kw)
        response.qcontext['matricula_tem_acesso'] = matricula_tem_acesso
        return response
