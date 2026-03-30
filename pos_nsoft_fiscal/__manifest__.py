# -*- coding: utf-8 -*-
{
    'name': 'nSoft Virtual Fiscalization for POS',
    'version': '19.0.1.43.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Tiesioginė nVirtualFiscal (i.EKA) integracija per REST API',
    'description': """
        v1.43.0: Pridėtas X Ataskaitos mygtukas POS ekrane ir sutvarkyta Cash In/Out pliuso/minuso logika.
    """,
    'author': 'Remigijus Kubilius',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_nsoft_fiscal/static/src/js/payment_screen.js',
            'pos_nsoft_fiscal/static/src/xml/OrderReceipt.xml',
            'pos_nsoft_fiscal/static/src/js/x_report_button.js',
            'pos_nsoft_fiscal/static/src/xml/x_report_button.xml',
        ],
    },
    'license': 'LGPL-3',
}
