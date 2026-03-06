# -*- coding: utf-8 -*-
{
    'name': 'Gemini AI Receipt Scanner (Odoo 18)',
    'version': '18.0.1.0.5',
    'category': 'Accounting',
    'summary': 'Auksinis paketas: AI powered receipt scanning with Vehicle detection',
    'description': 'PILNAS ATNAUJINIMAS: Automatinis kvitų nuskaitymas su automobilių atpažinimu pagal ranka rašytą numerį ir PVM kodo paieška.',
    'author': 'Remigijus',
    'depends': ['account', 'base', 'fleet'],
    'data': [
        'views/account_move_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
