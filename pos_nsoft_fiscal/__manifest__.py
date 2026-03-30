# -*- coding: utf-8 -*-
{
    'name': 'nSoft Virtual Fiscalization for POS',
    'version': '19.0.1.49.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Tiesioginė nVirtualFiscal (i.EKA) integracija per REST API',
    'description': """
        v1.49.0: X Ataskaitos mygtukas sėkmingai integruotas į pagrindinį POS langą per pos_control_buttons registrą.
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
