# -*- coding: utf-8 -*-
{
    'name': 'nSoft Virtual Fiscalization for POS',
    'version': '19.0.1.11.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Tiesioginė nVirtualFiscal (i.EKA) integracija per REST API',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_nsoft_fiscal/static/src/js/payment_screen.js',
        ],
    },
    'license': 'LGPL-3',
}
