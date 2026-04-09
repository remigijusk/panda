# -*- coding: utf-8 -*-
{
    'name': 'nSoft Virtual Fiscalization for POS',
    'version': '19.0.1.59.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Tiesioginė nVirtualFiscal (i.EKA) integracija per REST API',
    'description': """
        v1.59.0: Ištaisyta JS krovimo klaida (OWL lifecycle error), pridėjus privalomus patch pavadinimus į payment_screen.js. Dabar nepajungtos kasos sėkmingai ir be klaidų užbaigia pardavimus ir nespausdina nSoft informacijos ant kvitų.
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
