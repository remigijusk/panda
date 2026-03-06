# -*- coding: utf-8 -*-
{
    'name': 'Gemini AI Receipt Scanner (Odoo 18)',
    'version': '18.0.1.0.6',
    'category': 'Accounting',
    'summary': 'Auksinis paketas: AI powered receipt scanning with Vehicle detection',
    'description': 'PILNAS ATNAUJINIMAS: Automatinis kvitų nuskaitymas su teisingu kainos be PVM skaičiavimu (Suma be PVM / Kiekis).',
    'author': 'Remigijus',
    'depends': ['account', 'base', 'fleet'],
    'data': [
        'views/account_move_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
