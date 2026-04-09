# -*- coding: utf-8 -*-
{
    'name': 'nSoft Virtual Fiscalization for POS',
    'version': '19.0.1.58.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Tiesioginė nVirtualFiscal (i.EKA) integracija per REST API',
    'description': """
        v1.58.0: Ištaisyta "meluojančio" kvito klaida - nSoft tekstas ir ID ant kvito dabar spausdinami tik tuo atveju, jeigu kasoje iš tikrųjų įjungta nSoft fiskalizacija ir operacija nebuvo ignoruota.
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
