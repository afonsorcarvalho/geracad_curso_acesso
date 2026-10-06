# -*- coding: utf-8 -*-
{
    'name': 'Geracad Curso - Controle de Acesso',
    'version': '14.0.1.1.1',
    'summary': 'Bloqueio do portal do aluno por estado da matrícula e provisionamento de acesso do professor',
    'category': 'Education',
    'author': 'JGMA',
    'license': 'LGPL-3',
    'depends': ['geracad_curso', 'geracad_aluno', 'portal', 'auth_signup'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/portal_templates.xml',
        'views/res_partner_views.xml',
        'views/professor_acesso_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
