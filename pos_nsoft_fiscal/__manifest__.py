# -*- coding: utf-8 -*-
{
    'name': 'nSoft Virtual Fiscalization for POS',
    'version': '19.0.1.63.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Tiesioginė nVirtualFiscal (i.EKA) integracija per REST API',
    'description': """
        v1.63.0: Pilna ir galutinė modulio revizija. Atstatytas 100% stabilumas. JS faile įdiegtas universalus 'getVal' metodas, kuris apsaugo naršyklę nuo lūžimo ('is not a function'), atpažindamas ar Odoo naudoja funkcijas, ar savybes (getters). Modulis stabiliai veikia tiek su įjungta, tiek su išjungta nSoft varnelėmis.
    """,
    'author': 'Remigijus Kubilius',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/pos_session_views.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_nsoft_fiscal/static/src/js/payment_screen.js',
            'pos_nsoft_fiscal/static/src/xml/OrderReceipt.xml',
        ],
    },
    'license': 'LGPL-3',
}
